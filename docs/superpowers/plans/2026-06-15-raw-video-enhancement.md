# Raw-Video Enhancement Track Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manual-track on-ramp where an uploaded talking-head video is transcribed (local Whisper), analyzed by Claude into a reviewable timed-overlay plan, then auto-composited (AI b-roll / stills / text effects / screen-rec placeholders) over the footage and rendered into the existing QA gate.

**Architecture:** New "enhance" front-half (`uploaded → plan_ready → plan_approved`) that merges into the existing shared back half (`assets_ready → qa_pending → approved → published`). A new `EnhancementPlan` contract (Pydantic + zod mirror + shared fixture) is kept separate from `VideoScript`. A new `EnhancedTalkingHead` Remotion composition overlays assets on the base footage; the existing render server learns one `kind=enhanced` branch. Publishing/analytics are unchanged.

**Tech Stack:** Python 3.12 / uv / Pydantic / CrewAI(Claude) / faster-whisper / ffmpeg; Remotion 4 / React / zod; Supabase Postgres; n8n.

**Spec:** `docs/superpowers/specs/2026-06-15-raw-video-enhancement-design.md` (read it first). Section refs below point at it.

**Working dir:** `/Users/tannerkunz/coding/build-commons-pipeline` (branch `feature/enhance-track`). Conventions: `uv run …` for Python, Node from `remotion/`; conventional commits, NO attribution footers; vitest cold start is slow (~3–5 min) — be patient, never kill mid-run.

**Contract type names (consistent across all tasks):** Python `Overlay`, `EnhancementPlan`, `TranscriptSegment`; zod `overlaySchema`, `enhancementPlanSchema`; overlay fields `id, start_s, end_s, type, placement, prompt, text, rationale, asset_url`; overlay `type ∈ {ai_broll, ai_image, screen_recording, text_effect}`; `placement ∈ {fullframe, pip}`.

---

### Task 1: Supabase migration 0002 (enhance columns + statuses)

**Files:**
- Create: `supabase/migrations/0002_enhancement.sql`
- Test: `tests/test_migration_0002.py`

- [ ] **Step 1: Write the failing test** — `tests/test_migration_0002.py`

```python
from pathlib import Path

import sqlglot

MIGRATION = Path(__file__).parent.parent / "supabase" / "migrations" / "0002_enhancement.sql"


def sql() -> str:
    return MIGRATION.read_text()


def test_parses_as_postgres():
    assert len(sqlglot.parse(sql(), read="postgres")) > 0


def test_adds_enhance_columns():
    text = sql().lower()
    for col in ("kind", "source_video_url", "transcript", "enhancement_json"):
        assert col in text, f"missing column {col}"


def test_kind_constraint_values():
    text = sql()
    assert "'generated'" in text and "'enhanced'" in text


def test_adds_new_statuses():
    text = sql()
    for status in ("uploaded", "plan_ready", "plan_approved"):
        assert f"'{status}'" in text, f"missing status {status}"
    # existing statuses must remain
    for status in ("assets_ready", "qa_pending", "approved", "published"):
        assert f"'{status}'" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_migration_0002.py -q`
Expected: FAIL (FileNotFoundError)

- [ ] **Step 3: Write `supabase/migrations/0002_enhancement.sql`**

```sql
-- 0002_enhancement.sql — raw-video enhancement track (manual track on-ramp).
-- Adds the enhance discriminator + front-half statuses; back half is shared.
-- Apply via Supabase SQL editor or `supabase db push` AFTER 0001_init.sql.

alter table videos
    add column if not exists kind text not null default 'generated'
        check (kind in ('generated', 'enhanced')),
    add column if not exists source_video_url text,   -- uploaded raw footage
    add column if not exists transcript jsonb,         -- [{"text","start_s","end_s"}, ...]
    add column if not exists enhancement_json jsonb;   -- the EnhancementPlan

-- Extend the status machine with the enhance front-half states. Postgres has no
-- "alter check constraint", so drop and recreate. Existing rows keep their status.
alter table videos drop constraint if exists videos_status_check;
alter table videos add constraint videos_status_check check (status in (
    'ideation', 'scripted', 'assets_ready', 'rendered',
    'qa_pending', 'approved', 'rejected', 'published',
    'uploaded', 'plan_ready', 'plan_approved'
));

create index if not exists videos_kind_status_idx on videos (kind, status);
```

Note: the original `videos_status_check` may be auto-named differently by Postgres. If `supabase db push` reports the drop found nothing, that is fine (`if exists`); the new named constraint still applies. Document this in the migration comment (already included).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_migration_0002.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0002_enhancement.sql tests/test_migration_0002.py
git commit -m "feat(supabase): migration 0002 — enhance columns + front-half statuses"
```

---

### Task 2: EnhancementPlan contract (Pydantic) + shared fixture

**Files:**
- Create: `schemas/enhancement.py`
- Create: `schemas/fixtures/sample_enhancement_plan.json`
- Test: `tests/test_enhancement_schema.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_enhancement_schema.py`

```python
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.enhancement import EnhancementPlan, Overlay

FIXTURE = Path(__file__).parent.parent / "schemas" / "fixtures" / "sample_enhancement_plan.json"


def make_overlay(**overrides) -> Overlay:
    base = dict(
        id="ov-1",
        start_s=2.0,
        end_s=5.0,
        type="ai_image",
        placement="pip",
        prompt="A clean isometric diagram of a data pipeline, dark navy, amber accents",
        text=None,
        rationale="Speaker introduces the architecture here",
        asset_url=None,
    )
    base.update(overrides)
    return Overlay(**base)


def make_plan(**overrides) -> EnhancementPlan:
    base = dict(
        source_video_url="https://x.supabase.co/storage/v1/object/public/uploads/talk.mp4",
        source_duration_s=60.0,
        overlays=[make_overlay()],
        platform_captions={"youtube": "How I built it"},
        hashtags={"youtube": ["#build"]},
    )
    base.update(overrides)
    return EnhancementPlan(**base)


class TestOverlay:
    def test_round_trips(self):
        ov = make_overlay()
        assert Overlay.model_validate(ov.model_dump()) == ov

    def test_end_after_start(self):
        with pytest.raises(ValidationError):
            make_overlay(start_s=5.0, end_s=5.0)

    def test_negative_start_rejected(self):
        with pytest.raises(ValidationError):
            make_overlay(start_s=-1.0, end_s=2.0)

    def test_ai_type_requires_prompt(self):
        with pytest.raises(ValidationError, match="prompt"):
            make_overlay(type="ai_broll", prompt="   ", text=None)

    def test_text_effect_requires_text(self):
        with pytest.raises(ValidationError, match="text"):
            make_overlay(type="text_effect", prompt=None, text=None)

    def test_screen_recording_requires_text_label(self):
        with pytest.raises(ValidationError, match="text"):
            make_overlay(type="screen_recording", prompt=None, text=" ")

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            make_overlay(type="hologram")

    def test_unknown_placement_rejected(self):
        with pytest.raises(ValidationError):
            make_overlay(placement="sideways")

    def test_is_immutable(self):
        ov = make_overlay()
        with pytest.raises(ValidationError):
            ov.id = "mutated"


