def test_http_keep_writes_skill_pack(client, skills_dir) -> None:
    created = client.post(
        "/api/sessions",
        json={"job": "Draft release notes from PR diffs for the changelog."},
    ).json()
    sid = created["id"]
    built = client.post(
        f"/api/sessions/{sid}/build",
        json={
            "when": "Release notes from a PR or changelog.",
            "not_when": "Marketing or blog posts.",
            "body": "Draft the notes.",
            "should": ["Draft release notes from this PR diff for the changelog."],
            "should_not": ["Write a blog post about our product launch."],
            "relevant": ["Changelog notes from the PR diff."],
            "not_relevant": ["A 1200-word blog post about our product launch."],
            "continue_to_prove": True,
        },
    )
    assert built.status_code == 200
    proved = client.post(
        f"/api/sessions/{sid}/prove",
        json={"continue_to_dispose": True},
    )
    assert proved.status_code == 200
    assert proved.json()["proved"] is True
    assert proved.json()["benchmarks"]
    families = {row["family"] for row in proved.json()["benchmarks"]}
    assert families == {"wake", "output"}
    report = proved.json()["prove_report"]
    assert "wake" in report and "output" in report
    assert "composite_0_100" not in report
    assert all(row["evidence"]["fixture"] for row in proved.json()["benchmarks"])
    kept = client.post(f"/api/sessions/{sid}/keep")
    assert kept.status_code == 200
    body = kept.json()
    assert body["disposed"] == "keep"
    files = list(skills_dir.rglob("SKILL.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "Use when Release notes from a PR or changelog." in text
    assert "Not when Marketing or blog posts." in text
    assert text.startswith("---\nname: ")


def test_http_keep_blocked_before_prove(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"job": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(
        f"/api/sessions/{sid}/build",
        json={"when": "Hotfix ask.", "not_when": "Docs only."},
    )
    blocked = client.post(f"/api/sessions/{sid}/keep")
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["code"] == "not_proved"
    assert list(skills_dir.rglob("SKILL.md")) == []


def test_http_throw_away_writes_nothing(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"job": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(
        f"/api/sessions/{sid}/build",
        json={
            "when": "Hotfix ask.",
            "not_when": "Docs only.",
            "should": ["Walk me through the hotfix checklist."],
            "should_not": ["Write a blog post about our product launch."],
            "relevant": ["Hotfix checklist: confirm severity, open the runbook."],
            "not_relevant": ["A 1200-word blog post about our product launch."],
            "continue_to_prove": True,
        },
    )
    client.post(f"/api/sessions/{sid}/prove", json={"continue_to_dispose": True})
    thrown = client.post(f"/api/sessions/{sid}/throw")
    assert thrown.status_code == 200
    assert thrown.json()["disposed"] == "throw"
    assert list(p for p in skills_dir.rglob("*") if p.is_file()) == []
