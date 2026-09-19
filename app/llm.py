"""Server-only LLM fill/refine. Human disposes. No client-side model calls."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.academy import AcademyCite
from app.gate import Session
from app.methods import ACADEMY_INDICATORS_URL, method_name

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _quotes_block(cite: AcademyCite, method_id: str) -> str:
    quotes = cite.quotes.get(method_id) or []
    if quotes:
        return "\n".join(f"- {q}" for q in quotes)
    if cite.excerpt:
        return f"(page excerpt, no per-D list parsed)\n{cite.excerpt}"
    return (
        f"No indicator list parsed from {ACADEMY_INDICATORS_URL}. "
        "Do not invent 4D method prose. Write only from the job + this D's name."
    )


def stub_fill(session: Session, method_id: str, cite: AcademyCite) -> str:
    """Deterministic fill used in tests and when no LLM key is set.

    Uses the job + cited Academy text only. Does not invent 4D essays.
    """
    quoted = cite.quotes.get(method_id) or []
    cite_line = quoted[0] if quoted else (cite.excerpt[:180] if cite.excerpt else "cite only; no invented method prose")
    job = " ".join(session.intent.split())
    label = method_name(method_id)
    if method_id == "delegation":
        return (
            f"Agent drafts the procedure for: {job}\n"
            f"You own live confirmation and the final dispose.\n"
            f"Cited indicator: {cite_line}"
        )
    if method_id == "description":
        return (
            f"Job: {job}\n"
            f"When: {session.when or '—'}\n"
            f"Not when: {session.not_when or '—'}\n"
            f"Cited indicator: {cite_line}"
        )
    if method_id == "discernment":
        return (
            f"Refuse if the trigger is missing or this is a near-miss off-job.\n"
            f"Job under test: {job}\n"
            f"Cited indicator: {cite_line}"
        )
    return (
        f"Verify steps before any durable write. Short body · more in references/.\n"
        f"Job: {job}\n"
        f"Cited indicator: {cite_line}"
    )


def stub_prompts(session: Session) -> tuple[list[str], list[str]]:
    job = " ".join(session.intent.split())
    should = [
        f"Walk me through this job: {job}",
        f"I keep redoing this; capture it as a skill: {job}",
    ]
    should_not = [
        "How do I write a product brief for next quarter?",
        "Open the runbook — I already confirmed severity and on-call.",
    ]
    return should, should_not


def _anthropic_text(prompt: str, *, timeout: float = 30.0) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    payload = {
        "model": model,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(ANTHROPIC_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        chunks = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        text = "\n".join(chunks).strip()
        return text or None
    except Exception:
        return None


def fill_section(session: Session, method_id: str, cite: AcademyCite) -> str:
    prompt = (
        "Fill one SKILL.md section. Server fill only; the human will Accept or Reject.\n"
        "Quote Academy indicators. Do not invent 4D method prose.\n"
        f"Citation: {ACADEMY_INDICATORS_URL}\n"
        f"Section: {method_name(method_id)}\n"
        f"Quoted indicators:\n{_quotes_block(cite, method_id)}\n"
        f"Job: {session.intent}\n"
        f"When: {session.when}\n"
        f"Not when: {session.not_when}\n"
        "Write a short section body (3–6 lines). No frontmatter. No chrome."
    )
    text = _anthropic_text(prompt)
    return text or stub_fill(session, method_id, cite)


def refine_prompts(session: Session, cite: AcademyCite) -> tuple[list[str], list[str]]:
    prompt = (
        "Propose trigger-proof prompts for a skill. Return JSON only:\n"
        '{"should":["...","..."],"should_not":["...","..."]}\n'
        "Two should (on-trigger) and two should-not (near-miss) lines.\n"
        f"Job: {session.intent}\n"
        f"When: {session.when}\n"
        f"Not when: {session.not_when}\n"
        f"Academy cite: {ACADEMY_INDICATORS_URL}\n"
        f"Excerpt: {cite.excerpt[:400]}"
    )
    text = _anthropic_text(prompt)
    if text:
        try:
            start = text.find("{")
            end = text.rfind("}")
            data: dict[str, Any] = json.loads(text[start : end + 1])
            should = [str(x).strip() for x in data.get("should", []) if str(x).strip()]
            should_not = [str(x).strip() for x in data.get("should_not", []) if str(x).strip()]
            if len(should) >= 1 and len(should_not) >= 1:
                return should[:2], should_not[:2]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return stub_prompts(session)