class TestEnhancementPlan:
    def test_round_trips_json(self):
        plan = make_plan()
        assert EnhancementPlan.model_validate_json(plan.model_dump_json()) == plan

    def test_duration_must_be_positive(self):
        with pytest.raises(ValidationError):
            make_plan(source_duration_s=0)

    def test_overlay_within_duration(self):
        with pytest.raises(ValidationError, match="source_duration_s"):
            make_plan(source_duration_s=4.0, overlays=[make_overlay(start_s=2.0, end_s=5.0)])

    def test_overlays_may_be_empty(self):
        assert make_plan(overlays=[]).overlays == []

    def test_overlapping_overlays_rejected(self):
        a = make_overlay(id="a", start_s=0.0, end_s=3.0)
        b = make_overlay(id="b", start_s=2.0, end_s=5.0)
        with pytest.raises(ValidationError, match="overlap"):
            make_plan(overlays=[a, b])

    def test_adjacent_overlays_allowed(self):
        a = make_overlay(id="a", start_s=0.0, end_s=3.0)
        b = make_overlay(id="b", start_s=3.0, end_s=5.0)
        assert len(make_plan(overlays=[a, b]).overlays) == 2

    def test_duplicate_overlay_ids_rejected(self):
        a = make_overlay(id="dup", start_s=0.0, end_s=2.0)
        b = make_overlay(id="dup", start_s=2.0, end_s=4.0)
        with pytest.raises(ValidationError, match="unique"):
            make_plan(overlays=[a, b])


def test_sample_fixture_is_valid():
    plan = EnhancementPlan.model_validate(json.loads(FIXTURE.read_text()))
    assert plan.source_duration_s > 0
    assert len(plan.overlays) >= 3
    # overlays sorted and non-overlapping
    ends = [o.end_s for o in plan.overlays]
    starts = [o.start_s for o in plan.overlays]
    assert starts == sorted(starts)
    assert all(ends[i] <= starts[i + 1] for i in range(len(ends) - 1))
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_enhancement_schema.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write `schemas/enhancement.py`**

```python
"""EnhancementPlan contract for the raw-video enhance track (spec: §Contract).

Source of truth. Mirror: remotion/src/types/enhancement.ts (zod). Shared fixture:
schemas/fixtures/sample_enhancement_plan.json is validated by both sides.
Kept separate from video_script.py — enhanced videos overlay assets on real
footage; they are not generated from a narration script.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

OverlayType = Literal["ai_broll", "ai_image", "screen_recording", "text_effect"]
Placement = Literal["fullframe", "pip"]

AI_OVERLAY_TYPES: frozenset[str] = frozenset({"ai_broll", "ai_image"})
TEXT_OVERLAY_TYPES: frozenset[str] = frozenset({"text_effect", "screen_recording"})


class Overlay(BaseModel):
    """One timed visual laid over the base footage."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float
    type: OverlayType
    placement: Placement
    prompt: str | None = None        # required for ai_broll/ai_image
    text: str | None = None          # required for text_effect / screen_recording label
    rationale: str = Field(min_length=1)
    asset_url: str | None = None     # filled after asset generation

    @model_validator(mode="after")
    def _check(self) -> "Overlay":
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        if self.type in AI_OVERLAY_TYPES and not (self.prompt or "").strip():
            raise ValueError(f"prompt is required when type={self.type!r}")
        if self.type in TEXT_OVERLAY_TYPES and not (self.text or "").strip():
            raise ValueError(f"text is required when type={self.type!r}")
        return self


class EnhancementPlan(BaseModel):
    """Base footage + a non-overlapping, time-sorted list of overlays."""

    model_config = ConfigDict(frozen=True)

    source_video_url: str = Field(min_length=1)
    source_duration_s: float = Field(gt=0)
    overlays: list[Overlay] = Field(default_factory=list)
    platform_captions: dict[str, str]
    hashtags: dict[str, list[str]]

    @model_validator(mode="after")
    def _check(self) -> "EnhancementPlan":
        ids = [o.id for o in self.overlays]
        if len(ids) != len(set(ids)):
            raise ValueError("overlay ids must be unique")
        for o in self.overlays:
            if o.end_s > self.source_duration_s:
                raise ValueError(
                    f"overlay {o.id} ends at {o.end_s}s, past source_duration_s={self.source_duration_s}"
                )
        ordered = sorted(self.overlays, key=lambda o: o.start_s)
        for prev, nxt in zip(ordered, ordered[1:], strict=False):
            if nxt.start_s < prev.end_s:
                raise ValueError(f"overlays {prev.id} and {nxt.id} overlap in time")
        return self

    def sorted_overlays(self) -> list[Overlay]:
        return sorted(self.overlays, key=lambda o: o.start_s)
```

- [ ] **Step 4: Write `schemas/fixtures/sample_enhancement_plan.json`**

```json
{
  "source_video_url": "https://example.supabase.co/storage/v1/object/public/uploads/build-commons-demo.mp4",
  "source_duration_s": 48.0,
  "overlays": [
    {
      "id": "ov-1",
      "start_s": 3.0,
      "end_s": 9.0,
      "type": "ai_broll",
      "placement": "fullframe",
      "prompt": "Cinematic slow push-in over a tidy developer desk at night, glowing monitor, warm amber key light, shallow depth of field, 4k",
      "text": null,
      "rationale": "Opening context while the speaker sets up the problem",
      "asset_url": null
    },
    {
      "id": "ov-2",
      "start_s": 12.5,
      "end_s": 18.0,
      "type": "ai_image",
      "placement": "pip",
      "prompt": "Clean isometric illustration of a three-stage data pipeline, dark navy background, amber accent nodes, soft shadows",
      "text": null,
      "rationale": "Speaker names the three pipeline stages — show them",
      "asset_url": null
    },
    {
      "id": "ov-3",
      "start_s": 20.0,
      "end_s": 27.0,
      "type": "screen_recording",
      "placement": "fullframe",
      "prompt": null,
      "text": "the render server returning a video_id",
      "rationale": "Live demo of the actual API call lands trust",
      "asset_url": null
    },
    {
      "id": "ov-4",
      "start_s": 30.0,
      "end_s": 34.0,
      "type": "text_effect",
      "placement": "pip",
      "prompt": null,
      "text": "2-5 min / video",
      "rationale": "Reinforce the render-time stat the speaker quotes",
      "asset_url": null
    }
  ],
  "platform_captions": {
    "youtube": "How I built a semi-automated video pipeline",
    "tiktok": "I automated 70% of my video editing 👇",
    "instagram": "The build, end to end."
  },
  "hashtags": {
    "youtube": ["#buildinpublic", "#ai", "#automation"],
    "tiktok": ["#buildinpublic", "#aitools", "#devtok"],
    "instagram": ["#buildinpublic", "#automation"]
  }
}
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_enhancement_schema.py -q && uv run ruff check .`
Expected: PASS / clean

- [ ] **Step 6: Commit**

```bash
git add schemas/enhancement.py schemas/fixtures/sample_enhancement_plan.json tests/test_enhancement_schema.py
git commit -m "feat(schemas): EnhancementPlan contract + shared fixture"
```

---

### Task 3: zod mirror of EnhancementPlan

**Files:**
- Create: `remotion/src/types/enhancement.ts`
- Test: `remotion/src/types/enhancement.test.ts`

- [ ] **Step 1: Write the failing test** — `remotion/src/types/enhancement.test.ts`

