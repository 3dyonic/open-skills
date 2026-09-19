"""Durable skill pack — written only on Keep."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.skill_md import render_skill_md

SCRIPTS_STUB = """#!/bin/sh
# Progressive stub — open when the job needs a runnable helper.
# Day-1: not executed by the workshop. Keep the SKILL.md body lean.
set -eu
echo "open-skills scripts stub"
"""

NESTED_STUB = """# Nested sub-skill (stub)

Opens only when the root job needs depth. Day-1: not forced on the simple path.
"""

TOOLS_STUB = """# Tools (stub)

Attached capabilities the skill may call. Steered in Build; not a second product.
"""


def pack_root(skills_dir: Path, name: str) -> Path:
    return skills_dir / name


def write_pack(session: dict[str, Any], skills_dir: Path) -> Path:
    """Write an agentskills.io pack. Caller must have already gated Keep."""
    root = pack_root(skills_dir, session["name"])
    root.mkdir(parents=True, exist_ok=True)
    skill = root / "SKILL.md"
    skill.write_text(render_skill_md(session), encoding="utf-8")

    depth = session.get("depth") or {}
    if depth.get("scripts"):
        scripts = root / "scripts"
        scripts.mkdir(exist_ok=True)
        script = scripts / "draft.sh"
        script.write_text(SCRIPTS_STUB, encoding="utf-8")
        script.chmod(0o755)
    if depth.get("nested"):
        nested = root / "nested"
        nested.mkdir(exist_ok=True)
        (nested / "SKILL.md").write_text(NESTED_STUB, encoding="utf-8")
    if depth.get("tools"):
        tools = root / "tools"
        tools.mkdir(exist_ok=True)
        (tools / "README.md").write_text(TOOLS_STUB, encoding="utf-8")
    return skill


def pack_tree(session: dict[str, Any]) -> list[str]:
    """Preview lines for the pack that Keep would write."""
    name = session.get("name") or "skill"
    depth = session.get("depth") or {}
    lines = [f"{name}/", "SKILL.md"]
    extras: list[tuple[str, list[str]]] = []
    if depth.get("nested"):
        extras.append(("nested/", ["SKILL.md"]))
    if depth.get("scripts"):
        extras.append(("scripts/", ["draft.sh"]))
    if depth.get("tools"):
        extras.append(("tools/", ["README.md"]))
    if not extras:
        lines.append("(nested / tools / scripts closed — simple path)")
        return lines
    last = len(extras) - 1
    for i, (folder, children) in enumerate(extras):
        branch = "└── " if i == last else "├── "
        lines.append(f"{branch}{folder}")
        for child in children:
            child_branch = "    └── " if i == last else "│   └── "
            lines.append(f"{child_branch}{child}")
    return lines


def list_durable_skill_files(skills_dir: Path) -> list[Path]:
    if not skills_dir.exists():
        return []
    return sorted(p for p in skills_dir.rglob("*") if p.is_file())
