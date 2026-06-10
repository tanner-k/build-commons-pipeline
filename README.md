# build-commons-pipeline

Semi-automated short-form video pipeline: CrewAI scripting → asset generation (ElevenLabs / Nano Banana / Veo) → Remotion rendering → human quality gate → multi-platform publishing (YouTube/TikTok/IG), with a closed analytics feedback loop. Target: 3–5 automated videos/week + ~30% manual brand content.

Full spec: [docs/spec.md](docs/spec.md) · Setup guide: [docs/setup.md](docs/setup.md)

## Stack

| Layer | Tech |
|---|---|
| Agents (Stage 1 & 6) | Python 3.12 · uv · CrewAI · Pydantic v2 · Claude |
| Contract | `schemas/video_script.py` (source of truth) ↔ `remotion/src/types/video-script.ts` (zod mirror) |
| Rendering (Stage 3) | Remotion 4 · React 18 · Express render server · ffmpeg |
| State & assets | Supabase Postgres + Storage (`supabase/migrations/`) |
| Orchestration (Stages 2/5/6) | n8n self-hosted via Docker (`n8n/workflows/`) |

## Install

```bash
uv sync                      # Python deps
cd remotion && npm install   # Node deps
brew install ffmpeg          # if missing
```

## Commands

```bash
uv run pytest                          # Python tests
uv run ruff check .                    # Python lint
cd remotion && npm test                # TS tests (vitest)
cd remotion && npm run typecheck       # tsc --noEmit
cd remotion && npm run dev             # Remotion Studio (preview comps)
cd remotion && npm run serve           # render server on :3333
uv run python -m agents.pipeline run --topic "..."   # Stage 1: topic → scripted row
uv run python -m agents.analyst report                # Stage 6: weekly report
```

## Gotchas

- Remotion packages must all be the **exact same version** — never mix.
- ElevenLabs word timestamps are required for caption sync; without them captions fall back to even spacing.
- TikTok/IG publishing APIs need app approval (days–weeks) — apply early; manual posting fallback until then.
- YouTube uploads of AI b-roll videos must set the AI-disclosure flag.

## Recent updates

Last 5 entries from [CHANGELOG.md](./CHANGELOG.md):

<!-- BEGIN:RECENT-UPDATES -->
- (auto-populated by `scripts/done.py` once you ship something)
<!-- END:RECENT-UPDATES -->

## Project map

See [CLAUDE.md](./CLAUDE.md) (identical to [AGENTS.md](./AGENTS.md)) for the agent-readable map of this repo.
