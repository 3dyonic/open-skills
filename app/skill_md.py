"""agentskills.io SKILL.md shape: name + description (when / not when) + body."""

from __future__ import annotations

import re
from typing import Any

from app.methods import METHOD_CARDS

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "skill") -> str:
    s = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    s = s[:64].strip("-")
    return s or fallback


def skill_name_from_intent(intent: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", intent) if w]
    if not words:
        return "untitled-skill"
    # Prefer a short job slug from the first meaningful clause.
    return slugify(" ".join(words[:8]), fallback="untitled-skill")


def description_field(intent: str, when: str, not_when: str) -> str:
    job = " ".join((intent or "").split())
    when_s = " ".join((when or "").split())
    not_s = " ".join((not_when or "").split())
    desc = f"{job} Use when {when_s}. Not when {not_s}."
    if len(desc) > 1024:
        desc = desc[:1021] + "..."
    return desc


def render_skill_md(session: dict[str, Any]) -> str:
    name = session["name"]
    description = description_field(session["intent"], session["when"], session["not_when"])
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "---",
        "",
        f"# {name}",
        "",
        "## When",
        "",
        session["when"].strip(),
        "",
        "## Not when",
        "",
        session["not_when"].strip(),
        "",
    ]
    should = session.get("should") or []
    should_not = session.get("should_not") or []
    if should or should_not:
        lines.extend(["## Trigger-proof prompts", ""])
        for item in should:
            lines.append(f"- should: {item}")
        for item in should_not:
            lines.append(f"- should-not: {item}")
        lines.append("")

    sections = session.get("sections") or {}
    for card in METHOD_CARDS:
        did = card["id"]
        sec = sections.get(did) or {}
        lines.append(f"## {card['name']}")
        lines.append("")
        if sec.get("status") == "skipped":
            lines.append("Skipped")
        else:
            body = (sec.get("body") or "").strip()
            lines.append(body if body else "—")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def preview_sections(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Read-only preview model. Skipped Ds are labeled Skipped."""
    sections = session.get("sections") or {}
    out = []
    for card in METHOD_CARDS:
        sec = sections.get(card["id"]) or {}
        skipped = sec.get("status") == "skipped"
        out.append(
            {
                "id": card["id"],
                "name": card["name"],
                "status": "skipped" if skipped else (sec.get("status") or "empty"),
                "badge": "Skipped" if skipped else None,
                "body": "—" if skipped else (sec.get("body") or "—"),
            }
        )
    return out