```ts
import {describe, expect, it} from 'vitest';
import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema, overlaySchema} from './enhancement';

describe('enhancement contract mirror', () => {
  it('validates the shared fixture (same file pytest validates)', () => {
    const plan = enhancementPlanSchema.parse(samplePlan);
    expect(plan.source_duration_s).toBe(48);
    expect(plan.overlays.length).toBeGreaterThanOrEqual(3);
  });

  it('rejects ai overlay without a prompt', () => {
    const bad = {
      id: 'x', start_s: 0, end_s: 2, type: 'ai_broll', placement: 'fullframe',
      prompt: '  ', text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow(/prompt/);
  });

  it('rejects text_effect without text', () => {
    const bad = {
      id: 'x', start_s: 0, end_s: 2, type: 'text_effect', placement: 'pip',
      prompt: null, text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow(/text/);
  });

  it('rejects end before start', () => {
    const bad = {
      id: 'x', start_s: 3, end_s: 3, type: 'ai_image', placement: 'pip',
      prompt: 'p', text: null, rationale: 'r', asset_url: null,
    };
    expect(() => overlaySchema.parse(bad)).toThrow();
  });

  it('rejects overlapping overlays at plan level', () => {
    const plan = {...samplePlan, overlays: [
      {...samplePlan.overlays[0], id: 'a', start_s: 0, end_s: 4},
      {...samplePlan.overlays[0], id: 'b', start_s: 2, end_s: 6},
    ]};
    expect(() => enhancementPlanSchema.parse(plan)).toThrow(/overlap/);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd remotion && npx vitest run src/types/enhancement.test.ts`
Expected: FAIL (cannot resolve ./enhancement)

- [ ] **Step 3: Write `remotion/src/types/enhancement.ts`**

```ts
/**
 * Mirror of schemas/enhancement.py (source of truth). Change Python first,
 * then this file, then the shared fixture sample_enhancement_plan.json.
 */
import {z} from 'zod';

const AI_TYPES = ['ai_broll', 'ai_image'] as const;
const TEXT_TYPES = ['text_effect', 'screen_recording'] as const;

export const overlaySchema = z
  .object({
    id: z.string().min(1),
    start_s: z.number().min(0),
    end_s: z.number(),
    type: z.enum(['ai_broll', 'ai_image', 'screen_recording', 'text_effect']),
    placement: z.enum(['fullframe', 'pip']),
    prompt: z.string().nullable().optional(),
    text: z.string().nullable().optional(),
    rationale: z.string().min(1),
    asset_url: z.string().nullable().optional(),
  })
  .refine((o) => o.end_s > o.start_s, {message: 'end_s must be > start_s', path: ['end_s']})
  .refine(
    (o) => !(AI_TYPES as readonly string[]).includes(o.type) || (o.prompt ?? '').trim().length > 0,
    {message: 'prompt is required for ai_broll/ai_image', path: ['prompt']},
  )
  .refine(
    (o) => !(TEXT_TYPES as readonly string[]).includes(o.type) || (o.text ?? '').trim().length > 0,
    {message: 'text is required for text_effect/screen_recording', path: ['text']},
  );

export const enhancementPlanSchema = z
  .object({
    source_video_url: z.string().min(1),
    source_duration_s: z.number().positive(),
    overlays: z.array(overlaySchema).default([]),
    platform_captions: z.record(z.string()),
    hashtags: z.record(z.array(z.string())),
  })
  .refine(
    (p) => new Set(p.overlays.map((o) => o.id)).size === p.overlays.length,
    {message: 'overlay ids must be unique'},
  )
  .refine(
    (p) => p.overlays.every((o) => o.end_s <= p.source_duration_s),
    {message: 'an overlay ends past source_duration_s'},
  )
  .refine((p) => {
    const ordered = [...p.overlays].sort((a, b) => a.start_s - b.start_s);
    return ordered.every((o, i) => i === 0 || o.start_s >= ordered[i - 1]!.end_s);
  }, {message: 'overlays overlap in time'});

export type Overlay = z.infer<typeof overlaySchema>;
export type EnhancementPlan = z.infer<typeof enhancementPlanSchema>;

/** Overlays sorted by start time. */
export const sortedOverlays = (plan: EnhancementPlan): Overlay[] =>
  [...plan.overlays].sort((a, b) => a.start_s - b.start_s);
```

- [ ] **Step 4: Run to verify pass + typecheck**

Run: `cd remotion && npx vitest run src/types/enhancement.test.ts && npm run typecheck`
Expected: PASS / clean

- [ ] **Step 5: Commit**

```bash
git add remotion/src/types/enhancement.ts remotion/src/types/enhancement.test.ts
git commit -m "feat(remotion): zod mirror of EnhancementPlan + shared-fixture test"
```

---

### Task 4: Local transcription (faster-whisper + ffmpeg)

**Files:**
- Modify: `pyproject.toml` (add `faster-whisper>=1.0`)
- Create: `agents/transcribe.py`
- Test: `tests/test_transcribe.py`

- [ ] **Step 1: Add the dependency**

In `pyproject.toml` `[project].dependencies`, add `"faster-whisper>=1.0"`. Run `uv sync` (installs ctranslate2 etc.; no model download until used). If resolution fails, report the exact error; do not pin other deps without reporting.

- [ ] **Step 2: Write the failing tests** — `tests/test_transcribe.py`

```python
from agents.transcribe import TranscriptSegment, format_for_prompt, total_duration_s


def seg(text, a, b) -> TranscriptSegment:
    return TranscriptSegment(text=text, start_s=a, end_s=b)


class TestFormatForPrompt:
    def test_renders_timestamped_lines(self):
        out = format_for_prompt([seg("Hello there", 0.0, 1.5), seg("welcome back", 1.5, 3.0)])
        assert "[0.0-1.5] Hello there" in out
        assert "[1.5-3.0] welcome back" in out

    def test_empty_segments(self):
        assert format_for_prompt([]) == ""


class TestTotalDuration:
    def test_uses_last_end(self):
        assert total_duration_s([seg("a", 0.0, 1.0), seg("b", 1.0, 4.2)]) == 4.2

    def test_empty_is_zero(self):
        assert total_duration_s([]) == 0.0


class TestSegmentModel:
    def test_end_after_start(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            TranscriptSegment(text="x", start_s=2.0, end_s=1.0)
```

- [ ] **Step 3: Run to verify fail**

Run: `uv run pytest tests/test_transcribe.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: Write `agents/transcribe.py`**

```python
"""Local transcription for the enhance track (spec §Components).

faster-whisper runs on the Mac mini — offline, no new vendor. ffmpeg extracts
audio. The model call and ffmpeg are boundaries; the formatting helpers are pure
and unit-tested. Tests never download a model.
"""

import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_MODEL_SIZE = "base"


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _end_after_start(self) -> "TranscriptSegment":
        if self.end_s < self.start_s:
            raise ValueError("end_s must be >= start_s")
        return self


def format_for_prompt(segments: list[TranscriptSegment]) -> str:
    """One '[start-end] text' line per segment — the transcript Claude reads."""
    return "\n".join(f"[{s.start_s}-{s.end_s}] {s.text.strip()}" for s in segments)


def total_duration_s(segments: list[TranscriptSegment]) -> float:
    """Video length proxy: the last segment's end (0.0 if no speech)."""
    return segments[-1].end_s if segments else 0.0


