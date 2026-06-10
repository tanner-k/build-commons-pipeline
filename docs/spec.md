# Build Commons Content Pipeline — Technical Specification

**Version:** 1.0 · **Date:** June 2026
**Goal:** Semi-automated short-form video pipeline producing 3–5 videos/week of automated volume + ~30% manual brand content, with a closed analytics feedback loop.

---

## 1. Architecture Overview

```
[CrewAI Agents] → [Asset Generation APIs] → [n8n Orchestrator] → [Remotion Render]
       ↑                                           ↓
[Taste Library / Supabase] ← [Analyst Agent] ← [Quality Gate (human)] → [Publish (YT/TikTok/IG)]
                                                                              ↓
                                                                    [Analytics Ingest]
```

Six stages. Stages 1–3, 5, 6 automated; Stage 4 is the human quality gate (~15 min/video).

---

## 2. Hardware & Base Environment

| Item | Spec | Status |
|---|---|---|
| Dev machine | Mac mini M4 (existing) | ✅ Have |
| Render machine | Mac mini handles Remotion renders locally; Remotion Lambda (AWS) if scaling past ~10 videos/week | Decide later |
| Storage | Supabase Storage for assets, renders, thumbnails | ✅ Have |
| Database | Supabase Postgres (pipeline state, analytics, taste library) | ✅ Have |

**Local toolchain:** Node.js 20+, Python 3.12+ managed with `uv`, ffmpeg (`brew install ffmpeg`), n8n self-hosted via Docker on the Mac mini.

---

## 3. Accounts & API Keys Required

**Principle: one tool per job.** Every tool below owns exactly one responsibility. If a new tool overlaps an existing one, it must replace it, not join it.

| Service | Single Job | Est. Cost |
|---|---|---|
| Anthropic API | All LLM work: scripts, hooks, captions, analyst agent | ~$15–40/mo |
| ElevenLabs | Voiceover only (clone your own voice — Creator plan) | $22/mo |
| Google AI Studio | All AI visuals: Nano Banana (images/thumbnail bases), Veo 3.1 (b-roll) | ~$20–50/mo usage |
| Remotion | All branded rendering: videos AND thumbnails | Free (individual license, commercial use OK) |
| n8n | Plumbing only: API calls, scheduling, publishing. No content logic lives here | Free self-hosted |
| CapCut Pro | The only manual editor: pacing, audio, trims | ~$10/mo |
| YouTube Data API v3 | Upload + analytics | Free (quota-limited) |
| TikTok Content Posting API | Upload (requires developer app approval — apply early, takes days–weeks) | Free |
| Instagram Graph API | Reels publishing (requires Business/Creator account + Meta app) | Free |

**Estimated running cost: ~$65–120/mo.**

**Deliberately cut (do not set up):**

- ~~Canva~~ — replaced by a Remotion `Thumbnail.tsx` composition (programmatic, branded, zero manual step)
- ~~Descript~~ — CapCut covers the polish layer alone; two editors means two muscle memories
- ~~Kling~~ — single b-roll provider (Veo). Only add a fallback if Veo's failure rate exceeds ~5% in practice
- ~~Ollama in the pipeline~~ — at 3–5 videos/week, Claude handles everything for a few dollars; a second LLM path is premature optimization (keep Ollama for personal dev use)
- ~~OpusClip~~ — deferred until long-form content actually exists (Phase 6)

---

## 4. Repository Structure

```
build-commons-pipeline/
├── agents/                  # CrewAI (Python, uv, Pydantic)
│   ├── trend_scraper.py
│   ├── hook_writer.py
│   ├── script_writer.py
│   └── analyst.py
├── schemas/
│   └── video_script.py      # Pydantic models (source of truth)
├── remotion/                # Node/React
│   ├── src/compositions/
│   │   ├── Explainer.tsx
│   │   ├── Tutorial.tsx
│   │   ├── Listicle.tsx
│   │   ├── Comparison.tsx
│   │   └── Thumbnail.tsx    # Nano Banana base + headline → branded 1280×720 PNG
│   ├── src/components/      # Captions, progress bar, brand frame
│   └── render-server/       # Express API n8n calls to trigger renders
├── n8n/
│   └── workflows/           # Exported JSON: generate.json, publish.json, analytics.json
├── supabase/
│   └── migrations/
└── docs/
```

