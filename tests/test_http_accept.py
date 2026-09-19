def test_http_accept_writes_skill_md(client, skills_dir) -> None:
    created = client.post("/api/sessions", json={"intent": "Capture hotfix checklist."}).json()
    sid = created["id"]
    client.post(f"/api/sessions/{sid}/method", json={"method": "delegation"})
    proved = client.post(
        f"/api/sessions/{sid}/prove",
        json={"when": "Teammate asks how to ship a hotfix.", "not_when": "Routine deploys.", "continue_to_fill": True},
    )
    assert proved.status_code == 200
    for _ in range(4):
        session = client.get(f"/api/sessions/{sid}").json()
        if session["step"] == "preview":
            break
        cont = client.post(f"/api/sessions/{sid}/fill", json={"action": "continue"})
        assert cont.status_code == 200
    session = client.get(f"/api/sessions/{sid}").json()
    assert session["step"] == "preview"
    accepted = client.post(f"/api/sessions/{sid}/accept")
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["disposed"] == "accept"
    files = list(skills_dir.rglob("SKILL.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "Use when Teammate asks how to ship a hotfix." in text
    assert "Not when Routine deploys." in text
    assert text.startswith("---\nname: ")