def extract_audio(video_path: Path, out_wav: Path) -> None:
    """ffmpeg: strip a mono 16 kHz wav for Whisper (boundary)."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-ac", "1", "-ar", "16000", str(out_wav)],
        check=True,
        capture_output=True,
    )


def transcribe(video_path: Path, model_size: str = DEFAULT_MODEL_SIZE) -> list[TranscriptSegment]:
    """Transcribe a local video file to timestamped segments (boundary)."""
    from faster_whisper import WhisperModel  # local import: tests never load it

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        extract_audio(video_path, wav)
        model = WhisperModel(model_size, device="auto", compute_type="int8")
        segments, _info = model.transcribe(str(wav), word_timestamps=False)
        return [
            TranscriptSegment(text=s.text, start_s=round(s.start, 2), end_s=round(s.end, 2))
            for s in segments
        ]
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_transcribe.py -q && uv run ruff check .`
Expected: PASS / clean

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock agents/transcribe.py tests/test_transcribe.py
git commit -m "feat(agents): local Whisper transcription with pure formatting helpers"
```

---

### Task 5: Enhancement analyzer + CLI (Claude → EnhancementPlan)

**Files:**
- Create: `agents/enhance.py`
- Modify: `agents/db.py` (add `insert_enhanced_video`, `set_video_status`)
- Test: `tests/test_enhance.py`

Design rule (matches `script_writer.py`): prompt builder, parser, and summary are PURE (tested, no network). The Claude call (`generate_enhancement_plan`) and DB writes are thin boundaries tests never hit. The LLM returns `{overlays, platform_captions, hashtags}` only; `parse_enhancement_plan` injects the known `source_video_url`/`source_duration_s` so the model can't hallucinate them.

- [ ] **Step 1: Write the failing tests** — `tests/test_enhance.py`

```python
import json

import pytest

from agents.enhance import (
    HARD_CONSTRAINTS,
    build_enhancement_prompt,
    parse_enhancement_plan,
    render_plan_summary,
)
from schemas.enhancement import EnhancementPlan

GOOD_LLM_JSON = json.dumps(
    {
        "overlays": [
            {
                "id": "ov-1",
                "start_s": 2.0,
                "end_s": 6.0,
                "type": "ai_image",
                "placement": "pip",
                "prompt": "Isometric diagram of a pipeline, dark navy, amber accents",
                "text": None,
                "rationale": "names the stages",
                "asset_url": None,
            },
            {
                "id": "ov-2",
                "start_s": 8.0,
                "end_s": 12.0,
                "type": "screen_recording",
                "placement": "fullframe",
                "prompt": None,
                "text": "the CLI printing a video id",
                "rationale": "demo builds trust",
                "asset_url": None,
            },
        ],
        "platform_captions": {"youtube": "How I built it"},
        "hashtags": {"youtube": ["#build"]},
    }
)

SRC = "https://x.supabase.co/storage/v1/object/public/uploads/talk.mp4"


class TestPrompt:
    def test_constraints_present(self):
        low = HARD_CONSTRAINTS.lower()
        for phrase in ("overlap", "placement", "rationale", "screen_recording"):
            assert phrase in low

    def test_prompt_embeds_transcript_and_duration(self):
        p = build_enhancement_prompt("[0.0-3.0] hello world", 30.0)
        assert "hello world" in p
        assert "30" in p
        assert "overlays" in p


class TestParse:
    def test_parses_and_injects_source_fields(self):
        plan = parse_enhancement_plan(GOOD_LLM_JSON, SRC, 20.0)
        assert isinstance(plan, EnhancementPlan)
        assert plan.source_video_url == SRC
        assert plan.source_duration_s == 20.0
        assert len(plan.overlays) == 2

    def test_parses_fenced_json(self):
        plan = parse_enhancement_plan(f"```json\n{GOOD_LLM_JSON}\n```", SRC, 20.0)
        assert len(plan.overlays) == 2

    def test_overlay_past_duration_raises(self):
        with pytest.raises(ValueError):
            parse_enhancement_plan(GOOD_LLM_JSON, SRC, 5.0)  # ov-2 ends at 12 > 5

    def test_no_json_object_raises(self):
        with pytest.raises(ValueError, match="JSON"):
            parse_enhancement_plan("I cannot help with that.", SRC, 20.0)


class TestSummary:
    def test_summary_lists_each_overlay_with_time_and_type(self):
        plan = parse_enhancement_plan(GOOD_LLM_JSON, SRC, 20.0)
        md = render_plan_summary(plan)
        assert "# Enhancement plan" in md
        assert "ov-1" in md and "ov-2" in md
        assert "ai_image" in md and "screen_recording" in md
        assert "2.0" in md  # a start time
        assert "SCREEN REC" in md.upper()  # flags the manual swap
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_enhance.py -q`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Write `agents/enhance.py`**

```python
"""Stage: raw video -> reviewable EnhancementPlan, then approval (spec §Data flow).

CLI:
    uv run python -m agents.enhance plan --video <supabase_url> [--local <path>]
    uv run python -m agents.enhance approve --id <video_id>

Pure functions (prompt/parse/summary) are unit-tested. The Claude call and DB
writes are thin boundaries.
"""

import argparse
import json
import re
from pathlib import Path

from crewai import Agent, Task
from pydantic import ValidationError

from agents.db import get_client, insert_enhanced_video, set_video_status
from agents.llm import claude_llm
from agents.transcribe import format_for_prompt, total_duration_s, transcribe
from schemas.enhancement import EnhancementPlan

HARD_CONSTRAINTS = """HARD CONSTRAINTS (violating any makes the plan unusable):
- Suggest 3-8 overlays. Each overlay has a start_s and end_s within the video length.
- Overlays MUST NOT overlap in time. Leave the speaker on screen between overlays.
- Choose placement per overlay: "fullframe" (cutaway covering the picture) or "pip"
  (corner box while the speaker keeps talking). B-roll and screen recordings are
  usually fullframe; diagrams/stills and text effects are usually pip.
- type is one of: ai_broll (generated motion b-roll), ai_image (generated still),
  screen_recording (the creator records their real screen — you only LABEL it),
  text_effect (an on-screen text callout).
- ai_broll/ai_image MUST include a detailed cinematic "prompt" and null "text".
- screen_recording/text_effect MUST include "text" (the label/words) and null "prompt".
- Every overlay needs a one-line "rationale" tied to what is being said at that moment.
- Anchor each overlay to the transcript timestamps — enhance the actual claims, not filler."""

SCHEMA_GUIDE = """Respond with ONLY this JSON object (no commentary):
{
  "overlays": [
    {"id": "ov-1", "start_s": float, "end_s": float,
     "type": "ai_broll|ai_image|screen_recording|text_effect",
     "placement": "fullframe|pip",
     "prompt": str|null, "text": str|null,
     "rationale": str, "asset_url": null}
  ],
  "platform_captions": {"youtube": str, "tiktok": str, "instagram": str},
  "hashtags": {"youtube": [str], "tiktok": [str], "instagram": [str]}
}"""


def build_enhancement_prompt(transcript_text: str, duration_s: float) -> str:
    return f"""You are a short-form video editor. A creator recorded a {duration_s:.0f}-second \
talking-head video explaining a project. Below is the timestamped transcript. Propose timed \
visual overlays that make it more engaging and clearer, anchored to what is said.

Transcript:
{transcript_text}

{HARD_CONSTRAINTS}

{SCHEMA_GUIDE}"""


def _extract_json_object(raw: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in model output: {raw[:200]!r}")
    return cleaned[start : end + 1]


def parse_enhancement_plan(
    raw: str, source_video_url: str, source_duration_s: float
) -> EnhancementPlan:
    """Parse the LLM's {overlays, captions, hashtags} and inject the known source fields."""
    try:
        data = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"model output was not valid JSON: {exc}") from exc
    data["source_video_url"] = source_video_url
    data["source_duration_s"] = source_duration_s
    try:
        return EnhancementPlan.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"model output failed EnhancementPlan validation: {exc}") from exc


