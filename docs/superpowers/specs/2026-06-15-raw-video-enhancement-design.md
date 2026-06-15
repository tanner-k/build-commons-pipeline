# Raw-Video Enhancement Track — Design

**Date:** 2026-06-15 · **Status:** approved (brainstorming) → ready for plan

## Goal

When the user uploads a raw talking-head video (e.g. themselves explaining a project), the pipeline analyzes it, proposes timed visual enhancements (AI b-roll, AI still images, screen-recording placeholders, text effects), lets the user approve the plan, then **auto-composites** the overlays onto the footage and renders a finished video into the existing human QA gate.

This is the **manual track's** on-ramp (spec §8). It is a second front-half that merges into the existing shared back half (asset generation → render → QA → publish → analytics).

## Decisions (from brainstorming)

- **Deliverable:** suggestions + auto-composite (overlays applied, re-rendered).
- **Transcript:** auto-transcribe locally with Whisper (faster-whisper) — free, offline, on the Mac mini; no new vendor.
- **Screen recordings:** the system can't capture them — render a labeled placeholder card (`SCREEN REC: …`) and flag it in `qa_notes` so the user swaps in a real capture in CapCut at the QA gate.
- **Plan checkpoint:** Claude's overlay plan lands in a reviewable `plan_ready` state; a one-word approval triggers asset-gen + compositing (guards against wasting a 2–5 min render / Veo quota on a bad plan).
- **Approach:** new "enhance" track that reuses existing infra; new `EnhancementPlan` contract kept separate from `VideoScript`.

## Architecture

```
ENHANCE track (new front half):                         SHARED back half (already built):
 uploaded → plan_ready →[user approves]→ plan_approved → assets_ready → qa_pending → approved → published
   │            │                            │               │
 Whisper    Claude writes the            n8n generates   EnhancedTalkingHead
 transcript overlay plan (checkpoint)     overlay assets composition renders overlays
                                          (Veo/Nano)     onto the base footage
```

- One `videos` table. New `kind` column (`generated` | `enhanced`) is the discriminator.
- Render server already gates on `assets_ready` and selects a composition; it learns one branch: `kind=enhanced` → `EnhancedTalkingHead`.
- Publishing (Stage 5) and analytics (Stage 6) need **zero** changes — an enhanced video is just another `approved` row carrying `platform_captions`/`hashtags`.

## Data model changes (`supabase/migrations/0002_enhancement.sql`)

Add to `videos`:
- `kind text not null default 'generated' check (kind in ('generated','enhanced'))`
- `source_video_url text` — the uploaded raw footage
- `transcript jsonb` — timestamped Whisper segments
- `enhancement_json jsonb` — the `EnhancementPlan`

Extend the `status` CHECK to add: `uploaded`, `plan_ready`, `plan_approved` (front-half states for the enhance track). Existing statuses unchanged.

## Contract — `EnhancementPlan` (`schemas/enhancement.py` + `remotion/src/types/enhancement.ts` mirror + shared fixture)

```python
class Overlay(BaseModel):
    id: str
    start_s: float            # >= 0
    end_s: float              # > start_s, <= source_duration_s
    type: Literal["ai_broll", "ai_image", "screen_recording", "text_effect"]
    placement: Literal["fullframe", "pip"]   # full cutaway vs corner box
    prompt: str | None        # REQUIRED for ai_broll/ai_image; cinematic
    text: str | None          # REQUIRED for text_effect (words shown) & screen_recording (placeholder label)
    rationale: str            # why this overlay here — shown in plan review
    asset_url: str | None     # filled after generation (ai types); null for text/screen_recording

class EnhancementPlan(BaseModel):
    source_video_url: str
    source_duration_s: float  # > 0
    overlays: list[Overlay]   # may be empty; sorted by start_s; NO time overlaps
    platform_captions: dict[str, str]
    hashtags: dict[str, list[str]]
```

Validation (frozen models, mirror `video_script.py` discipline):
- `end_s > start_s`, `0 <= start_s`, `end_s <= source_duration_s`.
- `ai_broll`/`ai_image` require non-blank `prompt`; `text_effect`/`screen_recording` require non-blank `text`.
- Overlays must not overlap in time (one enhancement at a moment — v1).
- `placement` is a required field (Literal `fullframe`|`pip`). The prompt instructs the model to choose per type (typically fullframe for ai_broll/screen_recording, pip for ai_image/text_effect), but any valid value is accepted — no implicit default in the contract.

**Base video audio plays continuously** under all overlays (fullframe cutaways cover the picture, never the voice).

## Components

