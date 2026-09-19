# Open Skills — skill-authoring playground

Day-1: **job → build → prove (teachable) → Keep writes `SKILL.md` / Throw away writes nothing.**

Tracker: [OSK-16](https://juice-engine.atlassian.net/browse/OSK-16) · [OSK-22](https://juice-engine.atlassian.net/browse/OSK-22) (weights provisional).

Craft SoT — lean page [6:3](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-3) frames only:

- [6:5](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-5) Flow map
- [6:26](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-26) Start
- [6:34](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-34) Describe
- [6:49](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-49) Build
- [6:68](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-68) Prove / Run check
- [6:107](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-107) Keep / Throw
- [6:117](https://www.figma.com/design/Xa60SjtMsUZDYcIQyCKr1j/Open-Skills-%C2%B7-workshop-vision?node-id=6-117) Done

Parked opus **1:2** / **4:2** are not implemented. Not a marketplace, hub, Orchestra merge, OAuth invent, Open UX catalog clone, or the retired thin-gate mockup.

## Loop

1. **Start** — name the job.
2. **Describe** — short name + wake line preview.
3. **Build** — method, wake / not-when, body steps. Nested skills, tools, and scripts stay closed unless you open them.
4. **Prove** — **Run check** shells out to a thin `rank`/`prove` CLI (Pydantic). Primary: **Wake** recall/precision and **Output** rubric (`on_job`, `complete`, `safe`, `cites_skill_steps`) with **why on fail**. Composite is optional/secondary if weights are supplied — not acceptance. Prove before Keep.
5. **Keep / Throw away** — sacred dispose. Keep writes the pack. Throw away writes nothing.
6. **Done** — path to the pack, or confirmed empty disk.

Human labels are **Keep** and **Throw away**. Keep is blocked if When or Not when is empty, or if prove has not run.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SKILLS_DIR="$PWD/var/skills"   # default: ~/.agents/skills
export ANTHROPIC_API_KEY=sk-ant-...   # optional; external LLM for draft/suggest/rubric
uvicorn app.main:app --reload --port 8080
```

Open http://127.0.0.1:8080

Without `ANTHROPIC_API_KEY` the host still runs: draft uses a stub; the prove CLI structures the wake + output rubric without a local model. Humans still Keep / Throw away.

### Prove CLI

```bash
python -m app.cli prove < prove.json   # ProveReport JSON — wake + output rubric
python -m app.cli rank  < rank.json    # ProveReport JSON — ranked prompts + same scheme
```

The UI **Run check** shells out to this CLI. No in-app eval suite. No in-house model stack. LLM may fill the output rubric; the CLI always structures `FailureWhy` / `VerticalScore` / `ProveReport`.

OSK-22 **40/30/30** weights are **provisional** (Yonatan challenge) — not an Eng lock. Do not treat a composite as acceptance until a later stamp.

### Env

| Variable | Role |
| --- | --- |
| `ANTHROPIC_API_KEY` | External LLM only — draft / suggest / optional rubric fill |
| `ANTHROPIC_MODEL` | Optional model id (default `claude-sonnet-4-20250514`) |
| `SKILLS_DIR` | Directory Keep writes `<slug>/` skill packs into |

## Tests

```bash
pytest -q
```

Covers: Throw away leaves zero durable skill files; Keep writes a `SKILL.md` pack with When + Not when; prove is required before Keep; teachable why on fail is surfaced; output rubric keys are structured; nesting/tools/scripts stay optional on the simple path.

## Docker (optional)

```bash
docker build -t open-skills .
docker run --rm -p 8080:8080 -e SKILLS_DIR=/data/skills -v skills:/data/skills open-skills
```

## Tokens

Craft tokens: paper `#F9F6F2` / ink `#1F1C1A` / muted `#6A6056` / line `#DED4C8` / accent `#FF4B00` / wash `#FFECE0`.