def render_plan_summary(plan: EnhancementPlan) -> str:
    """Human-readable review of the plan (printed at the checkpoint)."""
    lines = [
        "# Enhancement plan",
        f"Source: {plan.source_video_url} ({plan.source_duration_s:.0f}s)",
        f"{len(plan.overlays)} overlay(s):",
        "",
    ]
    for o in plan.sorted_overlays():
        detail = o.prompt or o.text or ""
        flag = "  ⚠ SCREEN REC — record + swap in CapCut" if o.type == "screen_recording" else ""
        lines.append(
            f"- [{o.start_s:.1f}-{o.end_s:.1f}s] {o.id} · {o.type} · {o.placement} — "
            f"{detail}  ({o.rationale}){flag}"
        )
    return "\n".join(lines)


def build_enhance_agent() -> Agent:
    return Agent(
        role="Short-form video editor",
        goal="Suggest timed visual overlays that sharpen a talking-head explainer",
        backstory="Edits founder and developer videos; knows when a cutaway earns attention.",
        llm=claude_llm(temperature=0.6),
        verbose=False,
    )


def generate_enhancement_plan(
    transcript_text: str, source_duration_s: float, source_video_url: str
) -> EnhancementPlan:
    agent = build_enhance_agent()
    task = Task(
        description=build_enhancement_prompt(transcript_text, source_duration_s),
        expected_output="A single JSON object of overlays + captions + hashtags",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_enhancement_plan(result.raw, source_video_url, source_duration_s)


def run_plan(video_url: str, local_path: str | None = None) -> str:
    """Transcribe + analyze a raw video, insert a plan_ready row, print the summary."""
    source = Path(local_path) if local_path else None
    if source is None:
        raise RuntimeError("pass --local <downloaded path> for transcription in v1")
    segments = transcribe(source)
    transcript_text = format_for_prompt(segments)
    duration = total_duration_s(segments)
    plan = generate_enhancement_plan(transcript_text, duration, video_url)
    video_id = insert_enhanced_video(
        plan=plan,
        transcript=[s.model_dump(mode="json") for s in segments],
        client=get_client(),
    )
    print(render_plan_summary(plan))
    print(f"\n[enhance] inserted video {video_id} (status=plan_ready)")
    print(f"[enhance] approve with: uv run python -m agents.enhance approve --id {video_id}")
    return video_id


def run_approve(video_id: str) -> None:
    set_video_status(video_id, "plan_approved", client=get_client())
    print(f"[enhance] video {video_id} -> plan_approved (n8n will generate overlays + render)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents.enhance")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="raw video -> reviewable overlay plan")
    plan.add_argument("--video", required=True, help="Supabase URL stored on the row")
    plan.add_argument("--local", default=None, help="local file path to transcribe")
    appr = sub.add_parser("approve", help="approve a plan_ready video")
    appr.add_argument("--id", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        run_plan(args.video, args.local)
    elif args.command == "approve":
        run_approve(args.id)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add DB helpers to `agents/db.py`** (append after `top_taste_hooks`)

```python
def insert_enhanced_video(
    plan: "EnhancementPlan", transcript: list[dict], client: Client | None = None
) -> str:
    """Insert an enhance-track row at status=plan_ready. Returns the new video id."""
    client = client or get_client()
    row = {
        "kind": "enhanced",
        "status": "plan_ready",
        "source_video_url": plan.source_video_url,
        "transcript": transcript,
        "enhancement_json": plan.model_dump(mode="json"),
    }
    result = client.table("videos").insert(row).execute()
    if not result.data:
        raise RuntimeError("Supabase insert returned no data for enhanced video")
    return result.data[0]["id"]


def set_video_status(video_id: str, status: str, client: Client | None = None) -> None:
    """Move a video to a new status (e.g. plan_approved)."""
    client = client or get_client()
    client.table("videos").update({"status": status}).eq("id", video_id).execute()
```

Add the import at the top of `agents/db.py`: `from schemas.enhancement import EnhancementPlan` (used only as a type hint — keep it a real import so ruff/typing pass; if a circular import appears, change the annotation to a string `"EnhancementPlan"` and import under `if TYPE_CHECKING:`).

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest -q && uv run ruff check .`
Expected: PASS (existing + new) / clean

- [ ] **Step 6: Commit**

```bash
git add agents/enhance.py agents/db.py tests/test_enhance.py
git commit -m "feat(agents): enhancement analyzer (Claude -> plan) + plan/approve CLI"
```

---

### Task 6: EnhancedTalkingHead composition + overlay timeline

**Files:**
- Create: `remotion/src/lib/overlay-timeline.ts`
- Test: `remotion/src/lib/overlay-timeline.test.ts`
- Create: `remotion/src/components/Overlay.tsx`
- Create: `remotion/src/compositions/EnhancedTalkingHead.tsx`
- Modify: `remotion/src/Root.tsx` (register composition)
- Create: `remotion/src/lib/enhancement-fixture.ts`

- [ ] **Step 1: Write the failing timeline test** — `remotion/src/lib/overlay-timeline.test.ts`

```ts
import {describe, expect, it} from 'vitest';
import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema} from '../types/enhancement';
import {overlayWindow, planDurationInFrames, resolveSourceSrc} from './overlay-timeline';

const plan = enhancementPlanSchema.parse(samplePlan);
const FPS = 30;

describe('overlayWindow', () => {
  it('maps seconds to a frame window', () => {
    const w = overlayWindow(plan.overlays[0]!, FPS); // 3.0-9.0s
    expect(w.from).toBe(90);
    expect(w.durationInFrames).toBe(180);
  });
  it('always at least one frame', () => {
    const w = overlayWindow({...plan.overlays[0]!, start_s: 1.0, end_s: 1.001}, FPS);
    expect(w.durationInFrames).toBeGreaterThan(0);
  });
});

describe('planDurationInFrames', () => {
  it('rounds source duration to frames', () => {
    expect(planDurationInFrames(plan, FPS)).toBe(Math.round(48 * FPS));
  });
});

describe('resolveSourceSrc', () => {
  it('passes http urls through', () => {
    expect(resolveSourceSrc('https://x/v.mp4')).toBe('https://x/v.mp4');
  });
  it('wraps relative paths for staticFile lookup', () => {
    expect(resolveSourceSrc('smoke-base.mp4')).toMatch(/smoke-base\.mp4$/);
  });
  it('empty stays empty (composition shows brand bg)', () => {
    expect(resolveSourceSrc('')).toBe('');
  });
});
```

- [ ] **Step 2: Run to verify fail**

Run: `cd remotion && npx vitest run src/lib/overlay-timeline.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Write `remotion/src/lib/overlay-timeline.ts`**

```ts
import {staticFile} from 'remotion';
import type {EnhancementPlan, Overlay} from '../types/enhancement';

export type FrameWindow = {from: number; durationInFrames: number};

export const overlayWindow = (overlay: Overlay, fps: number): FrameWindow => ({
  from: Math.round(overlay.start_s * fps),
  durationInFrames: Math.max(1, Math.round((overlay.end_s - overlay.start_s) * fps)),
});

export const planDurationInFrames = (plan: EnhancementPlan, fps: number): number =>
  Math.max(1, Math.round(plan.source_duration_s * fps));

/** http(s) urls pass through; relative paths resolve via staticFile (public/); empty stays empty. */
export const resolveSourceSrc = (url: string): string => {
  if (url === '') return '';
  if (/^https?:\/\//.test(url)) return url;
  return staticFile(url);
};
```

