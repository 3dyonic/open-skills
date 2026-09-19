from app.gate import Store
from app.prove import run_prove
from app.scheme import ProveRequest
from app.cli import run_prove as cli_prove


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
        relevant=["Changelog notes drafted from the PR diff."],
        not_relevant=["A 1200-word blog post about our product launch."],
        continue_to_prove=True,
    )
    store.prove(session)
    assert session.proved is True
    assert session.benchmarks
    assert all(row["why"].startswith("WHY:") for row in session.benchmarks)
    assert all(row["teach"] for row in session.benchmarks)
    families = {row["family"] for row in session.benchmarks}
    assert families == {"wake", "output"}
    badges = {row["badge"] for row in session.benchmarks}
    assert "SHOULD WAKE" in badges
    assert "SHOULD NOT" in badges
    assert "RELEVANT" in badges
    assert "NOT RELEVANT" in badges
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
    assert any(row["family"] == "wake" for row in failed)
    assert all(row["why"] and row["teach"] for row in failed)


def test_run_prove_shells_out_to_cli() -> None:
    rows = run_prove(
        job="Draft release notes from PR diffs for the changelog.",
        when="Release notes from a PR or changelog.",
        not_when="Marketing or blog posts.",
        should=["Draft release notes from this PR diff for the changelog."],
        should_not=["Write a blog post about our product launch."],
        relevant=["Changelog notes from the PR diff."],
        not_relevant=["A 1200-word blog post about our product launch."],
    )
    assert {row["family"] for row in rows} == {"wake", "output"}
    wake = [row for row in rows if row["family"] == "wake"]
    output = [row for row in rows if row["family"] == "output"]
    assert wake[0]["badge"] == "SHOULD WAKE"
    assert wake[1]["badge"] == "SHOULD NOT"
    assert output[0]["badge"] == "RELEVANT"
    assert output[1]["badge"] == "NOT RELEVANT"


def test_cli_prove_scheme_direct() -> None:
    resp = cli_prove(
        ProveRequest(
            job="Draft release notes from PR diffs for the changelog.",
            when="Release notes from a PR or changelog.",
            not_when="Marketing or blog posts.",
            should=["Draft release notes from this PR diff for the changelog."],
            should_not=["Write a blog post about our product launch."],
            relevant=["Changelog notes from the PR diff."],
            not_relevant=["A 1200-word blog post about our product launch."],
        )
    )
    assert resp.via == "cli"
    assert {c.family for c in resp.cases} == {"wake", "output"}
