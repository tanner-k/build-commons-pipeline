# Architecture

```
[CrewAI Agents] → [Asset Generation APIs] → [n8n Orchestrator] → [Remotion Render]
       ↑                                           ↓
[Taste Library / Supabase] ← [Analyst Agent] ← [Quality Gate (human)] → [Publish (YT/TikTok/IG)]
                                                                              ↓
                                                                    [Analytics Ingest]
```

Six stages (spec §7). Stages 1–3, 5, 6 automated; Stage 4 is the human gate.

| Stage | Component | Code |
|---|---|---|
| 1 Research/Scripting | CrewAI on Claude | `agents/trend_scraper.py`, `agents/hook_writer.py`, `agents/script_writer.py`, `agents/pipeline.py` |
| 2 Asset generation | n8n fan-out (ElevenLabs, Nano Banana, Veo) | `n8n/workflows/generate.json` |
| 3 Assembly | Express render server → Remotion → ffmpeg | `remotion/render-server/`, `remotion/src/` |
| 4 Quality gate | Human (~15 min/video) | procedure in `docs/setup.md` §8 |
| 5 Publishing | n8n cron → platform APIs | `n8n/workflows/publish.json` |
| 6 Feedback loop | n8n ingest + analyst agent | `n8n/workflows/analytics.json`, `agents/analyst.py` |

**Contract:** `schemas/video_script.py` (Pydantic, source of truth) ↔
`remotion/src/types/video-script.ts` (zod mirror), pinned by the shared fixtures in
`schemas/fixtures/` which both test suites validate.

**State machine** (`videos.status`): ideation → scripted → assets_ready → qa_pending →
approved | rejected → published. Definition lives in
`supabase/migrations/0001_init.sql`. Note: `rendered` is a reserved status value in the
CHECK constraint but is currently unused — the render server transitions
assets_ready → qa_pending directly once the render completes. The videos table also
includes `thumbnail_url` (populated by Stage 3; Stage 4 previews the thumbnail from it).

**Key decisions** (spec §3): one tool per job; single b-roll provider (Veo) unless
failure rate >5%; no content logic in n8n; renders local on the Mac mini, Remotion
Lambda only if >10 videos/week.