- [ ] **Step 4: Run to verify pass**

Run: `cd remotion && npx vitest run src/lib/overlay-timeline.test.ts`
Expected: PASS

- [ ] **Step 5: Write `remotion/src/components/Overlay.tsx`** (no unit test — exercised by the smoke render)

```tsx
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import {resolveSourceSrc} from '../lib/overlay-timeline';
import type {Overlay as OverlayT} from '../types/enhancement';

const PlaceholderCard: React.FC<{label: string; tone?: string}> = ({label, tone}) => (
  <AbsoluteFill
    style={{
      backgroundColor: BRAND.surface,
      border: `4px dashed ${tone ?? BRAND.accent}`,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 64,
    }}
  >
    <div style={{color: tone ?? BRAND.accent, fontSize: 56, fontWeight: 800, textAlign: 'center'}}>
      {label}
    </div>
  </AbsoluteFill>
);

const Visual: React.FC<{overlay: OverlayT}> = ({overlay}) => {
  const url = overlay.asset_url ?? '';
  if (overlay.type === 'screen_recording') {
    return <PlaceholderCard label={`SCREEN REC:\n${overlay.text ?? ''}`} />;
  }
  if (overlay.type === 'text_effect') {
    const frame = useCurrentFrame();
    const {fps} = useVideoConfig();
    const pop = spring({frame, fps, config: {damping: 12, mass: 0.5}});
    return (
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: 48}}>
        <div
          style={{
            color: BRAND.text,
            backgroundColor: 'rgba(11,18,32,0.72)',
            padding: '20px 32px',
            borderRadius: 18,
            fontSize: 64,
            fontWeight: 800,
            textAlign: 'center',
            transform: `scale(${0.9 + 0.1 * pop})`,
          }}
        >
          {overlay.text}
        </div>
      </AbsoluteFill>
    );
  }
  if (!url) {
    return <PlaceholderCard label={`${overlay.type}:\n${overlay.prompt ?? ''}`} tone={BRAND.muted} />;
  }
  if (overlay.type === 'ai_broll') {
    return (
      <AbsoluteFill>
        <OffthreadVideo src={resolveSourceSrc(url)} muted style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <Img src={resolveSourceSrc(url)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};

/** Full-frame cutaway, or a picture-in-picture corner box. */
export const OverlayLayer: React.FC<{overlay: OverlayT}> = ({overlay}) => {
  if (overlay.placement === 'pip') {
    return (
      <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'flex-end', padding: 48}}>
        <div
          style={{
            width: '42%',
            aspectRatio: '4 / 5',
            borderRadius: 24,
            overflow: 'hidden',
            border: `6px solid ${BRAND.accent}`,
            boxShadow: '0 12px 48px rgba(0,0,0,0.5)',
            position: 'relative',
          }}
        >
          <Visual overlay={overlay} />
        </div>
      </AbsoluteFill>
    );
  }
  return <Visual overlay={overlay} />;
};
```

- [ ] **Step 6: Write `remotion/src/lib/enhancement-fixture.ts`**

```ts
import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema} from '../types/enhancement';

export const SAMPLE_PLAN = enhancementPlanSchema.parse(samplePlan);
```

- [ ] **Step 7: Write `remotion/src/compositions/EnhancedTalkingHead.tsx`**

```tsx
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence} from 'remotion';
import {BrandFrame} from '../components/BrandFrame';
import {OverlayLayer} from '../components/Overlay';
import {FPS} from '../lib/theme';
import {overlayWindow, resolveSourceSrc} from '../lib/overlay-timeline';
import {sortedOverlays, type EnhancementPlan} from '../types/enhancement';

export type EnhancedProps = {plan: EnhancementPlan};

export const EnhancedTalkingHead: React.FC<EnhancedProps> = ({plan}) => {
  const src = resolveSourceSrc(plan.source_video_url);
  return (
    <AbsoluteFill>
      {src ? (
        <OffthreadVideo src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      ) : (
        <BrandFrame>{null}</BrandFrame>
      )}
      {sortedOverlays(plan).map((overlay) => {
        const win = overlayWindow(overlay, FPS);
        return (
          <Sequence key={overlay.id} from={win.from} durationInFrames={win.durationInFrames} name={overlay.id}>
            <OverlayLayer overlay={overlay} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
```

(`sortedOverlays` comes from `../types/enhancement`; `overlayWindow`/`resolveSourceSrc` from `../lib/overlay-timeline`; `FPS` from `../lib/theme`. Do not create any extra helper file.)

- [ ] **Step 8: Register in `remotion/src/Root.tsx`** — add imports and a `<Composition>`:

```tsx
import {EnhancedTalkingHead} from './compositions/EnhancedTalkingHead';
import {SAMPLE_PLAN} from './lib/enhancement-fixture';
import {planDurationInFrames} from './lib/overlay-timeline';
import type {EnhancedProps} from './compositions/EnhancedTalkingHead';
```

Inside the `<>` fragment, add (preview uses an empty source so Studio shows the brand bg + overlays without a committed binary):

```tsx
    <Composition
      id="EnhancedTalkingHead"
      component={EnhancedTalkingHead}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={Math.round(SAMPLE_PLAN.source_duration_s * FPS)}
      defaultProps={{plan: {...SAMPLE_PLAN, source_video_url: ''}} satisfies EnhancedProps}
      calculateMetadata={({props}: {props: EnhancedProps}) => ({
        durationInFrames: planDurationInFrames(props.plan, FPS),
      })}
    />
```

- [ ] **Step 9: Typecheck + smoke render** (the acceptance gate — generates a throwaway base clip; do NOT skip)

```bash
cd remotion
npm run typecheck
mkdir -p public
ffmpeg -y -f lavfi -i testsrc=size=1080x1920:rate=30:duration=12 -pix_fmt yuv420p public/smoke-base.mp4
cat > /tmp/enh-props.json <<'JSON'
{"plan": {"source_video_url": "smoke-base.mp4", "source_duration_s": 12.0,
  "overlays": [
    {"id":"ov-1","start_s":1.0,"end_s":4.0,"type":"text_effect","placement":"pip","prompt":null,"text":"2-5 min / video","rationale":"stat","asset_url":null},
    {"id":"ov-2","start_s":5.0,"end_s":9.0,"type":"screen_recording","placement":"fullframe","prompt":null,"text":"the CLI output","rationale":"demo","asset_url":null}
  ],
  "platform_captions": {"youtube":"x"}, "hashtags": {"youtube":["#x"]}}}
JSON
npx remotion render EnhancedTalkingHead out/smoke-enhanced.mp4 --props=/tmp/enh-props.json --frames=0-90
ls -la out/smoke-enhanced.mp4
echo "public/smoke-base.mp4" >> .gitignore
```

Expected: typecheck clean; render exits 0; `out/smoke-enhanced.mp4` is non-empty (text_effect PIP over the test pattern, then a SCREEN REC placeholder cutaway). If `staticFile` can't find `smoke-base.mp4`, confirm it is in `remotion/public/`.

- [ ] **Step 10: Run the full vitest suite**

Run: `cd remotion && npx vitest run`
Expected: all PASS (prior + new overlay-timeline + enhancement mirror tests)

- [ ] **Step 11: Commit**

