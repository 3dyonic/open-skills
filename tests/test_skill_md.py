from app.skill_md import description_field, render_skill_md, skill_name_from_job


def test_skill_md_has_name_and_when_not_when() -> None:
    session = {
        "name": "hotfix-ship-checklist",
        "job": "Capture the hotfix ship checklist so I stop pasting Slack.",
        "when": "Teammate asks how to ship a hotfix.",
        "not_when": "Routine feature deploys.",
        "body": "Confirm severity. Open the runbook.",
        "should": ["Walk me through our hotfix ship checklist."],
        "should_not": ["How do I write a product brief?"],
        "sections": {},
        "depth": {},
    }
    md = render_skill_md(session)
    assert md.startswith("---\nname: hotfix-ship-checklist\n")
    assert "Use when Teammate asks how to ship a hotfix." in md
    assert "Not when Routine feature deploys." in md
    assert "## When\n\nTeammate asks how to ship a hotfix." in md
    assert "## Not when\n\nRoutine feature deploys." in md
    assert "## Steps\n\nConfirm severity. Open the runbook." in md


def test_description_includes_when_and_not_when() -> None:
    desc = description_field("Ship hotfixes.", "ask for hotfix", "docs only")
    assert "Use when ask for hotfix" in desc
    assert "Not when docs only" in desc
    assert len(desc) <= 1024


def test_slug_from_job() -> None:
    assert skill_name_from_job("Hotfix ship checklist please") == "hotfix-ship-checklist-please"
    assert skill_name_from_job("") == "untitled-skill"
