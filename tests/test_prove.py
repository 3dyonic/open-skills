from pathlib import Path

import pytest

from app.gate import GateError, Store


def test_empty_when_blocks_continue_to_fill(store: Store) -> None:
    session = store.create("Ship a hotfix checklist.")
    store.pick_method(session, "delegation")
    store.set_prove(session, when="", not_when="Routine deploys.")
    with pytest.raises(GateError) as exc:
        store.continue_from_prove(session)
    assert exc.value.code == "empty_trigger"


def test_empty_when_or_not_when_blocks_accept(store: Store, skills_dir: Path) -> None:
    session = store.create("Ship a hotfix checklist.")
    store.pick_method(session, "delegation")
    store.set_prove(session, when="", not_when="")
    with pytest.raises(GateError) as exc:
        store.accept(session, skills_dir)
    assert exc.value.code == "empty_trigger"
    assert list(skills_dir.rglob("SKILL.md")) == []

    store.set_prove(session, when="On hotfix ask.", not_when="")
    with pytest.raises(GateError):
        store.accept(session, skills_dir)
    assert list(skills_dir.rglob("SKILL.md")) == []

    store.set_prove(session, when="On hotfix ask.", not_when="Docs-only.")
    path = store.accept(session, skills_dir)
    assert path.exists()


def test_must_pick_method(store: Store) -> None:
    session = store.create("Ship a hotfix checklist.")
    with pytest.raises(GateError) as exc:
        store.pick_method(session, "marketplace")
    assert exc.value.code == "bad_method"
