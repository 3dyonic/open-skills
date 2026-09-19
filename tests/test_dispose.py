from pathlib import Path

import pytest

from app.gate import GateError, Store


def _built(store: Store, job: str = "Draft release notes from PR diffs for the changelog.") -> object:
    session = store.create(job)
    store.build(
        session,
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        body="Draft the notes. Stay on the changelog unit.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
        relevant=["Changelog notes from the PR diff."],
        not_relevant=["A 1200-word blog post about our product launch."],
        continue_to_prove=True,
    )
    return session


def _proved(store: Store) -> object:
    session = _built(store)
    store.prove(session)
    return session


def test_throw_away_writes_zero_skill_files(store: Store, skills_dir: Path) -> None:
    session = _proved(store)
    before = list(p for p in skills_dir.rglob("*") if p.is_file())
    store.throw_away(session, skills_dir)
    after = list(p for p in skills_dir.rglob("*") if p.is_file())
    assert session.disposed == "throw"
    assert session.written_path is None
    assert session.step == "done_throw"
    assert before == []
    assert after == []
    assert list(skills_dir.iterdir()) == []


def test_keep_writes_skill_pack_with_when_and_not_when(store: Store, skills_dir: Path) -> None:
    session = _proved(store)
    path = store.keep(session, skills_dir)
    assert path.exists()
    assert path.name == "SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert "name:" in text
    assert "Use when Release notes from a PR or changelog." in text
    assert "Not when Marketing or blog posts." in text
    assert "## When" in text
    assert "## Not when" in text
    assert session.disposed == "keep"
    assert path.parent.name == session.name


def test_throw_away_after_draft_does_not_create_dir(store: Store, skills_dir: Path) -> None:
    session = _proved(store)
    store.throw_away(session, skills_dir)
    assert list(skills_dir.iterdir()) == []


def test_keep_blocked_before_prove(store: Store, skills_dir: Path) -> None:
    session = _built(store)
    assert session.proved is False
    with pytest.raises(GateError) as exc:
        store.keep(session, skills_dir)
    assert exc.value.code == "not_proved"
    assert list(skills_dir.rglob("SKILL.md")) == []


def test_empty_when_blocks_keep(store: Store, skills_dir: Path) -> None:
    session = store.create("Ship a hotfix checklist.")
    store.build(session, when="", not_when="")
    with pytest.raises(GateError) as exc:
        store.keep(session, skills_dir)
    assert exc.value.code == "empty_trigger"
    assert list(skills_dir.rglob("SKILL.md")) == []
