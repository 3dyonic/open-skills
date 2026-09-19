from pathlib import Path

from app.gate import Store
from app.skill_md import preview_sections


def test_skip_appears_as_skipped_in_preview(store: Store) -> None:
    session = store.create("Capture the hotfix ship checklist.")
    store.build(session, method="delegation")
    store.apply_fill(session, "Delegation draft")
    assert session.current_d == "delegation"
    store.skip_current(session)
    preview = preview_sections(session.preview_session())
    by_id = {row["id"]: row for row in preview}
    assert by_id["delegation"]["badge"] == "Skipped"
    assert by_id["delegation"]["status"] == "skipped"
    assert by_id["delegation"]["body"] == "—"
    names = [row["name"] for row in preview]
    assert names == ["Delegation", "Description", "Discernment", "Diligence"]


def test_http_empty_when_blocks_prove_and_keep(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"job": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(f"/api/sessions/{sid}/build", json={"when": "", "not_when": ""})
    blocked = client.post(
        f"/api/sessions/{sid}/prove",
        json={"when": "", "not_when": "", "should": ["a"], "should_not": ["b"]},
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["code"] == "empty_trigger"
    accept = client.post(f"/api/sessions/{sid}/keep")
    assert accept.status_code == 400
    assert accept.json()["detail"]["code"] == "empty_trigger"
    assert list(skills_dir.rglob("SKILL.md")) == []


def test_ui_uses_keep_throw_away_not_accept_reject() -> None:
    html = Path("app/static/index.html").read_text(encoding="utf-8")
    js = Path("app/static/app.js").read_text(encoding="utf-8")
    assert "Keep — write skill pack" in html
    assert "Throw away — write nothing" in html
    assert "Accept — write" not in html
    assert "Reject — write" not in html
    assert "/keep" in js
    assert "/throw" in js


def test_ui_is_skill_authoring_playground_not_workshop() -> None:
    html = Path("app/static/index.html").read_text(encoding="utf-8")
    js = Path("app/static/app.js").read_text(encoding="utf-8")
    assert "Open Skills — skill-authoring playground" in html
    assert "skill-authoring playground" in html
    assert "WORKSHOP" not in html
    assert "Workshop" not in html
    assert "workshop" not in html.lower()
    assert "start-workshop" not in js
    assert "start-continue" in js
    assert "start-author" not in js
    assert "Run check" in html
    assert "id=\"run-check\"" in html
    assert "Prove trigger" not in html
    assert "with-skill" in html
    assert "near-miss" in html
    assert "evidence" in js


def test_ui_cites_lean_frames_not_opus() -> None:
    html = Path("app/static/index.html").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Say the job in plain words" in html
    assert "You’ve proved the trigger. Decide." in html
    assert "Two outcomes — same frame" in html
    assert "Keep/Throw" in Path("app/static/app.js").read_text(encoding="utf-8")
    assert "node-id=6-5" in readme
    assert "node-id=6-68" in readme
    assert "node-id=6-107" in readme
    assert "node-id=1-2" not in readme
    assert "node-id=4-2" not in readme
    assert "I learned" not in html


def test_no_old_thin_gate_figma() -> None:
    roots = [Path("app"), Path("README.md")]
    files = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(p for p in root.rglob("*") if p.suffix in {".py", ".html", ".js", ".css", ".md"})
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "YTDZYEp7b1ul5lNSAGYh0e" not in text
        assert "Accept — write SKILL.md" not in text
