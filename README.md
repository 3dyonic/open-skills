# Open Skills

Day-1 thin gate: **intent → 4Ds pick → prove-trigger → per-D fill → read-only preview → Accept writes `SKILL.md` / Reject writes nothing.**

Tracker: [OSK-16](https://juice-engine.atlassian.net/browse/OSK-16). Craft SoT: [Figma thin-gate funnel](https://www.figma.com/design/YTDZYEp7b1ul5lNSAGYh0e).

Not a marketplace, hub, skill IDE, Orchestra merge, OAuth invent, or Open UX catalog clone.

## Loop

1. **Intent** — plain job. No gallery.
2. **Methods** — mandatory pick of one Anthropic Academy Fluency 4D (Delegation / Description / Discernment / Diligence). Cards cite [The 4 Ds of AI Fluency — Behavioral Indicators](https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators). Host fetches that page and quotes indicators; no paraphrased method essays.
3. **Prove trigger** — When and Not when are required. Should / should-not prompts are habit checks before keep/kill.
4. **Fill** — server LLM fills the current D. **Skip this D** or **Regenerate section**. Skipped Ds show a **Skipped** badge in preview.
5. **Preview · dispose** — read-only `SKILL.md`. No Save-draft hero.
6. **Accept** writes a durable agentskills.io `SKILL.md` (`name`, `description` with when / not when, body). **Reject** writes nothing.

Accept is blocked if When or Not when is empty.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SKILLS_DIR="$PWD/var/skills"   # default: ~/.agents/skills
export ANTHROPIC_API_KEY=sk-ant-...   # optional; fill/refine only
uvicorn app.main:app --reload --port 8080
```

Open http://127.0.0.1:8080

Without `ANTHROPIC_API_KEY` the host still runs: fill/refine uses a deterministic server stub. Humans still Accept / Reject.

### Env

| Variable | Role |
| --- | --- |
| `ANTHROPIC_API_KEY` | Server LLM for fill / regenerate / trigger-proof prompts |
| `ANTHROPIC_MODEL` | Optional model id (default `claude-sonnet-4-20250514`) |
| `SKILLS_DIR` | Directory Accept writes `<slug>/SKILL.md` into |

## Tests

```bash
pytest -q
```

Covers: Reject leaves zero skill files; Accept produces `SKILL.md` with When + Not when; Skip → Skipped in preview; empty When / Not when blocks Accept.

## Docker (Fly-ready)

```bash
docker build -t open-skills .
docker run --rm -p 8080:8080 -e SKILLS_DIR=/data/skills -v skills:/data/skills open-skills
```

Deploy is optional for Day-1.

## Tokens

Semantic Craft tokens only: paper `#F9F6F2` / ink `#1F1C16` / muted `#6A6056` / line `#DED4C8` / accent `#FF4B00`. No Open UX catalog chrome.
