# build-commons-pipeline — Project Map

Semi-automated short-form video pipeline (CrewAI → assets → Remotion → human QA → publish → analytics loop). Spec: `docs/spec.md`. Plan: `docs/superpowers/plans/2026-06-10-build-commons-pipeline.md`.

## Layout

| Folder | Owns | Context |
|---|---|---|
| `schemas/` | Pydantic `VideoScript` contract (source of truth) + shared fixtures | `schemas/context.md` |
| `agents/` | CrewAI Stage-1 agents (trend_scraper, hook_writer, script_writer) + analyst + pipeline CLI | `agents/context.md` |
| `remotion/` | Compositions, brand components, TS contract mirror, render server | `remotion/context.md` |
| `supabase/` | SQL migrations (videos, analytics, taste_library, templates) | `supabase/context.md` |
| `n8n/` | Workflow JSON exports (generate/publish/analytics) | `n8n/context.md` |
| `tests/` | Python tests (pytest) | — |

## Commands

- Python: `uv sync`, `uv run pytest`, `uv run ruff check .`
- Node (from `remotion/`): `npm install`, `npm test`, `npm run typecheck`, `npm run dev`, `npm run serve`

## Rules

- `schemas/video_script.py` is the contract source of truth. Any change MUST be mirrored in `remotion/src/types/video-script.ts` and validated against `schemas/fixtures/sample_video_script.json` on both sides.
- One tool per job (spec §3). Do not add overlapping providers/services.
- No content logic in n8n — n8n is plumbing only.
- Statuses: ideation → scripted → assets_ready → rendered → qa_pending → approved|rejected → published. Only the DB constraint in `supabase/migrations/` defines valid values.
- Never publish with a missing asset; retries are 2 per provider then manual-review flag.

## Working state

- `uv run pytest` green, `uv run ruff check .` clean
- `cd remotion && npm test && npm run typecheck` green
- CLAUDE.md == AGENTS.md (byte-identical)
