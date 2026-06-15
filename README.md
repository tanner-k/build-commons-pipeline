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

## Using the pipeline

**Where do you start? Either an idea or a raw clip — that choice decides which of the two tracks you're on.**

- **Start from an idea → automated track.** You give the pipeline a *topic* (one sentence). It writes the hook and script, generates the voiceover in your cloned voice, generates the visuals, renders a branded vertical video plus a thumbnail, and drops it in your review queue. You never point a camera at anything. This is the 3–5 videos/week of volume.
- **Start from a raw video you filmed → manual track.** Screen-recording tutorials, a weekly face-on-camera, a same-day trend reaction — you record and edit these yourself, then hand the finished file to the same publishing step. This is the ~30% brand content.

The two tracks converge at the **human review gate** and the **publisher**, so everything — generated or hand-shot — goes out through one scheduler with the same per-platform captions. It never takes a raw video *into* the automated track: an idea drives generation; a clip you already shot rides the manual track and merges in near the end.

### The status lifecycle (the spine)

Every video is one row in the `videos` table moving through states. You can check progress any time by reading its `status`:

```
ideation → scripted → assets_ready → qa_pending → approved → published
                                          └─────────→ rejected (sent back to fix)
```

### Automated track, step by step

> First-time setup (accounts, API keys, Supabase, n8n, voice clone) is in [docs/setup.md](docs/setup.md) — do that once before the steps below. The n8n `generate`/`publish` steps are importable skeletons until you complete the Phase-3 wiring checklist in setup.md §4.

1. **Idea → script.** Let it mine trends, or hand it a specific topic:
   ```bash
   uv run python -m agents.pipeline trends                 # ranked topic candidates (Reddit + YouTube)
   uv run python -m agents.pipeline run                    # auto-pick the top trending topic
   uv run python -m agents.pipeline run --topic "Summarize any PDF with Claude in 30s"
   ```
   The topic can come from anywhere — a Reddit thread, a TikTok Creative Center trend you spotted (no API, so you paste it), or your own idea. Writes a `videos` row at `status=scripted`. *(Stage 1)*
2. **Assets generate automatically.** The n8n `generate` workflow polls `scripted` rows every 15 min and fans out: ElevenLabs voiceover (your cloned voice, with word timestamps for caption sync), Nano Banana images, Veo b-roll. → `assets_ready` *(Stage 2)*
3. **It renders itself.** n8n calls the render server (`POST /render {video_id}`), which assembles the 1080×1920 MP4 + a branded thumbnail and compresses them. → `qa_pending` *(Stage 3)*
4. **You review (~15 min — the only required human step).** Watch the render and thumbnail; trim or re-pace in CapCut if needed. Then set the status:
   ```sql
   update videos set status = 'approved' where id = '<video_id>';
   -- or send it back with notes:
   update videos set status = 'rejected', qa_notes = 'hook is weak — rewrite' where id = '<video_id>';
   ```
   (Full QA checklist: [docs/setup.md](docs/setup.md) §8.) *(Stage 4)*
5. **It publishes itself.** The n8n `publish` workflow posts `approved` rows to YouTube, TikTok, and Instagram using the per-platform captions and hashtags from the script. → `published` *(Stage 5)*
6. **It learns.** Analytics ingest daily; once a week, `uv run python -m agents.analyst report` scores what held attention and promotes your best-performing hooks back into the taste library so future scripts copy what works. *(Stage 6)*

### Manual track (you already have a raw video)

For screen recordings, face-on-camera, sponsor reads, or same-day trend reactions there's nothing to generate — you skip Stages 1–3. Edit your clip in CapCut, upload it to Supabase Storage, then drop it into the flow at the publishing step by inserting a row with your finished file as `render_url`:

```sql
insert into videos (status, topic, template, render_url, script_json)
values ('approved', 'My screen-recording tutorial', 'tutorial',
        'https://<your-project>.supabase.co/storage/v1/object/public/renders/my-clip.mp4',
        '{"platform_captions": {"youtube": "...", "tiktok": "...", "instagram": "..."},
          "hashtags": {"youtube": ["#..."], "tiktok": ["#..."], "instagram": ["#..."]}}'::jsonb);
```

The publisher treats it identically to a generated video. Use `qa_pending` instead of `approved` if you still want it to pass through your own review queue first.

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
- Shipped n8n workflow skeletons (generate/publish/analytics) with retry policy and structural tests
- Shipped analyst agent: retention scoring, idempotent hook promotion, weekly markdown report
- Wrote setup guide (accounts, n8n Phase-3 wiring checklist) and architecture map
- Shipped Explainer/Listicle compositions + branded Thumbnail still with word-synced captions
- Shipped Express render server: POST /render renders video+thumbnail, compresses, updates Supabase
<!-- END:RECENT-UPDATES -->

## Project map

See [CLAUDE.md](./CLAUDE.md) (identical to [AGENTS.md](./AGENTS.md)) for the agent-readable map of this repo.
