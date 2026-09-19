from pathlib import Path

from app.gate import Store


def _proved(store: Store, *, depth: dict[str, bool] | None = None):
    session = store.create("Draft release notes from PR diffs for the changelog.")
    store.build(
        session,
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        body="Draft the notes.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
        depth=depth or {"nested": False, "tools": False, "scripts": False},
        continue_to_prove=True,
    )
    store.prove(session)
    return session


def test_simple_keep_does_not_force_nesting_tools_scripts(store: Store, skills_dir: Path) -> None:
    session = _proved(store)
    path = store.keep(session, skills_dir)
    pack = path.parent
    assert (pack / "SKILL.md").exists()
    assert not (pack / "scripts").exists()
    assert not (pack / "nested").exists()
    assert not (pack / "tools").exists()
    assert "simple path" in "\n".join(session.as_dict()["pack_tree"])


def test_keep_with_scripts_stub(store: Store, skills_dir: Path) -> None:
    session = _proved(store, depth={"nested": False, "tools": False, "scripts": True})
    store.keep(session, skills_dir)
    script = skills_dir / session.name / "scripts" / "draft.sh"
    assert script.exists()
    assert "stub" in script.read_text(encoding="utf-8").lower()


def test_throw_away_with_depth_open_still_writes_nothing(store: Store, skills_dir: Path) -> None:
    session = _proved(store, depth={"nested": True, "tools": True, "scripts": True})
    store.throw_away(session, skills_dir)
    assert list(skills_dir.iterdir()) == []
