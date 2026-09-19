"""Server-only LLM draft/refine. Human disposes. No client-side model calls."""

from __future__ import annotations

import json
from typing import Any

from app.academy import AcademyCite
from app.external_llm import anthropic_text
from app.gate import Session
from app.methods import ACADEMY_INDICATORS_URL, method_name


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


def stub_when(job: str) -> str:
    flat = " ".join(job.split())
    return f"Someone asks you to do this job: {flat}"


def stub_not_when(_job: str) -> str:
    return (
        "The request is a different job, a near-miss, marketing or blog prose, "
        "or only shares a vague verb like summarize."
    )


def stub_body(session: Session, cite: AcademyCite) -> str:
    quoted = cite.quotes.get(session.method or "description") or []
    cite_line = quoted[0] if quoted else (cite.excerpt[:180] if cite.excerpt else "cite only; no invented method prose")
    job = " ".join(session.job.split())
    return (
        f"1. Confirm the job is: {job}\n"
        f"2. Check When / Not when before loading the rest of the pack.\n"
        f"3. Follow the short procedure; put depth in references/ or scripts/ if needed.\n"
        f"4. Human Keep writes the pack; Throw away writes nothing.\n"
        f"Cited indicator: {cite_line}"
    )


def stub_fill(session: Session, method_id: str, cite: AcademyCite) -> str:
    """Deterministic fill used in tests and when no LLM key is set."""
    quoted = cite.quotes.get(method_id) or []
    cite_line = quoted[0] if quoted else (cite.excerpt[:180] if cite.excerpt else "cite only; no invented method prose")
    job = " ".join(session.job.split())
    if method_id == "delegation":
        return (
            f"Agent drafts the procedure for: {job}\n"
            f"You own live confirmation and the final dispose (Keep / Throw away).\n"
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


def stub_prompts(session: Session) -> tuple[list[str], list[str], list[str]]:
    job = " ".join(session.job.split())
    should = [
        f"Help me do this job now: {job}",
        f"I keep redoing this; capture it as a skill: {job}",
    ]
    should_not = ["Write a blog post about our product launch."]
    near_miss = ["Summarize this meeting for the team."]
    return should, should_not, near_miss


def stub_outputs(session: Session) -> tuple[list[str], list[str]]:
    job = " ".join(session.job.split())
    with_skill = [f"Drafted output for this job: {job}"]
    without_skill = ["A 1200-word blog post about our product launch."]
    return with_skill, without_skill


def fill_section(session: Session, method_id: str, cite: AcademyCite) -> str:
    prompt = (
        "Fill one SKILL.md section. Server fill only; the human will Keep or Throw away.\n"
        "Quote Academy indicators. Do not invent 4D method prose.\n"
        f"Citation: {ACADEMY_INDICATORS_URL}\n"
        f"Section: {method_name(method_id)}\n"
        f"Quoted indicators:\n{_quotes_block(cite, method_id)}\n"
        f"Job: {session.job}\n"
        f"When: {session.when}\n"
        f"Not when: {session.not_when}\n"
        "Write a short section body (3–6 lines). No frontmatter. No chrome."
    )
    text = anthropic_text(prompt)
    return text or stub_fill(session, method_id, cite)


def draft_build(session: Session, cite: AcademyCite) -> Session:
    """Fill empty Build fields from the job. Does not write a pack."""
    if not session.when:
        session.when = stub_when(session.job)
    if not session.not_when:
        session.not_when = stub_not_when(session.job)
    if not session.body:
        session.body = stub_body(session, cite)
    if not session.should or not (session.should_not or session.near_miss):
        should, should_not, near_miss = refine_prompts(session, cite)
        if not session.should:
            session.should = should
        if not session.should_not:
            session.should_not = should_not
        if not session.near_miss:
            session.near_miss = near_miss
    if not session.with_skill and not session.relevant:
        with_skill, without_skill = stub_outputs(session)
        session.with_skill = with_skill
        session.relevant = list(with_skill)
        if not session.without_skill and not session.not_relevant:
            session.without_skill = without_skill
            session.not_relevant = list(without_skill)
    elif not session.without_skill and not session.not_relevant:
        _with, without_skill = stub_outputs(session)
        session.without_skill = without_skill
        session.not_relevant = list(without_skill)
    method_id = session.method or "description"
    if session.sections[method_id].status == "empty":
        session.sections[method_id].status = "filled"
        session.sections[method_id].body = fill_section(session, method_id, cite)
    return session


def refine_prompts(session: Session, cite: AcademyCite) -> tuple[list[str], list[str], list[str]]:
    prompt = (
        "Propose trigger-proof prompts for a skill. Return JSON only:\n"
        '{"should":["..."],"should_not":["..."],"near_miss":["..."]}\n'
        "One should (on-trigger), one should-not, one near-miss.\n"
        f"Job: {session.job}\n"
        f"When: {session.when}\n"
        f"Not when: {session.not_when}\n"
        f"Academy cite: {ACADEMY_INDICATORS_URL}\n"
        f"Excerpt: {cite.excerpt[:400]}"
    )
    text = anthropic_text(prompt)
    if text:
        try:
            start = text.find("{")
            end = text.rfind("}")
            data: dict[str, Any] = json.loads(text[start : end + 1])
            should = [str(x).strip() for x in data.get("should", []) if str(x).strip()]
            should_not = [str(x).strip() for x in data.get("should_not", []) if str(x).strip()]
            near_miss = [str(x).strip() for x in data.get("near_miss", []) if str(x).strip()]
            if len(should) >= 1 and (should_not or near_miss):
                return should[:2], should_not[:2], near_miss[:2]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return stub_prompts(session)
