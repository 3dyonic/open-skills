from pathlib import Path

from app.gate import GateError, Store


def _ready(store: Store, intent: str = "Capture the hotfix ship checklist.") :
    session = store.create(intent)
    store.pick_method(session, "delegation")
    store.set_prove(session, when="Teammate asks how to ship a hotfix.", not_when="Routine deploys.")
    store.continue_from_prove(session)
    return session


def test_reject_writes_zero_skill_files(store: Store, skills_dir: Path) -> None:
    session = _ready(store)
    store.apply_fill(session, "draft")
    before = list(skills_dir.rglob("SKILL.md"))
    store.reject(session, skills_dir)
    after = list(skills_dir.rglob("SKILL.md"))
    assert session.disposed == "reject"
    assert session.written_path is None
    assert session.step == "done_reject"
    assert before == []
    assert after == []
    assert not (skills_dir / session.name / "SKILL.md").exists()


def test_accept_writes_skill_md_with_when_and_not_when(store: Store, skills_dir: Path) -> None:
    session = _ready(store)
    store.apply_fill(session, "Agent drafts checklist.")
    path = store.accept(session, skills_dir)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert path.name == "SKILL.md"
    assert "name:" in text
    assert "Use when Teammate asks how to ship a hotfix." in text
    assert "Not when Routine deploys." in text
    assert "## When" in text
    assert "## Not when" in text
    assert session.disposed == "accept"


def test_reject_after_draft_does_not_create_dir(store: Store, skills_dir: Path) -> None:
    session = _ready(store)
    store.reject(session, skills_dir)
    assert list(skills_dir.iterdir()) == []