---

## 5. Data Model (Supabase)

```sql
videos (
  id uuid pk, status text,        -- ideation|scripted|assets_ready|rendered|
                                  -- qa_pending|approved|rejected|published
  template text, topic text, hook text,
  script_json jsonb, asset_urls jsonb, render_url text,
  platform_ids jsonb,             -- {youtube: "...", tiktok: "...", ig: "..."}
  created_at, published_at
)

analytics (
  video_id fk, platform text, captured_at timestamptz,
  views int, avg_view_duration_s float, retention_curve jsonb,
  ctr float, likes int, shares int, follows_attributed int
)

taste_library (
  id uuid pk, source_url text, niche text, transcript text,
  hook_text text, hook_type text,   -- question|bold_claim|curiosity_gap|demo
  why_it_works text, views bigint, added_by text  -- manual|analyst_agent
)

templates (
  name text pk, version int, created_at, retired_at,
  avg_retention float               -- updated by analyst agent
)
```

---

## 6. Script JSON Schema (Pipeline Contract)

Every downstream step consumes this. Pydantic on the Python side; mirror as a TypeScript type in Remotion.

```python
class Segment(BaseModel):
    id: str
    text: str                      # narration for this segment
    visual_type: Literal["ai_broll", "ai_image", "screen_recording", "text_card"]
    visual_prompt: str | None      # prompt for Veo/Nano Banana
    duration_estimate_s: float
    caption_emphasis: list[str]    # words to highlight in captions

class VideoScript(BaseModel):
    topic: str
    template: Literal["explainer", "tutorial", "listicle", "comparison"]
    hook: Segment                  # first 3s — human reviews/rewrites this
    segments: list[Segment]        # body
    cta: Segment
    target_duration_s: int         # 30–60
    platform_captions: dict[str, str]   # per-platform post text
    hashtags: dict[str, list[str]]
```

---

## 7. Stage-by-Stage Build Spec

### Stage 1 — Research & Scripting (CrewAI)

- **trend_scraper:** pulls TikTok Creative Center trends, YouTube trending in niche, target subreddits (r/ChatGPT, r/ArtificialInteligence, r/sidehustle). Outputs ranked topic candidates with evidence.
- **hook_writer:** generates 5 hook variants per topic, few-shot prompted from `taste_library` (top 20 hooks by retention).
- **script_writer:** produces `VideoScript` JSON. Hard constraints in prompt: hook ≤ 3s, payoff in first 15s, one idea per video, plain language for non-technical audience.
- All agent steps run on Claude — one LLM provider, one prompt-management surface.
- **Output:** row in `videos` with `status=scripted`.

### Stage 2 — Asset Generation

- n8n picks up `scripted` rows, fans out parallel calls:
  - ElevenLabs TTS per segment (your cloned voice; request word-level timestamps for caption sync).
  - Nano Banana for `ai_image` segments + thumbnail base.
  - Veo 3.1 for `ai_broll` segments (single provider; revisit only if failure rate >5%).
- All assets → Supabase Storage; URLs written to `asset_urls`. Status → `assets_ready`.
- **Retry policy:** 2 retries per provider, then flag for manual review. Never publish with a missing asset.

### Stage 3 — Remotion Assembly

- Render server (Express) exposes `POST /render {video_id}`; loads script JSON + assets, picks composition by `template`, renders 1080×1920 30fps MP4 **plus a `Thumbnail.tsx` still** (Nano Banana base + headline → branded PNG) in the same job.
- **Composition requirements:** word-synced captions from ElevenLabs timestamps, `spring()` animations (never linear), brand frame (colors/logo/font), progress bar.
- Post-process: `ffmpeg -crf 28 -preset slow` (~80% size reduction).
- Renders on the Mac mini initially; budget ~2–5 min/video. Status → `qa_pending`.