```bash
git add remotion/src/ remotion/.gitignore
git commit -m "feat(remotion): EnhancedTalkingHead composition + overlay timeline"
```

---

### Task 7: Render server — kind=enhanced branch

**Files:**
- Modify: `remotion/render-server/src/supabase.ts` (add `kind`, `enhancement_json` to VideoRow + select)
- Modify: `remotion/render-server/src/render.ts` (render EnhancedTalkingHead for enhanced rows)
- Modify: `remotion/render-server/src/app.ts` (allow enhanced rows past the template guard)
- Test: `remotion/render-server/src/app.test.ts` (extend)

- [ ] **Step 1: Extend the failing test** — add to `remotion/render-server/src/app.test.ts`

Add an `enhancedReadyRow` near `assetsReadyRow`:
```ts
const enhancedReadyRow = {
  id: 'enh-1',
  status: 'assets_ready',
  kind: 'enhanced',
  template: null,
  topic: 'My build',
  script_json: null,
  asset_urls: null,
  enhancement_json: {source_video_url: 'https://x/v.mp4', source_duration_s: 10, overlays: [],
    platform_captions: {youtube: 'x'}, hashtags: {youtube: ['#x']}},
};
```
Add a test inside `describe('POST /render', ...)`:
```ts
  it('renders an enhanced (kind=enhanced) row even though template is null', async () => {
    mocks.fetchVideo.mockResolvedValue(enhancedReadyRow);
    mocks.renderVideoJob.mockResolvedValue({
      renderUrl: 'https://x/renders/enh-1.mp4',
      thumbnailUrl: 'https://x/renders/enh-1.png',
    });
    const res = await request(app).post('/render').send({video_id: 'enh-1'});
    expect(res.status).toBe(200);
    expect(mocks.updateVideo).toHaveBeenCalledWith('enh-1', {
      status: 'qa_pending',
      render_url: 'https://x/renders/enh-1.mp4',
      thumbnail_url: 'https://x/renders/enh-1.png',
    });
  });
```

- [ ] **Step 2: Run to verify the new test fails**

Run: `cd remotion && npx vitest run render-server`
Expected: FAIL — the 422 template guard rejects the null-template enhanced row.

- [ ] **Step 3: Update `remotion/render-server/src/supabase.ts`**

Change `VideoRow` to add `kind` and `enhancement_json`, and widen `template` to nullable:
```ts
export type VideoRow = {
  id: string;
  status: string;
  kind: 'generated' | 'enhanced';
  template: 'explainer' | 'tutorial' | 'listicle' | 'comparison' | null;
  topic: string;
  script_json: unknown;
  asset_urls: unknown;
  enhancement_json: unknown;
};
```
Update the select string in `fetchVideo` to: `'id,status,kind,template,topic,script_json,asset_urls,enhancement_json'`.

- [ ] **Step 4: Update `remotion/render-server/src/app.ts`** — only enforce the template guard for generated rows:

Replace the template-guard block with:
```ts
      if (video.kind !== 'enhanced' && !RENDERABLE_TEMPLATES.has(video.template ?? '')) {
        res.status(422).json({
          error: `video ${videoId} has unknown/missing template '${video.template}'`,
        });
        return;
      }
```

- [ ] **Step 5: Update `remotion/render-server/src/render.ts`** — branch on kind:

Add the enhancement import and an enhanced render path. Add near the top:
```ts
import {enhancementPlanSchema} from '../../src/types/enhancement';
```
In `renderVideoJob`, before the existing generated logic, branch:
```ts
  const serveUrl = await getBundle();
  const workDir = await mkdtemp(join(tmpdir(), `render-${video.id}-`));
  try {
    if (video.kind === 'enhanced') {
      const plan = enhancementPlanSchema.parse(video.enhancement_json);
      const inputProps = {plan};
      const composition = await selectComposition({serveUrl, id: 'EnhancedTalkingHead', inputProps});
      const rawPath = join(workDir, 'raw.mp4');
      const finalPath = join(workDir, 'final.mp4');
      const thumbPath = join(workDir, 'thumb.png');
      await renderMedia({composition, serveUrl, codec: 'h264', outputLocation: rawPath, inputProps});
      await compress(rawPath, finalPath);
      const thumbProps = {headline: plan.platform_captions.youtube ?? 'Build Commons', baseImageUrl: null};
      const thumbComposition = await selectComposition({serveUrl, id: 'Thumbnail', inputProps: thumbProps});
      await renderStill({composition: thumbComposition, serveUrl, output: thumbPath, inputProps: thumbProps});
      const [renderUrl, thumbnailUrl] = await Promise.all([
        uploadRender(`${video.id}/final.mp4`, await readFile(finalPath), 'video/mp4'),
        uploadRender(`${video.id}/thumbnail.png`, await readFile(thumbPath), 'image/png'),
      ]);
      return {renderUrl, thumbnailUrl};
    }
    // ... existing generated-video logic stays here (script_json/asset_urls path) ...
```
Keep the existing generated path intact inside the same `try` (after the enhanced branch returns). Ensure the existing `script`/`assets` parsing only runs in the generated branch — move those two `videoScriptSchema.parse` / `videoAssetsSchema.parse` lines into the generated branch so an enhanced row (null script_json) never hits them.

- [ ] **Step 6: Run to verify pass + typecheck**

Run: `cd remotion && npx vitest run && npm run typecheck`
Expected: all PASS / clean

- [ ] **Step 7: Commit**

```bash
git add remotion/render-server/
git commit -m "feat(render-server): render enhanced (kind=enhanced) videos via EnhancedTalkingHead"
```

---

### Task 8: n8n enhance workflow

**Files:**
- Create: `n8n/workflows/enhance.json`
- Test: `tests/test_n8n_workflows.py` (extend the parametrized fixture list)

- [ ] **Step 1: Extend the failing test** — in `tests/test_n8n_workflows.py`, add `"enhance.json"` to `WORKFLOW_FILES`. The existing parametrized tests (shape, single trigger, connections resolve, no secrets) then cover it. Also add a focused test:

```python
def test_enhance_overlay_node_has_retries():
    import json
    from pathlib import Path
    wf = json.loads((Path(__file__).parent.parent / "n8n" / "workflows" / "enhance.json").read_text())
    providers = [n for n in wf["nodes"]
                 if n["type"] == "n8n-nodes-base.httpRequest" and "render" not in n["name"].lower()]
    assert providers
    for n in providers:
        assert n.get("retryOnFail") is True
        assert n.get("maxTries") == 3
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run pytest tests/test_n8n_workflows.py -q`
Expected: FAIL (enhance.json missing)

- [ ] **Step 3: Write `n8n/workflows/enhance.json`** (skeleton — Phase-3 UI wiring assembles per-overlay asset_url back into enhancement_json; documented in setup.md)

