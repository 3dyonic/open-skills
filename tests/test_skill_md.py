from app.skill_md import description_field, render_skill_md, skill_name_from_intent


def test_skill_md_has_name_and_when_not_when() -> None:
    session = {
        "name": "hotfix-ship-checklist",
        "intent": "Capture the hotfix ship checklist so I stop pasting Slack.",
        "when": "Teammate asks how to ship a hotfix.",
        "not_when": "Routine feature deploys.",
        "should": ["Walk me through our hotfix ship checklist."],
        "should_not": ["How do I write a product brief?"],
        "sections": {
            "delegation": {"status": "filled", "body": "Agent drafts; human disposes."},
            "description": {"status": "skipped", "body": ""},
            "discernment": {"status": "filled", "body": "Refuse if severity unknown."},
            "diligence": {"status": "filled", "body": "Short body · more in references/"},
        },
    }
    md = render_skill_md(session)
    assert md.startswith("---\nname: hotfix-ship-checklist\n")
    assert "Use when Teammate asks how to ship a hotfix." in md
    assert "Not when Routine feature deploys." in md
    assert "## When\n\nTeammate asks how to ship a hotfix." in md
    assert "## Not when\n\nRoutine feature deploys." in md
    assert "## Description\n\nSkipped" in md


def test_description_includes_when_and_not_when() -> None:
    desc = description_field("Ship hotfixes.", "ask for hotfix", "docs only")
    assert "Use when ask for hotfix" in desc
    assert "Not when docs only" in desc
    assert len(desc) <= 1024


def test_slug_from_intent() -> None:
    assert skill_name_from_intent("Hotfix ship checklist please") == "hotfix-ship-checklist-please"
    assert skill_name_from_intent("") == "untitled-skill"
