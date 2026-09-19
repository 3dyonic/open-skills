"""Thin host: wizard UI + server fill + human dispose."""

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
from app.llm import fill_section, refine_prompts
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


app = FastAPI(title="Open Skills", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _http(exc: GateError) -> HTTPException:
    status = 404 if exc.code == "not_found" else 400
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})


class IntentIn(BaseModel):
    intent: str = Field(min_length=1)


class MethodIn(BaseModel):
    method: str


class ProveIn(BaseModel):
    when: str = ""
    not_when: str = ""
    should: list[str] | None = None
    should_not: list[str] | None = None
    continue_to_fill: bool = False


class FillIn(BaseModel):
    action: str


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
def create_session(body: IntentIn) -> dict:
    try:
        session = _store.create(body.intent)
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    try:
        return _store.get(session_id).as_dict()
    except GateError as exc:
        raise _http(exc) from exc


@app.post("/api/sessions/{session_id}/method")
def pick_method(session_id: str, body: MethodIn) -> dict:
    try:
        session = _store.get(session_id)
        _store.pick_method(session, body.method)
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.post("/api/sessions/{session_id}/prove")
def prove(session_id: str, body: ProveIn) -> dict:
    try:
        session = _store.get(session_id)
        _store.set_prove(
            session,
            when=body.when,
            not_when=body.not_when,
            should=body.should,
            should_not=body.should_not,
        )
        if not session.should or not session.should_not:
            should, should_not = refine_prompts(session, _academy)
            session.should = should
            session.should_not = should_not
        if body.continue_to_fill:
            _store.continue_from_prove(session)
            current = session.current_d
            if current and session.sections[current].status == "empty":
                body_text = fill_section(session, current, _academy)
                _store.apply_fill(session, body_text)
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.post("/api/sessions/{session_id}/fill")
def fill(session_id: str, body: FillIn) -> dict:
    try:
        session = _store.get(session_id)
        action = body.action
        if action == "skip":
            _store.skip_current(session)
        elif action == "regen":
            current = session.current_d
            if not current:
                raise GateError("bad_step", "No current D to fill.")
            text = fill_section(session, current, _academy)
            _store.apply_fill(session, text)
        elif action == "continue":
            _store.continue_fill(session)
        else:
            raise GateError("bad_action", "Fill action must be skip, regen, or continue.")
        if session.step == "fill" and session.current_d:
            current = session.current_d
            if session.sections[current].status == "empty":
                text = fill_section(session, current, _academy)
                _store.apply_fill(session, text)
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.post("/api/sessions/{session_id}/accept")
def accept(session_id: str) -> dict:
    try:
        session = _store.get(session_id)
        path = _store.accept(session, skills_dir())
    except GateError as exc:
        raise _http(exc) from exc
    return {**session.as_dict(), "path": str(path)}


@app.post("/api/sessions/{session_id}/reject")
def reject(session_id: str) -> dict:
    try:
        session = _store.get(session_id)
        before = {p for p in skills_dir().rglob("SKILL.md")}
        _store.reject(session, skills_dir())
        after = {p for p in skills_dir().rglob("SKILL.md")}
        if after - before:
            raise GateError("reject_wrote", "Reject must write nothing.")
    except GateError as exc:
        raise _http(exc) from exc
    return session.as_dict()


@app.get("/api/sessions/{session_id}/skill")
def skill_file(session_id: str) -> PlainTextResponse:
    try:
        session = _store.get(session_id)
    except GateError as exc:
        raise _http(exc) from exc
    if session.disposed != "accept" or not session.written_path:
        raise HTTPException(status_code=404, detail={"code": "not_written", "message": "No SKILL.md until Accept."})
    path = Path(session.written_path)
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/api/sessions/{session_id}/preview.md")
def preview_markdown(session_id: str) -> PlainTextResponse:
    try:
        session = _store.get(session_id)
    except GateError as exc:
        raise _http(exc) from exc
    return PlainTextResponse(render_skill_md(session.preview_session()), media_type="text/markdown")
