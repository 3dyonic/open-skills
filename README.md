# Open Skills — skill-authoring playground

Day-1: **job → build → prove (teachable) → Keep writes `SKILL.md` / Throw away writes nothing.**

Tracker: [OSK-16](https://juice-engine.atlassian.net/browse/OSK-16). Craft SoT: [playground vision 1:2](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=1-2) · [UX/UI example 4:2](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=4-2).

Not a marketplace, hub, Orchestra merge, OAuth invent, Open UX catalog clone, or the retired thin-gate mockup.

## Loop

1. **Start** — empty state. Make a skill that knows when to help.
2. **Describe** — the job in plain words.
3. **Build** — steer When / Not when, steps, and an Academy Fluency 4D cite. Nested skills, tools, and scripts stay closed unless you open them.
4. **Prove** — **Run check** shells out to a thin `rank`/`prove` CLI (Pydantic scheme). Scores **Wake** (should / should-not) and **Output** (relevant / not). Prove before Keep.
5. **Keep / Throw away** — sacred dispose. Keep writes the pack. Throw away writes nothing.
6. **Done** — path to the pack, or confirmed empty disk.

Human labels are **Keep** and **Throw away**. Keep is blocked if When or Not when is empty, or if prove has not run.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SKILLS_DIR="$PWD/var/skills"   # default: ~/.agents/skills
export ANTHROPIC_API_KEY=sk-ant-...   # optional; external LLM for draft/suggest/explain
uvicorn app.main:app --reload --port 8080
```

Open http://127.0.0.1:8080

Without `ANTHROPIC_API_KEY` the host still runs: draft uses a stub; the prove CLI scores wake/output without a local model. Humans still Keep / Throw away.

### Prove CLI

```bash
python -m app.cli prove < prove.json   # wake + output relevance
python -m app.cli rank  < rank.json    # order prompts/samples by score
```

The UI **Run check** shells out to this CLI. No in-app eval suite. No in-house model stack.

### Env

| Variable | Role |
| --- | --- |
| `ANTHROPIC_API_KEY` | External LLM only — draft / suggest / optional relevance explain |
| `ANTHROPIC_MODEL` | Optional model id (default `claude-sonnet-4-20250514`) |
| `SKILLS_DIR` | Directory Keep writes `<slug>/` skill packs into |

## Tests

```bash
pytest -q
```

Covers: Throw away leaves zero durable skill files; Keep writes a `SKILL.md` pack with When + Not when; prove is required before Keep; teachable why pass/fail is surfaced; nesting/tools/scripts stay optional on the simple path.

## Docker (optional)

```bash
docker build -t open-skills .
docker run --rm -p 8080:8080 -e SKILLS_DIR=/data/skills -v skills:/data/skills open-skills
```

## Tokens

Craft tokens: paper `#F9F6F2` / ink `#1F1C16` / muted `#6A6056` / line `#DED4C8` / accent `#FF4B00`.