**New (Python):**
- `agents/transcribe.py` — `transcribe(video_path) -> list[TranscriptSegment]` via faster-whisper (the boundary); pure helpers (`merge_segments`, `format_for_prompt`) tested without the model. ffmpeg extracts audio.
- `agents/enhance.py` — `build_enhancement_prompt(transcript, duration)` [pure], `parse_enhancement_plan(raw) -> EnhancementPlan` [pure, validates], `generate_enhancement_plan(...)` [thin Claude boundary], `render_plan_summary(plan) -> str` [markdown for review], and a CLI: `enhance plan --video <url>`, `enhance approve --id <id>`.
- `agents/db.py` additions — `insert_enhanced_video(...)`, `set_status(...)` (injectable client, untested boundary).
- `schemas/enhancement.py` — the contract above.

**New (Remotion):**
- `remotion/src/types/enhancement.ts` — zod mirror (validates the shared fixture too).
- `remotion/src/lib/overlay-timeline.ts` — `activeOverlays(plan, frame, fps)` etc., pure + unit-tested.
- `remotion/src/compositions/EnhancedTalkingHead.tsx` — base `OffthreadVideo` (full duration, audio on) + overlay track: fullframe cutaways (`OffthreadVideo`/`Img`), PIP corner boxes, `text_effect` (reuse brand caption styling), `screen_recording` → labeled placeholder card. Missing `asset_url` degrades to a placeholder (never crash).
- Register `EnhancedTalkingHead` in `Root.tsx` with `calculateMetadata` driving duration from `source_duration_s`.

**Extended:**
- `remotion/render-server/src/render.ts` + `app.ts` — when `kind=enhanced`, render `EnhancedTalkingHead` with `{enhancement_json}`; else existing template path. `app.ts` already validates id/status; add the kind branch.
- `supabase/migrations/0002_enhancement.sql`.
- `n8n/workflows/enhance.json` — poll `plan_approved` rows, generate overlay assets (Veo/Nano per overlay `prompt`), write `asset_url` back into `enhancement_json`, set `assets_ready`, trigger render. Skeleton like the others; retries; no secrets.
- Docs: README manual-track section + `docs/setup.md` enhance section.

**Reused unchanged:** Nano Banana / Veo asset generation, render server upload + `qa_pending` transition, publishing, analytics, brand theme, caption components.

## Data flow

1. User uploads raw video to Supabase Storage; runs `uv run python -m agents.enhance plan --video <url>` (optionally `--captions`/`--hashtags` or let Claude draft them).
2. `enhance.py`: locate video → ffmpeg extract audio → faster-whisper → timestamped transcript. Insert `videos` row (`kind=enhanced`, `source_video_url`, `status=uploaded`), then Claude → `EnhancementPlan` → store `enhancement_json`, `status=plan_ready`. Print the markdown plan summary.
3. User reviews the summary; `uv run python -m agents.enhance approve --id <id>` → `status=plan_approved`.
4. `n8n/enhance.json` polls `plan_approved`: for each `ai_broll`/`ai_image` overlay, call Veo/Nano with `prompt`, upload, write `asset_url` into the plan. `text_effect`/`screen_recording` need no asset. → `assets_ready`, trigger render.
5. Render server (`kind=enhanced`) → `EnhancedTalkingHead` composites overlays on the base footage → MP4 + thumbnail → upload → `qa_pending`. Screen-rec placeholders noted in `qa_notes`.
6. Human QA gate → `approved`/`rejected` (reject returns to `plan_ready` with notes) → existing publish/analytics.

## Error handling

- Whisper/ffmpeg failure → clear error, row stays `uploaded` (retry).
- Claude plan parse/validation failure → `ValueError`, surfaced; row stays `uploaded`.
- Overlay asset-gen failure → existing 2-retry-then-manual-flag policy; a missing `asset_url` degrades that overlay to a labeled placeholder card in the composite (defensive, mirrors `SegmentVisual`).
- Time-overlap rejected at the contract boundary; plan checkpoint prevents wasted renders.

## Testing (TDD, matching the repo)

- `EnhancementPlan`/`Overlay` validation tests (time ordering, bounds, type→prompt/text rules, no-overlap, placement) — Python; the zod mirror validates the **same** shared fixture.
- `enhance.py` pure functions: prompt contains constraints + schema; `parse_enhancement_plan` handles fenced JSON and raises on invalid/overlapping.
- `transcribe.py`: pure merge/format helpers tested; faster-whisper call mocked.
- Remotion: `overlay-timeline` unit tests; `EnhancedTalkingHead` exercised by a smoke render over a tiny fixture base video.
- Render server: `app.test.ts` extended for the `kind=enhanced` branch (mocked boundaries).
- `enhance.json`: structural test (trigger, retries, no secrets).
- Migration: sqlglot test for new columns + statuses.

## Out of scope (v1)

- Vision analysis of video frames (transcript-driven only).
- Overlapping/stacked overlays; transitions between overlays beyond a simple spring fade.
- Auto-capturing screen recordings (placeholder only).
- A web UI for plan editing (CLI + SQL approval, matching the rest of the pipeline).
