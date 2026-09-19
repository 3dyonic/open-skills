# Open Skills — skill-authoring playground

Day-1: **job → build → prove (Wake + Output evidence reports) → Keep writes `SKILL.md` / Throw away writes nothing.**

Tracker: [OSK-16](https://juice-engine.atlassian.net/browse/OSK-16) · [OSK-22](https://juice-engine.atlassian.net/browse/OSK-22) (no numeric keep/kill floors) · [OSK-23](https://juice-engine.atlassian.net/browse/OSK-23) (prove shape).

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
4. **Prove** — **Run check** shells out to `python -m app.cli prove`. `ProveReport = {wake, output}`. Evidence on every case. Wake: should / should-not / near-miss, multi-run trigger rates (± P/R), harness honesty. Output: with / without + assertions; LLM judge is pass/fail + evidence (deterministic fallback). **No required composite %.** **No numeric Keep floor** — human Keep / Throw after the reports.
5. **Keep / Throw away** — sacred dispose. Keep writes the pack. Throw away writes nothing.
6. **Done** — path to the pack, or confirmed empty disk.

Human labels are **Keep** and **Throw away**. Keep is blocked only if When / Not when is empty or prove has not run. Optional floors later only if labeled ours.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SKILLS_DIR="$PWD/var/skills"   # default: ~/.agents/skills
export ANTHROPIC_API_KEY=sk-ant-...   # optional; external LLM for draft/suggest/output judge
uvicorn app.main:app --reload --port 8080
```

Open http://127.0.0.1:8080

Without `ANTHROPIC_API_KEY` the host still runs: draft uses a stub; the prove CLI structures Wake + Output evidence without a local model.

### Prove CLI

```bash
python -m app.cli prove < prove.json   # ProveReport {wake, output}
python -m app.cli rank  < rank.json    # same shape + ranked[]
```

The UI **Run check** shells out to this CLI. No in-app eval suite. No in-house model stack.

### Env

| Variable | Role |
| --- | --- |
| `ANTHROPIC_API_KEY` | External LLM only — draft / suggest / optional output judge |
| `ANTHROPIC_MODEL` | Optional model id (default `claude-sonnet-4-20250514`) |
| `SKILLS_DIR` | Directory Keep writes `<slug>/` skill packs into |

## Tests

```bash
pytest -q
```

Covers: Throw away leaves zero durable skill files; Keep writes a `SKILL.md` pack with When + Not when; prove (evidence reports) is required before Keep; mismatches do not invent a keep/kill floor; evidence is present on every case; nesting/tools/scripts stay optional on the simple path.

## Docker (optional)

```bash
docker build -t open-skills .
docker run --rm -p 8080:8080 -e SKILLS_DIR=/data/skills -v skills:/data/skills open-skills
```

## Tokens

Craft tokens: paper `#F9F6F2` / ink `#1F1C1A` / muted `#6A6056` / line `#DED4C8` / accent `#FF4B00` / wash `#FFECE0`.