### Stage 4 — Human Quality Gate (~15 min/video)

Checklist (reject ≈ 1 in 15–20 expected):

1. Hook lands in 3s? Rewrite if weak — highest-leverage edit.
2. No AI artifacts (garbled text in visuals, voice glitches, caption desync).
3. Factually correct (you're teaching tools — wrong info kills trust).
4. Pacing: trim dead air in CapCut; add trending audio bed where appropriate.
5. Thumbnail: review the auto-rendered Remotion thumbnail; regenerate headline or base image only if weak.

- Approve → `approved`. Reject → back to Stage 2/3 with notes.

### Stage 5 — Publishing (n8n)

- Cron checks `approved` rows against posting schedule (start: 1/day, stagger platforms by 1–2h).
- YouTube Data API → Shorts; TikTok Content Posting API; Instagram Graph API → Reels.
- Per-platform captions/hashtags from script JSON. Store returned IDs in `platform_ids`. Status → `published`.

### Stage 6 — Analytics Feedback Loop

- Daily n8n cron: pull views, retention curve, avg view duration, CTR per platform → `analytics`.
- Weekly **analyst agent** run:
  - Scores hooks/templates/topics by 3s-hold rate and completion rate.
  - Promotes winning hooks into `taste_library` (closing the loop).
  - Flags templates with declining retention → rebuild monthly.
  - Outputs a weekly markdown report: what to make more of, what to kill.

---

## 8. Manual-Only Content Track (~30% of volume)

Not in the automated pipeline; merges at Stage 4/5:

- **Screen-recording tutorials** — real tool usage, your narration (core trust-builder for the niche).
- **Weekly face-on-camera video** — anchors audience connection.
- **Same-day trend reactions** — film and ship within hours; skip the pipeline, publish via n8n directly.
- **Monetized content** — lead magnets, sponsor reads: fully manual.

---

## 9. Build Phases

| Phase | Scope | Time |
|---|---|---|
| 1 | Remotion: 2 compositions (Explainer, Listicle) + Thumbnail.tsx + render server + caption sync | Week 1–2 |
| 2 | CrewAI agents + Pydantic schema + Supabase tables; seed taste library with 50 annotated videos (manual, ~3–4 hrs — do not skip) | Week 3 |
| 3 | n8n: asset fan-out + render trigger + YouTube publishing (TikTok/IG APIs pending approval — apply Week 1) | Week 4 |
| 4 | First 10 videos through full pipeline; tune prompts and templates | Week 5 |
| 5 | Analytics ingest + analyst agent + weekly report | Week 6 |
| 6 | Add Tutorial/Comparison templates; OpusClip once long-form exists | Ongoing |

---

## 10. Risks & Mitigations

- **AI-slop penalty:** platforms downrank generic automated content → taste library + human hook rewrite + monthly template refresh are mandatory, not optional.
- **TikTok/IG API approval delays:** apply Week 1; fall back to manual posting from a "ready" folder until approved.
- **AI disclosure:** YouTube requires disclosure of realistic AI-generated content — toggle the disclosure flag in upload metadata for AI b-roll videos.
- **Provider failures/cost spikes:** per-stage retries with manual-review flag; monthly budget alert at $120. Add a second b-roll provider only if Veo failure rate exceeds ~5%.
- **Voice cloning:** use only your own voice; keep consent recording.

## 11. Success Metrics (90 days)

- Pipeline: ≤ 20 min human time per automated video; ≥ 95% render success.
- Content: 3s hook-hold ≥ 70%; completion rate ≥ 40% on 30s videos.
- Growth: posting consistency ≥ 5/week for 12 straight weeks (consistency beats virality early); follower growth trend positive month-over-month.
