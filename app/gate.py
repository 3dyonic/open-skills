"""Thin-gate contracts: prove-trigger, skip visibility, Accept/Reject dispose."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from app.methods import DS, fill_order, method_name
from app.skill_md import preview_sections, render_skill_md, skill_name_from_intent

Step = Literal[
    "intent",
    "methods",
    "prove",
    "fill",
    "preview",
    "done_accept",
    "done_reject",
]


class GateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _empty(value: str | None) -> bool:
    return not (value or "").strip()


@dataclass
class Section:
    status: Literal["empty", "filled", "skipped"] = "empty"
    body: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "body": self.body}


@dataclass
class Session:
    id: str
    intent: str = ""
    method: str | None = None
    when: str = ""
    not_when: str = ""
    should: list[str] = field(default_factory=list)
    should_not: list[str] = field(default_factory=list)
    sections: dict[str, Section] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    fill_index: int = 0
    step: Step = "intent"
    disposed: Literal["accept", "reject"] | None = None
    written_path: str | None = None

    def __post_init__(self) -> None:
        if not self.sections:
            self.sections = {d: Section() for d in DS}

    @property
    def name(self) -> str:
        return skill_name_from_intent(self.intent)

    @property
    def current_d(self) -> str | None:
        if not self.order or self.fill_index >= len(self.order):
            return None
        return self.order[self.fill_index]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "intent": self.intent,
            "method": self.method,
            "method_name": method_name(self.method) if self.method else None,
            "when": self.when,
            "not_when": self.not_when,
            "should": list(self.should),
            "should_not": list(self.should_not),
            "sections": {k: v.as_dict() for k, v in self.sections.items()},
            "order": list(self.order),
            "fill_index": self.fill_index,
            "current_d": self.current_d,
            "step": self.step,
            "disposed": self.disposed,
            "written_path": self.written_path,
            "name": self.name,
            "preview": preview_sections(self.preview_session()),
        }

    def preview_session(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "intent": self.intent,
            "when": self.when,
            "not_when": self.not_when,
            "should": self.should,
            "should_not": self.should_not,
            "sections": {k: v.as_dict() for k, v in self.sections.items()},
        }


class Store:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, intent: str) -> Session:
        if _empty(intent):
            raise GateError("empty_intent", "Intent is required.")
        session = Session(id=str(uuid.uuid4()), intent=intent.strip(), step="methods")
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise GateError("not_found", "Session not found.") from exc

    def pick_method(self, session: Session, method: str) -> Session:
        if method not in DS:
            raise GateError("bad_method", "Must pick one Academy Fluency 4D.")
        session.method = method
        session.order = fill_order(method)
        session.fill_index = 0
        session.step = "prove"
        return session

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
            session.should = [s.strip() for s in should if s.strip()]
        if should_not is not None:
            session.should_not = [s.strip() for s in should_not if s.strip()]
        return session

    def continue_from_prove(self, session: Session) -> Session:
        self._require_trigger(session)
        if not session.method:
            raise GateError("bad_method", "Must pick one Academy Fluency 4D.")
        session.step = "fill"
        session.fill_index = 0
        return session

    def skip_current(self, session: Session) -> Session:
        current = self._require_fill(session)
        session.sections[current] = Section(status="skipped", body="")
        return self._advance_fill(session)

    def apply_fill(self, session: Session, body: str) -> Session:
        current = self._require_fill(session)
        session.sections[current] = Section(status="filled", body=body.strip())
        return session

    def continue_fill(self, session: Session) -> Session:
        current = self._require_fill(session)
        sec = session.sections[current]
        if sec.status == "empty":
            raise GateError("empty_fill", "Fill, skip, or regenerate this D first.")
        return self._advance_fill(session)

    def accept(self, session: Session, skills_dir: Path) -> Path:
        if session.disposed == "reject":
            raise GateError("already_rejected", "Rejected session writes nothing.")
        self._require_trigger(session, code="empty_trigger")
        markdown = render_skill_md(session.preview_session())
        dest = skills_dir / session.name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(markdown, encoding="utf-8")
        session.disposed = "accept"
        session.written_path = str(dest)
        session.step = "done_accept"
        return dest

    def reject(self, session: Session, skills_dir: Path) -> None:
        """Reject writes nothing. Disk under skills_dir is unchanged."""
        target = skills_dir / session.name / "SKILL.md"
        if session.disposed == "accept" and session.written_path:
            raise GateError("already_accepted", "Session already accepted.")
        # Fail closed: never create or touch a skill file on reject.
        if target.exists() and session.disposed != "accept":
            # A leftover from another session with the same slug is not ours to delete.
            pass
        session.disposed = "reject"
        session.written_path = None
        session.step = "done_reject"

    def _advance_fill(self, session: Session) -> Session:
        session.fill_index += 1
        if session.fill_index >= len(session.order):
            session.step = "preview"
        return session

    def _require_fill(self, session: Session) -> str:
        if session.step not in {"fill", "preview"}:
            raise GateError("bad_step", "Fill happens after prove-trigger.")
        current = session.current_d
        if not current:
            raise GateError("bad_step", "No current D to fill.")
        return current

    def _require_trigger(self, session: Session, code: str = "empty_trigger") -> None:
        if _empty(session.when) or _empty(session.not_when):
            raise GateError(
                code,
                "Accept blocked: When and Not when must be non-empty.",
            )
