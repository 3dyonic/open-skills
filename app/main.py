"""Open Skills — skill-authoring playground. Keep writes pack / Throw away writes nothing."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.academy import AcademyCite, fetch_academy_indicators
from app.gate import GateError, Store
from app.llm import draft_build, fill_section
from app.methods import methods_payload
from app.skill_md import render_skill_md

STATIC_DIR = Path(__file__).parent / "static"
_store = Store()
_academy = AcademyCite(
    url="https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators",
    title="The 4 Ds of AI Fluency — Behavioral Indicators",
    fetched=False,
    excerpt="",
)


def skills_dir() -> Path:
    raw = os.environ.get("SKILLS_DIR") or str(Path.home() / ".agents" / "skills")
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_academy(cite: AcademyCite) -> None:
    global _academy
    _academy = cite


@asynccontextmanager
async def lifespan(_app: FastAPI):
    set_academy(fetch_academy_indicators())
    yield


app = FastAPI(title="Open Skills — skill-authoring playground", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _http(exc: GateError) -> HTTPException:
    status = 404 if exc.code == "not_found" else 400
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})


class JobIn(BaseModel):
    job: str = Field(default="")
    intent: str = Field(default="")

    def text(self) -> str:
        return (self.job or self.intent).strip()


class BuildIn(BaseModel):
    when: str | None = None
    not_when: str | None = None
    body: str | None = None
    method: str | None = None
    should: list[str] | None = None
    should_not: list[str] | None = None
    near_miss: list[str] | None = None
    relevant: list[str] | None = None
    not_relevant: list[str] | None = None
    with_skill: list[str] | None = None
    without_skill: list[str] | None = None
    runs: int | None = None
    depth: dict[str, bool] | None = None
    continue_to_prove: bool = False
    fill_action: str | None = None


class ProveIn(BaseModel):
    when: str | None = None
    not_when: str | None = None
    should: list[str] | None = None
    should_not: list[str] | None = None
    near_miss: list[str] | None = None
    relevant: list[str] | None = None
    not_relevant: list[str] | None = None
    with_skill: list[str] | None = None
    without_skill: list[str] | None = None
    runs: int | None = None
    continue_to_dispose: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "open-skills"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/methods")
def api_methods() -> dict:
    return methods_payload(_academy.quotes)


@app.get("/api/academy")
def api_academy() -> dict:
    return _academy.as_dict()


@app.post("/api/sessions")
def create_session(body: JobIn) -> dict:
    try:
        session = _store.create(body.text())
        draft_build(session, _academy)
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    try:
        return _store.get(session_id).as_dict()
    except GateError as exc:
        raise _http(exc) from exc


@app.post("/api/sessions/{session_id}/build")
def build(session_id: str, body: BuildIn) -> dict:
    try:
        session = _store.get(session_id)
        if body.fill_action == "skip":
            _store.skip_current(session)
        elif body.fill_action == "regen":
            current = session.current_d or session.method or "description"
            text = fill_section(session, current, _academy)
            _store.apply_fill(session, text)
        _store.build(
            session,
            when=body.when,
            not_when=body.not_when,
            body=body.body,
            method=body.method,
            should=body.should,
            should_not=body.should_not,
            near_miss=body.near_miss,
            relevant=body.relevant,
            not_relevant=body.not_relevant,
            with_skill=body.with_skill,
            without_skill=body.without_skill,
            runs=body.runs,
            depth=body.depth,
            continue_to_prove=body.continue_to_prove,
        )
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.post("/api/sessions/{session_id}/prove")
def prove(session_id: str, body: ProveIn) -> dict:
    try:
        session = _store.get(session_id)
        _store.prove(
            session,
            when=body.when,
            not_when=body.not_when,
            should=body.should,
            should_not=body.should_not,
            near_miss=body.near_miss,
            relevant=body.relevant,
            not_relevant=body.not_relevant,
            with_skill=body.with_skill,
            without_skill=body.without_skill,
            runs=body.runs,
            continue_to_dispose=body.continue_to_dispose,
        )
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.post("/api/sessions/{session_id}/keep")
def keep(session_id: str) -> dict:
    try:
        session = _store.get(session_id)
        path = _store.keep(session, skills_dir())
    except GateError as exc:
        raise _http(exc) from exc
    return {**session.as_dict(), "path": str(path)}


@app.post("/api/sessions/{session_id}/throw")
def throw_away(session_id: str) -> dict:
    try:
        session = _store.get(session_id)
        before = {p for p in skills_dir().rglob("*") if p.is_file()}
        _store.throw_away(session, skills_dir())
        after = {p for p in skills_dir().rglob("*") if p.is_file()}
        if after - before:
            raise GateError("throw_wrote", "Throw away must write nothing.")
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.get("/api/sessions/{session_id}/skill")
def skill_file(session_id: str) -> PlainTextResponse:
    try:
        session = _store.get(session_id)
    except GateError as exc:
        raise _http(exc) from exc
    if session.disposed != "keep" or not session.written_path:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_written", "message": "No skill pack until Keep."},
        )
    path = Path(session.written_path)
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/api/sessions/{session_id}/preview.md")
def preview_markdown(session_id: str) -> PlainTextResponse:
    try:
        session = _store.get(session_id)
    except GateError as exc:
        raise _http(exc) from exc
    return PlainTextResponse(render_skill_md(session.preview_session()), media_type="text/markdown")
