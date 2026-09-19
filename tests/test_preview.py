from app.gate import Store
from app.skill_md import preview_sections


def test_skip_appears_as_skipped_in_preview(store: Store) -> None:
    session = store.create("Capture the hotfix ship checklist.")
    store.pick_method(session, "delegation")
    store.set_prove(session, when="Hotfix ask.", not_when="Routine deploy.")
    store.continue_from_prove(session)
    store.apply_fill(session, "Delegation draft")
    store.continue_fill(session)
    # Description is next after Delegation spine
    assert session.current_d == "description"
    store.skip_current(session)
    preview = preview_sections(session.preview_session())
    by_id = {row["id"]: row for row in preview}
    assert by_id["description"]["badge"] == "Skipped"
    assert by_id["description"]["status"] == "skipped"
    assert by_id["description"]["body"] == "—"
    assert by_id["delegation"]["badge"] is None
    names = [row["name"] for row in preview]
    assert names == ["Delegation", "Description", "Discernment", "Diligence"]


def test_http_skip_preview_and_reject(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"intent": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(f"/api/sessions/{sid}/method", json={"method": "delegation"})
    client.post(
        f"/api/sessions/{sid}/prove",
        json={"when": "Hotfix ask.", "not_when": "Docs only.", "continue_to_fill": True},
    )
    # skip current (delegation, already auto-filled)
    client.post(f"/api/sessions/{sid}/fill", json={"action": "skip"})
    # skip remaining to preview
    for _ in range(3):
        session = client.get(f"/api/sessions/{sid}").json()
        if session["step"] == "preview":
            break
        client.post(f"/api/sessions/{sid}/fill", json={"action": "skip"})
    session = client.get(f"/api/sessions/{sid}").json()
    assert session["step"] == "preview"
    skipped = [row for row in session["preview"] if row["badge"] == "Skipped"]
    assert skipped
    assert all(row["badge"] == "Skipped" for row in skipped)

    reject = client.post(f"/api/sessions/{sid}/reject")
    assert reject.status_code == 200
    assert reject.json()["disposed"] == "reject"
    assert list(skills_dir.rglob("SKILL.md")) == []


def test_http_accept_blocked_when_empty(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"intent": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(f"/api/sessions/{sid}/method", json={"method": "delegation"})
    blocked = client.post(
        f"/api/sessions/{sid}/prove",
        json={"when": "", "not_when": "", "continue_to_fill": True},
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["code"] == "empty_trigger"
    accept = client.post(f"/api/sessions/{sid}/accept")
    assert accept.status_code == 400
    assert accept.json()["detail"]["code"] == "empty_trigger"
    assert list(skills_dir.rglob("SKILL.md")) == []
