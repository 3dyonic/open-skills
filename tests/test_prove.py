from app.gate import Store
from app.prove import evaluate_benchmarks


def test_teachable_why_pass_fail_surfaced(store: Store) -> None:
    session = store.create("Draft release notes from PR diffs for the changelog.")
    store.build(
        session,
        when="Release notes from a PR or changelog.",
        not_when="Marketing, blog posts, or product launch prose.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=[
            "Write a blog post about our product launch.",
            "Summarize this meeting for the team.",
        ],
        continue_to_prove=True,
    )
    store.prove(session)
    assert session.proved is True
    assert session.benchmarks
    assert all(row["why"].startswith("WHY:") for row in session.benchmarks)
    assert all(row["teach"] for row in session.benchmarks)
    assert all(row["verdict"] for row in session.benchmarks)
    badges = {row["badge"] for row in session.benchmarks}
    assert "SHOULD WAKE" in badges
    assert "SHOULD NOT" in badges
    assert all(row["passed"] for row in session.benchmarks)


def test_vague_wake_teaches_failed_case(store: Store) -> None:
    session = store.create("Summarize things for people.")
    store.build(
        session,
        when="When someone asks you to summarize.",
        not_when="Nothing in particular.",
        should=["Summarize the weekly notes."],
        should_not=["Summarize this meeting for the team."],
        continue_to_prove=True,
    )
    store.prove(session)
    failed = [row for row in session.benchmarks if row["badge"] == "FAILED · TEACH"]
    assert failed
    assert any("vague" in row["why"].lower() or "wrong job" in row["verdict"].lower() for row in failed)
    assert all(row["why"] and row["teach"] for row in failed)


def test_evaluate_benchmarks_direct() -> None:
    rows = evaluate_benchmarks(
        job="Draft release notes from PR diffs for the changelog.",
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
    )
    assert rows[0]["badge"] == "SHOULD WAKE"
    assert rows[1]["badge"] == "SHOULD NOT"
    assert rows[0]["why"].startswith("WHY:")
    assert rows[1]["why"].startswith("WHY:")