```json
{
  "name": "BC Enhance — Overlay Assets + Render",
  "nodes": [
    {
      "parameters": {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}},
      "id": "trigger-15min",
      "name": "Every 15 minutes",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "select id, enhancement_json from videos where kind = 'enhanced' and status = 'plan_approved' order by created_at limit 1"
      },
      "id": "fetch-approved-plans",
      "name": "Fetch approved plans",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [220, 0]
    },
    {
      "parameters": {
        "fieldToSplitOut": "enhancement_json.overlays",
        "include": "selectedOtherFields",
        "fieldsToInclude": "id"
      },
      "id": "split-overlays",
      "name": "Split overlays",
      "type": "n8n-nodes-base.splitOut",
      "typeVersion": 1,
      "position": [440, 0]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpQueryAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"contents\": [{\"parts\": [{\"text\": {{ JSON.stringify($json[\"enhancement_json.overlays\"].prompt || \"\") }}}]}]}"
      },
      "id": "nano-banana",
      "name": "Nano Banana still (ai_image)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, -90],
      "retryOnFail": true,
      "maxTries": 3,
      "onError": "continueErrorOutput"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpQueryAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"instances\": [{\"prompt\": {{ JSON.stringify($json[\"enhancement_json.overlays\"].prompt || \"\") }}}]}"
      },
      "id": "veo",
      "name": "Veo b-roll (ai_broll)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, 90],
      "retryOnFail": true,
      "maxTries": 3,
      "onError": "continueErrorOutput"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "update videos set status = 'assets_ready', enhancement_json = $1::jsonb where id = $2",
        "options": {"queryReplacement": "={{ JSON.stringify($json.enhancement_json) }},{{ $json.id }}"}
      },
      "id": "save-overlays",
      "name": "Save overlay asset_urls",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [900, 0]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://host.docker.internal:3333/render",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"video_id\": \"{{ $json.id }}\"}"
      },
      "id": "trigger-render",
      "name": "Trigger render",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1120, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "update videos set qa_notes = concat(coalesce(qa_notes, ''), ' overlay asset generation failed after retries — manual review') where id = $1",
        "options": {"queryReplacement": "={{ $json.id }}"}
      },
      "id": "flag-manual",
      "name": "Flag manual review",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [900, 220]
    }
  ],
  "connections": {
    "Every 15 minutes": {"main": [[{"node": "Fetch approved plans", "type": "main", "index": 0}]]},
    "Fetch approved plans": {"main": [[{"node": "Split overlays", "type": "main", "index": 0}]]},
    "Split overlays": {
      "main": [[
        {"node": "Nano Banana still (ai_image)", "type": "main", "index": 0},
        {"node": "Veo b-roll (ai_broll)", "type": "main", "index": 0}
      ]]
    },
    "Nano Banana still (ai_image)": {
      "main": [
        [{"node": "Save overlay asset_urls", "type": "main", "index": 0}],
        [{"node": "Flag manual review", "type": "main", "index": 0}]
      ]
    },
    "Veo b-roll (ai_broll)": {
      "main": [
        [{"node": "Save overlay asset_urls", "type": "main", "index": 0}],
        [{"node": "Flag manual review", "type": "main", "index": 0}]
      ]
    },
    "Save overlay asset_urls": {"main": [[{"node": "Trigger render", "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_n8n_workflows.py -q`
Expected: PASS (parametrized tests now include enhance.json + the retry test)

- [ ] **Step 5: Commit**

```bash
git add n8n/workflows/enhance.json tests/test_n8n_workflows.py
git commit -m "feat(n8n): enhance workflow — overlay asset gen + render trigger"
```

---

### Task 9: Docs + full-suite verification

**Files:**
- Modify: `README.md` (manual-track section: add the enhance flow)
- Modify: `docs/setup.md` (enhance-track usage + Phase-3 wiring note)
- Modify: `CLAUDE.md` + `AGENTS.md` (note the enhance track + EnhancementPlan contract; keep byte-identical)

- [ ] **Step 1: Update `README.md`** — replace the "Manual track" subsection so it documents BOTH paths: (a) the existing "drop your finished clip in as render_url" path, and (b) the new auto-enhance path:

````markdown
### Manual track (you already have a raw video)

Two ways in, depending on whether you want the pipeline to add visuals for you:

**A) Auto-enhance a talking-head video.** Upload your raw clip to Supabase Storage, then let Claude suggest and composite timed overlays (AI b-roll, stills, text effects, screen-recording placeholders) onto your footage:

```bash
uv run python -m agents.enhance plan --video <supabase_url> --local ./my-talk.mp4   # transcribe + propose a plan
# review the printed plan, then:
uv run python -m agents.enhance approve --id <video_id>                              # kicks off asset gen + compositing
```

It transcribes locally (Whisper), Claude writes a reviewable overlay plan (the checkpoint), and on approval n8n generates the AI assets and the render server composites them onto your video into the same `qa_pending` review queue. Screen-recording overlays render as a labeled placeholder you swap for your real capture in CapCut.

**B) Drop a finished clip straight into publishing.** For fully self-edited videos (sponsor reads, same-day reactions), skip Stages 1–3 entirely — insert a row with your finished file as `render_url`:

```sql
insert into videos (status, kind, topic, template, render_url, script_json)
values ('approved', 'generated', 'My screen-recording tutorial', 'tutorial',
        'https://<your-project>.supabase.co/storage/v1/object/public/renders/my-clip.mp4',
        '{"platform_captions": {"youtube": "...", "tiktok": "...", "instagram": "..."},
          "hashtags": {"youtube": ["#..."], "tiktok": ["#..."], "instagram": ["#..."]}}'::jsonb);
```

Both converge at the publisher. Use `qa_pending` instead of `approved` to pass through your own review queue first.
````

- [ ] **Step 2: Append an enhance section to `docs/setup.md`** (after the existing manual/Stage sections):

```markdown
## Enhance track (auto-composite a talking-head video)

1. Apply migration `supabase/migrations/0002_enhancement.sql` (adds `kind`, `source_video_url`, `transcript`, `enhancement_json` + the `uploaded`/`plan_ready`/`plan_approved` statuses).
2. First run downloads a Whisper model (~150 MB) to cache; subsequent runs are offline.
3. `uv run python -m agents.enhance plan --video <url> --local <path>` → review the printed plan → `... approve --id <id>`.
4. Phase-3 n8n wiring for `enhance.json`: map each generated overlay asset back into `enhancement_json.overlays[].asset_url` before the `Save overlay asset_urls` write (the committed workflow is a skeleton, same as generate/publish). Screen-recording and text_effect overlays need no generated asset.
```

- [ ] **Step 3: Update `CLAUDE.md` then copy to `AGENTS.md`** — add a row/line noting the enhance track. In the Layout table's `agents/` row, append `+ enhance (raw-video → overlay plan)`; in the `schemas/` row append `+ EnhancementPlan`. Add a Rules bullet:
```markdown
- Enhance track (manual): `agents/enhance.py` + `agents/transcribe.py` turn an uploaded video into an `EnhancementPlan` (`schemas/enhancement.py` ↔ `remotion/src/types/enhancement.ts`), composited by the `EnhancedTalkingHead` composition. `kind=enhanced` rows skip the template guard.
```
Then: `cp CLAUDE.md AGENTS.md`.

- [ ] **Step 4: Full-suite verification**

```bash
cd /Users/tannerkunz/coding/build-commons-pipeline
uv run pytest -q                      # all green
uv run ruff check .                   # clean
cd remotion && npm run typecheck && npx vitest run && cd ..
cmp CLAUDE.md AGENTS.md               # silent
grep -rn "__[A-Z_]\+__" . --exclude-dir=node_modules --exclude-dir=.git | grep -v docs/superpowers || true   # zero
```

- [ ] **Step 5: Commit**

```bash
git add README.md docs/setup.md CLAUDE.md AGENTS.md
git commit -m "docs: document the raw-video enhance track"
```

---

## Out of scope (tracked, not built here)

Frame-level vision analysis, overlapping/stacked overlays, auto-capturing screen recordings, a plan-editing UI, and the full n8n response-mapping (Phase-3 UI work, same as the other workflows).
