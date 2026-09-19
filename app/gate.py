"""Skill-authoring contracts: job → build → prove → Keep writes pack / Throw away writes nothing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.methods import DS, fill_order, method_name
from app.pack import pack_tree, write_pack
from app.prove import ProveCLIError, run_prove
from app.skill_md import preview_sections, skill_name_from_job

Step = Literal[
    "job",
    "build",
    "prove",
    "dispose",
    "done_keep",
    "done_throw",
]


class GateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _empty(value: str | None) -> bool:
    return not (value or "").strip()


def _clean_list(items: list[str] | None) -> list[str]:
    if not items:
        return []
    return [s.strip() for s in items if s and s.strip()]


@dataclass
class Section:
    status: Literal["empty", "filled", "skipped"] = "empty"
    body: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "body": self.body}


@dataclass
class Depth:
    nested: bool = False
    tools: bool = False
    scripts: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {"nested": self.nested, "tools": self.tools, "scripts": self.scripts}


@dataclass
class Session:
    id: str
    job: str = ""
    method: str | None = "description"
    when: str = ""
    not_when: str = ""
    body: str = ""
    should: list[str] = field(default_factory=list)
    should_not: list[str] = field(default_factory=list)
    relevant: list[str] = field(default_factory=list)
    not_relevant: list[str] = field(default_factory=list)
    benchmarks: list[dict[str, Any]] = field(default_factory=list)
    proved: bool = False
    depth: Depth = field(default_factory=Depth)
    sections: dict[str, Section] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    fill_index: int = 0
    step: Step = "job"
    disposed: Literal["keep", "throw"] | None = None
    written_path: str | None = None
    pack_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.sections:
            self.sections = {d: Section() for d in DS}
        if not self.order and self.method in DS:
            self.order = fill_order(self.method)

    @property
    def intent(self) -> str:
        return self.job

    @property
    def name(self) -> str:
        return skill_name_from_job(self.job)

    @property
    def current_d(self) -> str | None:
        if not self.order or self.fill_index >= len(self.order):
            return None
        return self.order[self.fill_index]

    def preview_session(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "job": self.job,
            "intent": self.job,
            "when": self.when,
            "not_when": self.not_when,
            "body": self.body,
            "should": self.should,
            "should_not": self.should_not,
            "relevant": self.relevant,
            "not_relevant": self.not_relevant,
            "sections": {k: v.as_dict() for k, v in self.sections.items()},
            "depth": self.depth.as_dict(),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job": self.job,
            "intent": self.job,
            "method": self.method,
            "method_name": method_name(self.method) if self.method in DS else None,
            "when": self.when,
            "not_when": self.not_when,
            "body": self.body,
            "should": list(self.should),
            "should_not": list(self.should_not),
            "relevant": list(self.relevant),
            "not_relevant": list(self.not_relevant),
            "benchmarks": list(self.benchmarks),
            "proved": self.proved,
            "depth": self.depth.as_dict(),
            "sections": {k: v.as_dict() for k, v in self.sections.items()},
            "order": list(self.order),
            "fill_index": self.fill_index,
            "current_d": self.current_d,
            "step": self.step,
            "disposed": self.disposed,
            "written_path": self.written_path,
            "pack_files": list(self.pack_files),
            "pack_tree": pack_tree(self.preview_session()),
            "name": self.name,
            "preview": preview_sections(self.preview_session()),
        }


class Store:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, job: str) -> Session:
        if _empty(job):
            raise GateError("empty_job", "Job is required.")
        session = Session(id=str(uuid.uuid4()), job=job.strip(), step="build")
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise GateError("not_found", "Session not found.") from exc

    def build(
        self,
        session: Session,
        *,
        when: str | None = None,
        not_when: str | None = None,
        body: str | None = None,
        method: str | None = None,
        should: list[str] | None = None,
        should_not: list[str] | None = None,
        relevant: list[str] | None = None,
        not_relevant: list[str] | None = None,
        depth: dict[str, bool] | None = None,
        continue_to_prove: bool = False,
    ) -> Session:
        if session.disposed:
            raise GateError("already_disposed", "Session already disposed.")
        if when is not None:
            session.when = when.strip()
        if not_when is not None:
            session.not_when = not_when.strip()
        if body is not None:
            session.body = body.strip()
        if method is not None:
            if method not in DS:
                raise GateError("bad_method", "Method must be one Academy Fluency 4D.")
            session.method = method
            session.order = fill_order(method)
            session.fill_index = 0
        if should is not None:
            session.should = _clean_list(should)
        if should_not is not None:
            session.should_not = _clean_list(should_not)
        if relevant is not None:
            session.relevant = _clean_list(relevant)
        if not_relevant is not None:
            session.not_relevant = _clean_list(not_relevant)
        if depth is not None:
            session.depth = Depth(
                nested=bool(depth.get("nested")),
                tools=bool(depth.get("tools")),
                scripts=bool(depth.get("scripts")),
            )
        session.proved = False
        session.benchmarks = []
        session.step = "build"
        if continue_to_prove:
            self._require_trigger(session)
            session.step = "prove"
        return session

    def pick_method(self, session: Session, method: str) -> Session:
        return self.build(session, method=method)

    def set_prove(
        self,
        session: Session,
        *,
        when: str,
        not_when: str,
        should: list[str] | None = None,
        should_not: list[str] | None = None,
    ) -> Session:
        session.when = when.strip()
        session.not_when = not_when.strip()
        if should is not None:
            session.should = _clean_list(should)
        if should_not is not None:
            session.should_not = _clean_list(should_not)
        return session

    def prove(
        self,
        session: Session,
        *,
        when: str | None = None,
        not_when: str | None = None,
        should: list[str] | None = None,
        should_not: list[str] | None = None,
        relevant: list[str] | None = None,
        not_relevant: list[str] | None = None,
        continue_to_dispose: bool = False,
    ) -> Session:
        if session.disposed:
            raise GateError("already_disposed", "Session already disposed.")
        if when is not None:
            session.when = when.strip()
        if not_when is not None:
            session.not_when = not_when.strip()
        if should is not None:
            session.should = _clean_list(should)
        if should_not is not None:
            session.should_not = _clean_list(should_not)
        if relevant is not None:
            session.relevant = _clean_list(relevant)
        if not_relevant is not None:
            session.not_relevant = _clean_list(not_relevant)
        self._require_trigger(session)
        if not session.should or not session.should_not:
            raise GateError(
                "empty_benchmarks",
                "Prove needs at least one should-wake and one should-not prompt.",
            )
        if not session.relevant:
            session.relevant = [f"Drafted output for this job: {session.job}"]
        if not session.not_relevant:
            session.not_relevant = ["A 1200-word blog post about our product launch."]
        try:
            session.benchmarks = run_prove(
                job=session.job,
                when=session.when,
                not_when=session.not_when,
                should=session.should,
                should_not=session.should_not,
                relevant=session.relevant,
                not_relevant=session.not_relevant,
            )
        except ProveCLIError as exc:
            raise GateError("cli_failed", str(exc)) from exc
        session.proved = True
        session.step = "dispose" if continue_to_dispose else "prove"
        return session

    def apply_fill(self, session: Session, body: str) -> Session:
        current = session.current_d or session.method or "description"
        session.sections[current] = Section(status="filled", body=body.strip())
        if not session.body:
            session.body = body.strip()
        return session

    def skip_current(self, session: Session) -> Session:
        current = session.current_d
        if not current:
            raise GateError("bad_step", "No current method field to skip.")
        session.sections[current] = Section(status="skipped", body="")
        session.fill_index += 1
        return session

    def keep(self, session: Session, skills_dir: Path) -> Path:
        if session.disposed == "throw":
            raise GateError("already_thrown", "Thrown-away session writes nothing.")
        if session.disposed == "keep":
            raise GateError("already_kept", "Session already kept.")
        self._require_trigger(session, code="empty_trigger")
        if not session.proved:
            raise GateError("not_proved", "Prove the trigger before Keep.")
        path = write_pack(session.preview_session(), skills_dir)
        session.disposed = "keep"
        session.written_path = str(path)
        session.pack_files = [str(p.relative_to(skills_dir)) for p in sorted(path.parent.rglob("*")) if p.is_file()]
        session.step = "done_keep"
        return path

    def throw_away(self, session: Session, skills_dir: Path) -> None:
        """Throw away writes nothing. Disk under skills_dir is unchanged."""
        if session.disposed == "keep" and session.written_path:
            raise GateError("already_kept", "Session already kept.")
        session.disposed = "throw"
        session.written_path = None
        session.pack_files = []
        session.step = "done_throw"

    def _require_trigger(self, session: Session, code: str = "empty_trigger") -> None:
        if _empty(session.when) or _empty(session.not_when):
            raise GateError(
                code,
                "Keep blocked: When and Not when must be non-empty.",
            )
