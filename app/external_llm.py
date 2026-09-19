"""External LLM API only — draft/suggest/explain. No in-house model stack."""

from __future__ import annotations

import os

import httpx

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def anthropic_text(prompt: str, *, timeout: float = 30.0, max_tokens: int = 400) -> str | None:
    """Call the hosted Anthropic API. Returns None without a key or on failure."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    payload = {
        "model": model,
        "max_tokens": max_tokens,
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
