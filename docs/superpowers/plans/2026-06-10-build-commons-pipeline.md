# Build Commons Content Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the full `build-commons-pipeline` repo — Pydantic/TS script contract, Supabase schema, CrewAI Stage-1 agents, Remotion compositions + render server, n8n workflow JSONs, analyst agent, CI, and docs — per `docs/spec.md`.

**Architecture:** A Python (uv) package (`agents/`, `schemas/`) produces a `VideoScript` JSON contract stored in Supabase; n8n orchestrates asset generation and calls an Express render server inside the Node/React `remotion/` package, which renders branded 1080×1920 videos + thumbnails. An analyst agent closes the loop by scoring analytics and promoting hooks into the taste library. The repo is scaffolded from the Tree template at `/Users/tannerkunz/coding/project_template/template/`.

**Tech Stack:** Python 3.12 + uv + Pydantic v2 + CrewAI + supabase-py + httpx + pytest; Node 20 + Remotion 4 + React 18 + zod + Express + vitest/supertest; Supabase Postgres/Storage; n8n (self-hosted Docker); ffmpeg.

**Read first:** `docs/spec.md` in this repo (the full technical spec). Section references below (e.g. "spec §6") point at it.

**Working directory:** `/Users/tannerkunz/coding/build-commons-pipeline` — all paths below are relative to it unless absolute.

**Environment conventions (apply to every task):**
- Python commands run via `uv run …` from the repo root. Node commands run from `remotion/`.
- No real API keys anywhere. All external calls are behind injectable boundaries and mocked in tests.
- Commit after every task with a conventional-commit message (attribution disabled globally — no Co-Authored-By).

---

### Task 1: Scaffold repo from Tree template

**Files:**
- Create: entire repo from `/Users/tannerkunz/coding/project_template/template/` (rsync)
- Create: `README.md`, `CLAUDE.md`, `AGENTS.md`, `TODO.md`, `.gitignore`, `.env.example`, `.github/workflows/ci.yml` (replace template versions)
- Create: `agents/context.md`, `schemas/context.md`, `remotion/context.md`, `n8n/context.md`, `supabase/context.md`
- Delete: `frontend/`, `backend/`, `data/`, `infra/`, `.github/workflows/deploy-ec2.yml`

- [ ] **Step 1: Copy template and reshape folders**

```bash
cd /Users/tannerkunz/coding
rsync -a --exclude '.git' --exclude '.DS_Store' project_template/template/ build-commons-pipeline/
cd build-commons-pipeline
rm -rf frontend backend data infra .github/workflows/deploy-ec2.yml
mkdir -p agents schemas/fixtures remotion n8n/workflows supabase/migrations tests docs/decisions
```

- [ ] **Step 2: Write README.md** (replace template version wholesale)

````markdown
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
````

- [ ] **Step 3: Write CLAUDE.md and copy to AGENTS.md (must stay byte-identical — CI enforces)**

````markdown
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
````

```bash
cp CLAUDE.md AGENTS.md
```

- [ ] **Step 4: Write TODO.md** (manual/external tasks the code can't do)

```markdown
# TODO

## Now (Week 1 — apply-early items, per spec §10)
- [ ] Apply for TikTok Content Posting API developer app (takes days–weeks)
- [ ] Convert IG to Business/Creator account + create Meta app for Graph API
- [ ] Create ElevenLabs Creator account; clone own voice; save consent recording
- [ ] Create Supabase project; run `supabase/migrations/0001_init.sql`; create `assets` and `renders` storage buckets
- [ ] Set up Google AI Studio key (Nano Banana + Veo 3.1) and Anthropic API key
- [ ] Set monthly budget alert at $120 across providers

## Next
- [ ] Seed taste_library with 50 annotated videos (~3–4 hrs, manual — do not skip; spec §9 Phase 2)
- [ ] Import n8n workflows from n8n/workflows/ and attach credentials
- [ ] Create GitHub repo tanner-k/build-commons-pipeline; push main + dev; enable branch protection
- [ ] First 10 videos through full pipeline; tune prompts/templates (Phase 4)

## Later
- [ ] Tutorial.tsx + Comparison.tsx compositions (Phase 6)
- [ ] Remotion Lambda if >10 videos/week
- [ ] OpusClip once long-form content exists
```

- [ ] **Step 5: Write context.md files**

`schemas/context.md`:
```markdown
# schemas/

Pydantic models — the pipeline contract (spec §6). `video_script.py` is the source of truth; `remotion/src/types/video-script.ts` mirrors it with zod. `fixtures/sample_video_script.json` is validated by BOTH sides (pytest + vitest) — change all three together.
```

`agents/context.md`:
```markdown
# agents/

CrewAI agents (spec §7 Stage 1 + Stage 6). All LLM calls go through `llm.py` (Claude via CrewAI/LiteLLM; model from $ANTHROPIC_MODEL). All DB access through `db.py`. Prompt builders and output parsers are pure functions — tested without network. `pipeline.py` is the Stage-1 CLI; `analyst.py` is the weekly Stage-6 run.
```

`remotion/context.md`:
```markdown
# remotion/

Node/React package: Remotion compositions (1080×1920@30fps + 1280×720 thumbnail still), brand components, and the Express render server (`render-server/`). All Remotion packages must share one exact version. Animations use spring(), never linear. Captions sync from ElevenLabs word timestamps with even-spacing fallback.
```

`supabase/context.md`:
```markdown
# supabase/

SQL migrations, applied manually via Supabase SQL editor or `supabase db push`. Tables: videos (pipeline state machine), analytics, taste_library, templates (spec §5). The `videos.status` CHECK constraint is the single definition of valid statuses.
```

`n8n/context.md`:
```markdown
# n8n/

Workflow JSON exports — import into self-hosted n8n, then attach credentials in the UI (creds never live in these files). Plumbing only: schedule triggers, HTTP calls, Postgres reads/writes. generate.json = Stage 2 asset fan-out + render trigger; publish.json = Stage 5; analytics.json = Stage 6 ingest.
```

- [ ] **Step 6: Write .env.example and .gitignore additions**

`.env.example`:
```bash
# LLM (Stage 1 + analyst)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
# Supabase (state + storage)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
# Asset providers (used by n8n, kept here for local testing)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
GOOGLE_AI_STUDIO_API_KEY=
# Publishing/analytics
YOUTUBE_API_KEY=
# Render server
RENDER_SERVER_PORT=3333
RENDERS_BUCKET=renders
```

Append to `.gitignore` (keep template entries):
```
.env
.venv/
__pycache__/
*.pyc
remotion/node_modules/
remotion/out/
out/
.DS_Store
```

- [ ] **Step 7: Replace `.github/workflows/ci.yml`**

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main, dev]
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { python-version: "3.12" }
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run pytest
  remotion:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: remotion } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: npm, cache-dependency-path: remotion/package-lock.json }
      - run: npm ci
      - run: npm run typecheck
      - run: npm test
  docs-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cmp CLAUDE.md AGENTS.md
```

- [ ] **Step 8: Fill remaining template placeholders**

```bash
grep -rn "__[A-Z_]\+__" . --exclude-dir=node_modules --exclude-dir=.git
```

For any hits (e.g. in `docs/architecture.md`, `docs/decisions/0001-stack.md`, `.lintstagedrc.json`, `.husky/pre-commit`, `scripts/done.py`, `.github/PULL_REQUEST_TEMPLATE.md`), substitute:

| Placeholder | Value |
|---|---|
| `__PROJECT_NAME__` | `build-commons-pipeline` |
| `__PROJECT_DESCRIPTION__` | `Semi-automated short-form video pipeline with closed analytics feedback loop` |
| `__FRONTEND_STACK__` | `Remotion 4 + React 18 + TypeScript (remotion/)` |
| `__BACKEND_STACK__` | `Python 3.12 + uv + CrewAI + Pydantic v2 (agents/, schemas/)` |
| `__DATA_STACK__` | `Supabase Postgres + Storage` |
| `__INFRA_STACK__` | `n8n self-hosted (Docker, Mac mini M4); renders local` |
| `__PACKAGE_MANAGER__` | `npm (remotion/) · uv (python)` |
| `__NODE_VERSION__` | `20` |
| `__INSTALL_CMD__` | `uv sync && cd remotion && npm install` |
| `__DEV_CMD__` | `cd remotion && npm run dev` |
| `__TEST_CMD__` | `uv run pytest && cd remotion && npm test` |
| `__BUILD_CMD__` | `cd remotion && npm run typecheck` |
| `__GITHUB_REPO__` | `tanner-k/build-commons-pipeline` |
| `__INIT_DATE__` | `2026-06-10` |
| `__STACK_RATIONALE__` | `One tool per job (spec §3): Claude for all LLM work, Remotion for all branded rendering, n8n for plumbing only, Supabase for state+storage. Deliberately cut: Canva, Descript, Kling, Ollama-in-pipeline, OpusClip.` |
| any other `__X__` | sensible value from spec §2–4; never leave a placeholder |

Re-run the grep — must return **zero** hits.

- [ ] **Step 9: Verify CLAUDE.md == AGENTS.md and git init + commit**

```bash
cmp CLAUDE.md AGENTS.md   # must output nothing
git init -b main
git add -A
git commit -m "chore: scaffold build-commons-pipeline from Tree template"
```

---

### Task 2: Python bootstrap + VideoScript contract (Pydantic)

**Files:**
- Create: `pyproject.toml`
- Create: `schemas/__init__.py`, `schemas/video_script.py`
- Test: `tests/test_video_script.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "build-commons-pipeline"
version = "0.1.0"
description = "Semi-automated short-form video pipeline with closed analytics feedback loop"
requires-python = ">=3.12"
dependencies = [
    "crewai>=0.86",
    "pydantic>=2.8",
    "supabase>=2.6",
    "httpx>=0.27",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
    "sqlglot>=25.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["agents", "schemas"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Run: `uv sync` — must resolve and install. Create empty `agents/__init__.py` and `schemas/__init__.py` so the build backend finds both packages.

- [ ] **Step 2: Write the failing tests** — `tests/test_video_script.py`

```python
import pytest
from pydantic import ValidationError

from schemas.video_script import Segment, VideoAssets, VideoScript, WordTiming


def make_segment(**overrides) -> Segment:
    base = dict(
        id="seg-1",
        text="Here is one idea explained plainly.",
        visual_type="text_card",
        visual_prompt=None,
        duration_estimate_s=4.0,
        caption_emphasis=["one", "idea"],
    )
    base.update(overrides)
    return Segment(**base)


def make_script(**overrides) -> VideoScript:
    base = dict(
        topic="Using AI to summarize PDFs",
        template="explainer",
        hook=make_segment(id="hook", text="Stop reading 50-page PDFs.", duration_estimate_s=2.5),
        segments=[make_segment(id="seg-1"), make_segment(id="seg-2")],
        cta=make_segment(id="cta", text="Follow for more AI workflows."),
        target_duration_s=45,
        platform_captions={"youtube": "Stop reading PDFs #shorts"},
        hashtags={"youtube": ["#ai", "#shorts"]},
    )
    base.update(overrides)
    return VideoScript(**base)


class TestSegment:
    def test_valid_segment_round_trips(self):
        seg = make_segment()
        assert Segment.model_validate(seg.model_dump()) == seg

    def test_ai_visual_requires_prompt(self):
        with pytest.raises(ValidationError, match="visual_prompt"):
            make_segment(visual_type="ai_broll", visual_prompt=None)

    def test_text_card_needs_no_prompt(self):
        assert make_segment(visual_type="text_card", visual_prompt=None).visual_prompt is None

    def test_duration_must_be_positive(self):
        with pytest.raises(ValidationError):
            make_segment(duration_estimate_s=0)

    def test_unknown_visual_type_rejected(self):
        with pytest.raises(ValidationError):
            make_segment(visual_type="hologram")


class TestVideoScript:
    def test_valid_script_round_trips(self):
        script = make_script()
        assert VideoScript.model_validate_json(script.model_dump_json()) == script

    def test_target_duration_bounds(self):
        with pytest.raises(ValidationError):
            make_script(target_duration_s=20)
        with pytest.raises(ValidationError):
            make_script(target_duration_s=90)

    def test_needs_at_least_one_body_segment(self):
        with pytest.raises(ValidationError):
            make_script(segments=[])

    def test_unknown_template_rejected(self):
        with pytest.raises(ValidationError):
            make_script(template="vlog")

    def test_duplicate_segment_ids_rejected(self):
        with pytest.raises(ValidationError, match="unique"):
            make_script(segments=[make_segment(id="dup"), make_segment(id="dup")])

    def test_all_segments_helper_in_order(self):
        script = make_script()
        assert [s.id for s in script.all_segments()] == ["hook", "seg-1", "seg-2", "cta"]


class TestAssets:
    def test_word_timing_orders(self):
        with pytest.raises(ValidationError):
            WordTiming(word="hi", start_s=2.0, end_s=1.0)

    def test_video_assets_defaults(self):
        assets = VideoAssets()
        assert assets.voiceover == {} and assets.timings == {} and assets.thumbnail_base is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_video_script.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'schemas.video_script'`

- [ ] **Step 4: Write `schemas/video_script.py`**

```python
"""Pipeline contract (spec §6). Source of truth.

Mirror: remotion/src/types/video-script.ts (zod). Shared fixture:
schemas/fixtures/sample_video_script.json is validated by both sides.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

VisualType = Literal["ai_broll", "ai_image", "screen_recording", "text_card"]
TemplateName = Literal["explainer", "tutorial", "listicle", "comparison"]

AI_VISUAL_TYPES: frozenset[str] = frozenset({"ai_broll", "ai_image"})


class Segment(BaseModel):
    """One narrated beat of the video with its visual."""

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    visual_type: VisualType
    visual_prompt: str | None = None
    duration_estimate_s: float = Field(gt=0)
    caption_emphasis: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ai_visuals_need_prompt(self) -> "Segment":
        if self.visual_type in AI_VISUAL_TYPES and not self.visual_prompt:
            raise ValueError(
                f"visual_prompt is required when visual_type={self.visual_type!r}"
            )
        return self


class VideoScript(BaseModel):
    """Everything downstream stages need to produce one video."""

    topic: str = Field(min_length=1)
    template: TemplateName
    hook: Segment
    segments: list[Segment] = Field(min_length=1)
    cta: Segment
    target_duration_s: int = Field(ge=30, le=60)
    platform_captions: dict[str, str]
    hashtags: dict[str, list[str]]

    @model_validator(mode="after")
    def _segment_ids_unique(self) -> "VideoScript":
        ids = [s.id for s in self.all_segments()]
        if len(ids) != len(set(ids)):
            raise ValueError("segment ids must be unique across hook, segments, and cta")
        return self

    def all_segments(self) -> list[Segment]:
        """Hook, body segments, CTA — in playback order."""
        return [self.hook, *self.segments, self.cta]


class WordTiming(BaseModel):
    """One word from ElevenLabs word-level timestamps (caption sync)."""

    word: str
    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _end_after_start(self) -> "WordTiming":
        if self.end_s < self.start_s:
            raise ValueError("end_s must be >= start_s")
        return self


class VideoAssets(BaseModel):
    """Shape of videos.asset_urls jsonb. Keys are segment ids."""

    voiceover: dict[str, str] = Field(default_factory=dict)
    visuals: dict[str, str] = Field(default_factory=dict)
    timings: dict[str, list[WordTiming]] = Field(default_factory=dict)
    thumbnail_base: str | None = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_video_script.py -q` → all PASS. Also `uv run ruff check .` → clean.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock schemas/ agents/__init__.py tests/test_video_script.py
git commit -m "feat(schemas): VideoScript pipeline contract with validation"
```

---

### Task 3: Shared contract fixture (Python side)

**Files:**
- Create: `schemas/fixtures/sample_video_script.json`, `schemas/fixtures/sample_assets.json`
- Test: `tests/test_fixture_contract.py`

- [ ] **Step 1: Write the failing test** — `tests/test_fixture_contract.py`

```python
import json
from pathlib import Path

from schemas.video_script import VideoAssets, VideoScript

FIXTURES = Path(__file__).parent.parent / "schemas" / "fixtures"


def test_sample_script_fixture_is_valid():
    raw = json.loads((FIXTURES / "sample_video_script.json").read_text())
    script = VideoScript.model_validate(raw)
    assert script.template == "explainer"
    assert len(script.segments) == 3
    assert script.hook.duration_estimate_s <= 3.0  # spec: hook lands in 3s


def test_sample_assets_fixture_is_valid():
    raw = json.loads((FIXTURES / "sample_assets.json").read_text())
    assets = VideoAssets.model_validate(raw)
    assert "hook" in assets.timings
    words = assets.timings["hook"]
    assert all(w.end_s >= w.start_s for w in words)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_fixture_contract.py -q` → FAIL (FileNotFoundError)

- [ ] **Step 3: Write `schemas/fixtures/sample_video_script.json`**

```json
{
  "topic": "Use Claude to summarize any PDF in 30 seconds",
  "template": "explainer",
  "hook": {
    "id": "hook",
    "text": "Stop reading 50 page PDFs like it's 2020.",
    "visual_type": "text_card",
    "visual_prompt": null,
    "duration_estimate_s": 2.8,
    "caption_emphasis": ["Stop", "2020"]
  },
  "segments": [
    {
      "id": "seg-1",
      "text": "Drag any PDF into Claude and ask for the five decisions that matter.",
      "visual_type": "screen_recording",
      "visual_prompt": null,
      "duration_estimate_s": 6.0,
      "caption_emphasis": ["five", "decisions"]
    },
    {
      "id": "seg-2",
      "text": "It reads every page so you can skim only what changed.",
      "visual_type": "ai_image",
      "visual_prompt": "Clean isometric illustration of a tall stack of paper documents compressing into a single glowing summary card, dark navy background, warm amber accent light",
      "duration_estimate_s": 5.5,
      "caption_emphasis": ["every", "page"]
    },
    {
      "id": "seg-3",
      "text": "Then paste the summary into your notes and you're done before the meeting starts.",
      "visual_type": "ai_broll",
      "visual_prompt": "Smooth cinematic close-up of hands typing on a laptop in a dim modern office, soft amber desk light, shallow depth of field, 4k",
      "duration_estimate_s": 6.5,
      "caption_emphasis": ["done"]
    }
  ],
  "cta": {
    "id": "cta",
    "text": "Follow Build Commons for one practical AI workflow every day.",
    "visual_type": "text_card",
    "visual_prompt": null,
    "duration_estimate_s": 3.2,
    "caption_emphasis": ["Follow"]
  },
  "target_duration_s": 30,
  "platform_captions": {
    "youtube": "Summarize any PDF in 30 seconds with Claude #shorts",
    "tiktok": "You're still reading PDFs manually?? 💀 #ai #productivity",
    "instagram": "The 30-second PDF workflow nobody showed you."
  },
  "hashtags": {
    "youtube": ["#shorts", "#ai", "#claude", "#productivity"],
    "tiktok": ["#ai", "#aitools", "#productivityhacks", "#claude"],
    "instagram": ["#aitools", "#productivity", "#workflow"]
  }
}
```

- [ ] **Step 4: Write `schemas/fixtures/sample_assets.json`**

(Word timings for the hook only — enough to exercise caption sync; other segments use the even-spacing fallback. URLs are Supabase-style paths, not live.)

```json
{
  "voiceover": {
    "hook": "https://example.supabase.co/storage/v1/object/public/assets/demo/hook.mp3"
  },
  "visuals": {
    "seg-2": "https://example.supabase.co/storage/v1/object/public/assets/demo/seg-2.png",
    "seg-3": "https://example.supabase.co/storage/v1/object/public/assets/demo/seg-3.mp4"
  },
  "timings": {
    "hook": [
      { "word": "Stop", "start_s": 0.0, "end_s": 0.38 },
      { "word": "reading", "start_s": 0.38, "end_s": 0.74 },
      { "word": "50", "start_s": 0.74, "end_s": 1.02 },
      { "word": "page", "start_s": 1.02, "end_s": 1.3 },
      { "word": "PDFs", "start_s": 1.3, "end_s": 1.72 },
      { "word": "like", "start_s": 1.72, "end_s": 1.9 },
      { "word": "it's", "start_s": 1.9, "end_s": 2.08 },
      { "word": "2020.", "start_s": 2.08, "end_s": 2.6 }
    ]
  },
  "thumbnail_base": "https://example.supabase.co/storage/v1/object/public/assets/demo/thumb-base.png"
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_fixture_contract.py -q` → PASS

- [ ] **Step 6: Commit**

```bash
git add schemas/fixtures/ tests/test_fixture_contract.py
git commit -m "feat(schemas): shared contract fixtures for cross-language validation"
```

---

### Task 4: Supabase migration

**Files:**
- Create: `supabase/migrations/0001_init.sql`
- Test: `tests/test_migrations.py`

- [ ] **Step 1: Write the failing test** — `tests/test_migrations.py`

```python
from pathlib import Path

import sqlglot
from sqlglot import expressions as exp

MIGRATION = Path(__file__).parent.parent / "supabase" / "migrations" / "0001_init.sql"


def parsed_statements():
    return sqlglot.parse(MIGRATION.read_text(), read="postgres")


def created_tables() -> set[str]:
    return {
        stmt.find(exp.Table).name
        for stmt in parsed_statements()
        if isinstance(stmt, exp.Create) and stmt.kind == "TABLE"
    }


def test_migration_parses_as_postgres():
    assert len(parsed_statements()) > 0


def test_all_spec_tables_created():
    assert created_tables() == {"videos", "analytics", "taste_library", "templates"}


def test_videos_status_constraint_lists_all_pipeline_states():
    sql = MIGRATION.read_text()
    for status in (
        "ideation", "scripted", "assets_ready", "rendered",
        "qa_pending", "approved", "rejected", "published",
    ):
        assert f"'{status}'" in sql, f"missing status {status} in CHECK constraint"


def test_templates_seeded():
    sql = MIGRATION.read_text().lower()
    assert "insert into templates" in sql
    for name in ("explainer", "tutorial", "listicle", "comparison"):
        assert name in sql
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_migrations.py -q` → FAIL (FileNotFoundError)

- [ ] **Step 3: Write `supabase/migrations/0001_init.sql`**

```sql
-- 0001_init.sql — pipeline state, analytics, taste library, templates (spec §5)
-- Apply via Supabase SQL editor or `supabase db push`.

create extension if not exists "pgcrypto";

create table if not exists videos (
    id uuid primary key default gen_random_uuid(),
    status text not null default 'ideation'
        check (status in (
            'ideation', 'scripted', 'assets_ready', 'rendered',
            'qa_pending', 'approved', 'rejected', 'published'
        )),
    template text
        check (template in ('explainer', 'tutorial', 'listicle', 'comparison')),
    topic text,
    hook text,
    script_json jsonb,
    asset_urls jsonb,
    render_url text,
    platform_ids jsonb,          -- {"youtube": "...", "tiktok": "...", "instagram": "..."}
    qa_notes text,               -- rejection notes feed Stage 2/3 retry
    created_at timestamptz not null default now(),
    published_at timestamptz
);

create index if not exists videos_status_idx on videos (status);

create table if not exists analytics (
    id bigint generated always as identity primary key,
    video_id uuid not null references videos (id) on delete cascade,
    platform text not null
        check (platform in ('youtube', 'tiktok', 'instagram')),
    captured_at timestamptz not null default now(),
    views int,
    avg_view_duration_s double precision,
    retention_curve jsonb,       -- [{"t_s": 0.0, "fraction": 1.0}, ...]
    ctr double precision,
    likes int,
    shares int,
    follows_attributed int
);

create index if not exists analytics_video_idx on analytics (video_id, platform, captured_at);

create table if not exists taste_library (
    id uuid primary key default gen_random_uuid(),
    source_url text,
    niche text,
    transcript text,
    hook_text text,
    hook_type text
        check (hook_type in ('question', 'bold_claim', 'curiosity_gap', 'demo')),
    why_it_works text,
    views bigint,
    added_by text not null default 'manual'
        check (added_by in ('manual', 'analyst_agent')),
    created_at timestamptz not null default now()
);

create table if not exists templates (
    name text primary key,
    version int not null default 1,
    created_at timestamptz not null default now(),
    retired_at timestamptz,
    avg_retention double precision   -- updated by analyst agent
);

insert into templates (name)
values ('explainer'), ('tutorial'), ('listicle'), ('comparison')
on conflict (name) do nothing;
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_migrations.py -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add supabase/ tests/test_migrations.py
git commit -m "feat(supabase): initial schema — videos, analytics, taste_library, templates"
```

---

### Task 5: Remotion bootstrap + TS contract mirror (zod)

**Files:**
- Create: `remotion/package.json`, `remotion/tsconfig.json`, `remotion/remotion.config.ts`, `remotion/vitest.config.ts`
- Create: `remotion/src/types/video-script.ts`
- Create: `remotion/src/index.ts`, `remotion/src/Root.tsx` (minimal — comps registered in Task 8)
- Test: `remotion/src/types/video-script.test.ts`

- [ ] **Step 1: Write `remotion/package.json`**

```json
{
  "name": "build-commons-remotion",
  "private": true,
  "scripts": {
    "dev": "remotion studio",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "serve": "tsx render-server/src/index.ts",
    "render:explainer": "remotion render Explainer out/explainer.mp4",
    "render:listicle": "remotion render Listicle out/listicle.mp4",
    "render:thumbnail": "remotion still Thumbnail out/thumbnail.png"
  },
  "dependencies": {
    "@remotion/bundler": "4.0.245",
    "@remotion/cli": "4.0.245",
    "@remotion/google-fonts": "4.0.245",
    "@remotion/renderer": "4.0.245",
    "@supabase/supabase-js": "^2.45.0",
    "express": "^4.21.0",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "remotion": "4.0.245",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^20.14.0",
    "@types/react": "18.3.3",
    "@types/supertest": "^6.0.2",
    "supertest": "^7.0.0",
    "tsx": "^4.16.0",
    "typescript": "5.5.4",
    "vitest": "^2.1.0"
  }
}
```

Note: if `npm install` reports a newer 4.0.x as latest, you MAY bump — but every `remotion`/`@remotion/*` package must be the **identical** version.

`remotion/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "lib": ["DOM", "ES2022"],
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src", "render-server/src", "remotion.config.ts"]
}
```

`remotion/remotion.config.ts`:
```ts
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
```

`remotion/vitest.config.ts`:
```ts
import {defineConfig} from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'render-server/**/*.test.ts'],
  },
});
```

Run: `cd remotion && npm install` — must succeed and produce `package-lock.json`.

- [ ] **Step 2: Write the failing contract test** — `remotion/src/types/video-script.test.ts`

```ts
import {describe, expect, it} from 'vitest';
import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from './video-script';

describe('contract mirror', () => {
  it('validates the shared script fixture (same file pytest validates)', () => {
    const script = videoScriptSchema.parse(sampleScript);
    expect(script.template).toBe('explainer');
    expect(script.segments).toHaveLength(3);
  });

  it('validates the shared assets fixture', () => {
    const assets = videoAssetsSchema.parse(sampleAssets);
    expect(assets.timings['hook']!.length).toBeGreaterThan(0);
  });

  it('rejects ai visuals without a prompt', () => {
    const bad = {
      id: 'x', text: 'x', visual_type: 'ai_broll', visual_prompt: null,
      duration_estimate_s: 3, caption_emphasis: [],
    };
    expect(() => videoScriptSchema.parse({...sampleScript, hook: bad})).toThrow(/visual_prompt/);
  });

  it('rejects out-of-range target duration', () => {
    expect(() => videoScriptSchema.parse({...sampleScript, target_duration_s: 20})).toThrow();
  });
});
```

(JSON imports, not `readFileSync` + `__dirname` — `__dirname` is undefined under vitest's ESM transform; `resolveJsonModule` is enabled in tsconfig.)

- [ ] **Step 3: Run to verify it fails**

Run: `cd remotion && npx vitest run src/types/video-script.test.ts`
Expected: FAIL — cannot resolve `./video-script`

- [ ] **Step 4: Write `remotion/src/types/video-script.ts`**

```ts
/**
 * Mirror of schemas/video_script.py (the source of truth — spec §6).
 * Change Python first, then this file, then the shared fixtures.
 */
import {z} from 'zod';

export const AI_VISUAL_TYPES = ['ai_broll', 'ai_image'] as const;

export const segmentSchema = z
  .object({
    id: z.string().min(1),
    text: z.string().min(1),
    visual_type: z.enum(['ai_broll', 'ai_image', 'screen_recording', 'text_card']),
    visual_prompt: z.string().nullable(),
    duration_estimate_s: z.number().positive(),
    caption_emphasis: z.array(z.string()),
  })
  .refine(
    (s) => !(AI_VISUAL_TYPES as readonly string[]).includes(s.visual_type) || !!s.visual_prompt,
    {message: 'visual_prompt is required for ai_broll/ai_image segments', path: ['visual_prompt']},
  );

export const videoScriptSchema = z
  .object({
    topic: z.string().min(1),
    template: z.enum(['explainer', 'tutorial', 'listicle', 'comparison']),
    hook: segmentSchema,
    segments: z.array(segmentSchema).min(1),
    cta: segmentSchema,
    target_duration_s: z.number().int().min(30).max(60),
    platform_captions: z.record(z.string()),
    hashtags: z.record(z.array(z.string())),
  })
  .refine(
    (s) => {
      const ids = [s.hook.id, ...s.segments.map((x) => x.id), s.cta.id];
      return new Set(ids).size === ids.length;
    },
    {message: 'segment ids must be unique across hook, segments, and cta'},
  );

export const wordTimingSchema = z
  .object({
    word: z.string(),
    start_s: z.number().min(0),
    end_s: z.number(),
  })
  .refine((w) => w.end_s >= w.start_s, {message: 'end_s must be >= start_s'});

export const videoAssetsSchema = z.object({
  voiceover: z.record(z.string()).default({}),
  visuals: z.record(z.string()).default({}),
  timings: z.record(z.array(wordTimingSchema)).default({}),
  thumbnail_base: z.string().nullable().default(null),
});

export type Segment = z.infer<typeof segmentSchema>;
export type VideoScript = z.infer<typeof videoScriptSchema>;
export type WordTiming = z.infer<typeof wordTimingSchema>;
export type VideoAssets = z.infer<typeof videoAssetsSchema>;

/** Hook, body segments, CTA — in playback order. */
export const allSegments = (script: VideoScript): Segment[] => [
  script.hook,
  ...script.segments,
  script.cta,
];
```

- [ ] **Step 5: Minimal Root so the package typechecks** — `remotion/src/index.ts` and `remotion/src/Root.tsx`

`remotion/src/index.ts`:
```ts
import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
```

`remotion/src/Root.tsx` (compositions are added in Tasks 8–9):
```tsx
import React from 'react';

export const Root: React.FC = () => {
  return <></>;
};
```

- [ ] **Step 6: Run tests + typecheck to verify they pass**

Run: `cd remotion && npx vitest run && npm run typecheck` → PASS / clean

- [ ] **Step 7: Commit**

```bash
git add remotion/
git commit -m "feat(remotion): bootstrap package with zod contract mirror + shared-fixture test"
```

---

### Task 6: Timeline & caption-timing library

**Files:**
- Create: `remotion/src/lib/timing.ts`
- Test: `remotion/src/lib/timing.test.ts`

This is the core sync logic: segment windows on the frame timeline, word-level caption timing from ElevenLabs timestamps, and an even-spacing fallback when timings are missing.

- [ ] **Step 1: Write the failing tests** — `remotion/src/lib/timing.test.ts`

```ts
import {describe, expect, it} from 'vitest';
import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from '../types/video-script';
import {
  activeWordIndex,
  buildTimeline,
  fallbackTimings,
  segmentDurationS,
  totalDurationInFrames,
} from './timing';

const script = videoScriptSchema.parse(sampleScript);
const assets = videoAssetsSchema.parse(sampleAssets);
const FPS = 30;

describe('segmentDurationS', () => {
  it('uses last word end when timings exist', () => {
    expect(segmentDurationS(script.hook, assets)).toBeCloseTo(2.6);
  });
  it('falls back to duration_estimate_s without timings', () => {
    expect(segmentDurationS(script.segments[0]!, assets)).toBeCloseTo(6.0);
  });
});

describe('buildTimeline', () => {
  it('covers hook + body + cta in order, contiguous from frame 0', () => {
    const tl = buildTimeline(script, assets, FPS);
    expect(tl.map((w) => w.segmentId)).toEqual(['hook', 'seg-1', 'seg-2', 'seg-3', 'cta']);
    expect(tl[0]!.from).toBe(0);
    for (let i = 1; i < tl.length; i++) {
      expect(tl[i]!.from).toBe(tl[i - 1]!.from + tl[i - 1]!.durationInFrames);
    }
  });
  it('every window has at least 1 frame', () => {
    for (const w of buildTimeline(script, assets, FPS)) {
      expect(w.durationInFrames).toBeGreaterThan(0);
    }
  });
});

describe('totalDurationInFrames', () => {
  it('equals the sum of all windows', () => {
    const tl = buildTimeline(script, assets, FPS);
    const sum = tl.reduce((acc, w) => acc + w.durationInFrames, 0);
    expect(totalDurationInFrames(script, assets, FPS)).toBe(sum);
  });
});

describe('fallbackTimings', () => {
  it('spreads words evenly across the duration', () => {
    const words = fallbackTimings('one two three four', 4);
    expect(words).toHaveLength(4);
    expect(words[0]).toEqual({word: 'one', start_s: 0, end_s: 1});
    expect(words[3]!.end_s).toBeCloseTo(4);
  });
  it('handles single-word text', () => {
    expect(fallbackTimings('hello', 2)).toEqual([{word: 'hello', start_s: 0, end_s: 2}]);
  });
});

describe('activeWordIndex', () => {
  const words = fallbackTimings('a b c d', 4); // 1s per word
  it('returns the word containing t', () => {
    expect(activeWordIndex(words, 0.5)).toBe(0);
    expect(activeWordIndex(words, 2.5)).toBe(2);
  });
  it('clamps before start and after end', () => {
    expect(activeWordIndex(words, -1)).toBe(0);
    expect(activeWordIndex(words, 99)).toBe(3);
  });
  it('returns -1 for empty word list', () => {
    expect(activeWordIndex([], 1)).toBe(-1);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd remotion && npx vitest run src/lib/timing.test.ts` → FAIL (module not found)

- [ ] **Step 3: Write `remotion/src/lib/timing.ts`**

```ts
import type {Segment, VideoAssets, VideoScript, WordTiming} from '../types/video-script';
import {allSegments} from '../types/video-script';

export type SegmentWindow = {
  segmentId: string;
  from: number;
  durationInFrames: number;
};

/** Real duration: last word end from ElevenLabs timings, else the script estimate. */
export const segmentDurationS = (segment: Segment, assets: VideoAssets): number => {
  const words = assets.timings[segment.id];
  if (words && words.length > 0) {
    return words[words.length - 1]!.end_s;
  }
  return segment.duration_estimate_s;
};

/** Contiguous frame windows for hook → segments → cta, starting at frame 0. */
export const buildTimeline = (
  script: VideoScript,
  assets: VideoAssets,
  fps: number,
): SegmentWindow[] => {
  const windows: SegmentWindow[] = [];
  let cursor = 0;
  for (const segment of allSegments(script)) {
    const durationInFrames = Math.max(1, Math.round(segmentDurationS(segment, assets) * fps));
    windows.push({segmentId: segment.id, from: cursor, durationInFrames});
    cursor += durationInFrames;
  }
  return windows;
};

export const totalDurationInFrames = (
  script: VideoScript,
  assets: VideoAssets,
  fps: number,
): number =>
  buildTimeline(script, assets, fps).reduce((acc, w) => acc + w.durationInFrames, 0);

/** Even-spacing caption fallback when ElevenLabs timings are missing. */
export const fallbackTimings = (text: string, durationS: number): WordTiming[] => {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const per = durationS / words.length;
  return words.map((word, i) => ({word, start_s: i * per, end_s: (i + 1) * per}));
};

/** Index of the word being spoken at t seconds into the segment; -1 if no words. */
export const activeWordIndex = (words: WordTiming[], tS: number): number => {
  if (words.length === 0) return -1;
  if (tS < words[0]!.start_s) return 0;
  for (let i = 0; i < words.length; i++) {
    if (tS < words[i]!.end_s) return i;
  }
  return words.length - 1;
};

/** Words for a segment: real timings if present, else even-spacing fallback. */
export const wordsForSegment = (segment: Segment, assets: VideoAssets): WordTiming[] => {
  const words = assets.timings[segment.id];
  if (words && words.length > 0) return words;
  return fallbackTimings(segment.text, segmentDurationS(segment, assets));
};
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd remotion && npx vitest run && npm run typecheck` → PASS

- [ ] **Step 5: Commit**

```bash
git add remotion/src/lib/
git commit -m "feat(remotion): segment timeline + word-sync caption timing with fallback"
```

---

### Task 7: Brand theme + shared components

**Files:**
- Create: `remotion/src/lib/theme.ts`
- Create: `remotion/src/components/BrandFrame.tsx`, `remotion/src/components/ProgressBar.tsx`, `remotion/src/components/Captions.tsx`, `remotion/src/components/SegmentVisual.tsx`
- Test: `remotion/src/lib/theme.test.ts` (emphasis matching — the only pure logic here)

Spec §7 Stage 3 requirements: word-synced captions, `spring()` animations (never linear), brand frame, progress bar.

- [ ] **Step 1: Write the failing test** — `remotion/src/lib/theme.test.ts`

```ts
import {describe, expect, it} from 'vitest';
import {isEmphasized} from './theme';

describe('isEmphasized', () => {
  it('matches case-insensitively ignoring punctuation', () => {
    expect(isEmphasized('Stop,', ['stop'])).toBe(true);
    expect(isEmphasized('2020.', ['2020'])).toBe(true);
    expect(isEmphasized('reading', ['stop'])).toBe(false);
  });
  it('handles empty emphasis list', () => {
    expect(isEmphasized('word', [])).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd remotion && npx vitest run src/lib/theme.test.ts` → FAIL

- [ ] **Step 3: Write `remotion/src/lib/theme.ts`**

```ts
import {loadFont} from '@remotion/google-fonts/Inter';

const {fontFamily} = loadFont();

export const BRAND = {
  name: 'BUILD COMMONS',
  bg: '#0B1220',
  surface: '#141E33',
  text: '#F4F6FB',
  muted: '#8A94A8',
  accent: '#FFB224',
  fontFamily,
  framePadding: 48,
} as const;

export const FPS = 30;
export const VIDEO_WIDTH = 1080;
export const VIDEO_HEIGHT = 1920;
export const THUMB_WIDTH = 1280;
export const THUMB_HEIGHT = 720;

const normalize = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

/** Should this caption word get the accent highlight? */
export const isEmphasized = (word: string, emphasis: string[]): boolean =>
  emphasis.some((e) => normalize(e) === normalize(word));
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd remotion && npx vitest run src/lib/theme.test.ts` → PASS

- [ ] **Step 5: Write the components** (no unit tests — exercised by Task 8's smoke render)

`remotion/src/components/BrandFrame.tsx`:
```tsx
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {BRAND} from '../lib/theme';

export const BrandFrame: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{backgroundColor: BRAND.bg, fontFamily: BRAND.fontFamily}}>
    {children}
    <div
      style={{
        position: 'absolute',
        bottom: 36,
        left: 0,
        right: 0,
        textAlign: 'center',
        color: BRAND.muted,
        fontSize: 28,
        fontWeight: 700,
        letterSpacing: '0.25em',
      }}
    >
      {BRAND.name}
    </div>
  </AbsoluteFill>
);
```

`remotion/src/components/ProgressBar.tsx`:
```tsx
import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';

export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames, fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 200}});
  const progress = interpolate(frame, [0, durationInFrames - 1], [0, 1], {
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        height: 12,
        width: `${progress * 100}%`,
        backgroundColor: BRAND.accent,
        transform: `scaleY(${entrance})`,
        transformOrigin: 'top',
      }}
    />
  );
};
```

`remotion/src/components/Captions.tsx` (word-synced; active word pops with spring; emphasis words get accent color):
```tsx
import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {activeWordIndex} from '../lib/timing';
import {BRAND, isEmphasized} from '../lib/theme';
import type {Segment, WordTiming} from '../types/video-script';

const GROUP_SIZE = 4;

export const Captions: React.FC<{segment: Segment; words: WordTiming[]}> = ({
  segment,
  words,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const tS = frame / fps;
  const active = activeWordIndex(words, tS);
  if (active === -1) return null;

  const groupStart = Math.floor(active / GROUP_SIZE) * GROUP_SIZE;
  const group = words.slice(groupStart, groupStart + GROUP_SIZE);
  const groupStartFrame = Math.round(group[0]!.start_s * fps);
  const pop = spring({frame: frame - groupStartFrame, fps, config: {damping: 12, mass: 0.5}});

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 320,
        left: BRAND.framePadding,
        right: BRAND.framePadding,
        textAlign: 'center',
        transform: `scale(${0.9 + 0.1 * pop})`,
      }}
    >
      {group.map((w, i) => {
        const idx = groupStart + i;
        const isActive = idx === active;
        const emphasized = isEmphasized(w.word, segment.caption_emphasis);
        return (
          <span
            key={`${idx}-${w.word}`}
            style={{
              fontSize: 64,
              fontWeight: 800,
              lineHeight: 1.3,
              margin: '0 10px',
              color: emphasized ? BRAND.accent : BRAND.text,
              opacity: isActive ? 1 : 0.65,
              textShadow: '0 4px 24px rgba(0,0,0,0.6)',
            }}
          >
            {w.word}
          </span>
        );
      })}
    </div>
  );
};
```

`remotion/src/components/SegmentVisual.tsx` (renders by visual_type; text cards show segment text large; missing URLs degrade to a text card, never crash):
```tsx
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import type {Segment, VideoAssets} from '../types/video-script';

const TextCard: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 14}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', padding: BRAND.framePadding * 2}}>
      <div
        style={{
          color: BRAND.text,
          fontSize: 88,
          fontWeight: 800,
          lineHeight: 1.15,
          textAlign: 'center',
          opacity: enter,
          transform: `translateY(${(1 - enter) * 60}px)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

export const SegmentVisual: React.FC<{segment: Segment; assets: VideoAssets}> = ({
  segment,
  assets,
}) => {
  const url = assets.visuals[segment.id];
  if (segment.visual_type === 'text_card' || !url) {
    return <TextCard text={segment.text} />;
  }
  if (segment.visual_type === 'ai_broll') {
    return (
      <AbsoluteFill>
        <OffthreadVideo src={url} style={{width: '100%', height: '100%', objectFit: 'cover'}} muted />
      </AbsoluteFill>
    );
  }
  // ai_image and screen_recording stills/uploads render as images
  return (
    <AbsoluteFill>
      <Img src={url} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 6: Typecheck + full test run**

Run: `cd remotion && npm run typecheck && npx vitest run` → clean / PASS

- [ ] **Step 7: Commit**

```bash
git add remotion/src/lib/theme.ts remotion/src/lib/theme.test.ts remotion/src/components/
git commit -m "feat(remotion): brand theme + caption, progress, frame, visual components"
```

---

### Task 8: Explainer + Listicle compositions, Root registration, smoke render

**Files:**
- Create: `remotion/src/compositions/VideoBody.tsx` (shared sequence logic)
- Create: `remotion/src/compositions/Explainer.tsx`, `remotion/src/compositions/Listicle.tsx`
- Modify: `remotion/src/Root.tsx`
- Create: `remotion/src/lib/fixtures.ts` (loads shared fixtures as defaultProps)

- [ ] **Step 1: Write `remotion/src/lib/fixtures.ts`**

```ts
import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from '../types/video-script';

export const SAMPLE_SCRIPT = videoScriptSchema.parse(sampleScript);
export const SAMPLE_ASSETS = videoAssetsSchema.parse(sampleAssets);
```

Note: `resolveJsonModule` is already on in tsconfig. The demo asset URLs in the fixture are not live — `SegmentVisual` degrades to text cards for missing/unreachable visuals only when the URL is absent; for the smoke render below, strip the fake URLs (see Step 4).

- [ ] **Step 2: Write `remotion/src/compositions/VideoBody.tsx`**

```tsx
import React from 'react';
import {Audio, Sequence} from 'remotion';
import {BrandFrame} from '../components/BrandFrame';
import {Captions} from '../components/Captions';
import {ProgressBar} from '../components/ProgressBar';
import {SegmentVisual} from '../components/SegmentVisual';
import {FPS} from '../lib/theme';
import {buildTimeline, wordsForSegment} from '../lib/timing';
import {allSegments, type VideoAssets, type VideoScript} from '../types/video-script';

export type VideoProps = {script: VideoScript; assets: VideoAssets};

/** Shared hook→segments→cta sequencing; templates wrap this with their own chrome. */
export const VideoBody: React.FC<
  VideoProps & {renderBadge?: (bodyIndex: number) => React.ReactNode}
> = ({script, assets, renderBadge}) => {
  const timeline = buildTimeline(script, assets, FPS);
  const segments = allSegments(script);
  const bodyIds = new Set(script.segments.map((s) => s.id));
  let bodyIndex = 0;

  return (
    <BrandFrame>
      {segments.map((segment, i) => {
        const window = timeline[i]!;
        const voice = assets.voiceover[segment.id];
        const badgeIndex = bodyIds.has(segment.id) ? bodyIndex++ : -1;
        return (
          <Sequence
            key={segment.id}
            from={window.from}
            durationInFrames={window.durationInFrames}
            name={segment.id}
          >
            <SegmentVisual segment={segment} assets={assets} />
            {voice ? <Audio src={voice} /> : null}
            <Captions segment={segment} words={wordsForSegment(segment, assets)} />
            {badgeIndex >= 0 && renderBadge ? renderBadge(badgeIndex) : null}
          </Sequence>
        );
      })}
      <ProgressBar />
    </BrandFrame>
  );
};
```

- [ ] **Step 3: Write the two compositions**

`remotion/src/compositions/Explainer.tsx`:
```tsx
import React from 'react';
import {VideoBody, type VideoProps} from './VideoBody';

export const Explainer: React.FC<VideoProps> = (props) => <VideoBody {...props} />;
```

`remotion/src/compositions/Listicle.tsx` (numbered badge per body segment, spring entrance):
```tsx
import React from 'react';
import {spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND} from '../lib/theme';
import {VideoBody, type VideoProps} from './VideoBody';

const NumberBadge: React.FC<{n: number}> = ({n}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 10, mass: 0.6}});
  return (
    <div
      style={{
        position: 'absolute',
        top: 96,
        left: BRAND.framePadding,
        width: 120,
        height: 120,
        borderRadius: 60,
        backgroundColor: BRAND.accent,
        color: BRAND.bg,
        fontSize: 64,
        fontWeight: 800,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `scale(${enter})`,
      }}
    >
      {n}
    </div>
  );
};

export const Listicle: React.FC<VideoProps> = (props) => (
  <VideoBody {...props} renderBadge={(i) => <NumberBadge n={i + 1} />} />
);
```

- [ ] **Step 4: Register compositions in `remotion/src/Root.tsx`** (replace the placeholder)

```tsx
import React from 'react';
import {Composition, Still} from 'remotion';
import {Explainer} from './compositions/Explainer';
import {Listicle} from './compositions/Listicle';
import {SAMPLE_ASSETS, SAMPLE_SCRIPT} from './lib/fixtures';
import {totalDurationInFrames} from './lib/timing';
import {FPS, VIDEO_HEIGHT, VIDEO_WIDTH} from './lib/theme';
import type {VideoProps} from './compositions/VideoBody';

// Preview props: fixture script, but strip non-live demo URLs so Studio/smoke
// renders don't try to fetch example.supabase.co. Real props come from the
// render server with live Supabase URLs.
const previewProps: VideoProps = {
  script: SAMPLE_SCRIPT,
  assets: {...SAMPLE_ASSETS, voiceover: {}, visuals: {}, thumbnail_base: null},
};

const calculateMetadata = ({props}: {props: VideoProps}) => ({
  durationInFrames: totalDurationInFrames(props.script, props.assets, FPS),
});

export const Root: React.FC = () => (
  <>
    <Composition
      id="Explainer"
      component={Explainer}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={30 * FPS}
      defaultProps={previewProps}
      calculateMetadata={calculateMetadata}
    />
    <Composition
      id="Listicle"
      component={Listicle}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
      fps={FPS}
      durationInFrames={30 * FPS}
      defaultProps={previewProps}
      calculateMetadata={calculateMetadata}
    />
  </>
);
```

(`Still` import is used in Task 9 — if the linter complains now, add it in Task 9 instead.)

- [ ] **Step 5: Typecheck + smoke render 2 seconds of each comp**

```bash
cd remotion && npm run typecheck
npx remotion render Explainer out/smoke-explainer.mp4 --frames=0-59
npx remotion render Listicle out/smoke-listicle.mp4 --frames=0-59
```

Expected: both commands exit 0 and produce playable MP4s. This is the verification that compositions actually render — do not skip.

- [ ] **Step 6: Run full test suite**

Run: `cd remotion && npx vitest run` → PASS

- [ ] **Step 7: Commit**

```bash
git add remotion/src/
git commit -m "feat(remotion): Explainer + Listicle compositions with word-synced captions"
```

---

### Task 9: Thumbnail composition

**Files:**
- Create: `remotion/src/compositions/Thumbnail.tsx`
- Modify: `remotion/src/Root.tsx` (register Still)

Spec §7 Stage 3: Nano Banana base + headline → branded 1280×720 PNG, rendered in the same job as the video.

- [ ] **Step 1: Write `remotion/src/compositions/Thumbnail.tsx`**

```tsx
import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {BRAND} from '../lib/theme';

export type ThumbnailProps = {
  headline: string;
  baseImageUrl: string | null;
};

export const Thumbnail: React.FC<ThumbnailProps> = ({headline, baseImageUrl}) => (
  <AbsoluteFill style={{backgroundColor: BRAND.bg, fontFamily: BRAND.fontFamily}}>
    {baseImageUrl ? (
      <Img
        src={baseImageUrl}
        style={{width: '100%', height: '100%', objectFit: 'cover', opacity: 0.55}}
      />
    ) : null}
    <AbsoluteFill style={{justifyContent: 'flex-end', padding: 64}}>
      <div
        style={{
          color: BRAND.text,
          fontSize: 96,
          fontWeight: 800,
          lineHeight: 1.05,
          textShadow: '0 6px 32px rgba(0,0,0,0.8)',
          maxWidth: '85%',
        }}
      >
        {headline}
      </div>
      <div
        style={{
          marginTop: 28,
          color: BRAND.accent,
          fontSize: 32,
          fontWeight: 700,
          letterSpacing: '0.25em',
        }}
      >
        {BRAND.name}
      </div>
    </AbsoluteFill>
  </AbsoluteFill>
);
```

- [ ] **Step 2: Register in Root.tsx** — add inside the fragment in `remotion/src/Root.tsx`:

```tsx
    <Still
      id="Thumbnail"
      component={Thumbnail}
      width={THUMB_WIDTH}
      height={THUMB_HEIGHT}
      defaultProps={{headline: SAMPLE_SCRIPT.topic, baseImageUrl: null}}
    />
```

with imports updated:
```tsx
import {Thumbnail} from './compositions/Thumbnail';
import {FPS, THUMB_HEIGHT, THUMB_WIDTH, VIDEO_HEIGHT, VIDEO_WIDTH} from './lib/theme';
```

- [ ] **Step 3: Smoke render the still**

```bash
cd remotion && npm run typecheck && npx remotion still Thumbnail out/smoke-thumb.png
```

Expected: exit 0, `out/smoke-thumb.png` exists (1280×720).

- [ ] **Step 4: Commit**

```bash
git add remotion/src/
git commit -m "feat(remotion): branded Thumbnail still composition"
```

---

### Task 10: Render server (Express)

**Files:**
- Create: `remotion/render-server/src/config.ts`, `remotion/render-server/src/supabase.ts`, `remotion/render-server/src/render.ts`, `remotion/render-server/src/app.ts`, `remotion/render-server/src/index.ts`
- Test: `remotion/render-server/src/app.test.ts`

Contract (spec §7 Stage 3): `POST /render {video_id}` → load row (must be `assets_ready`), render MP4 (comp picked by `template`) + thumbnail PNG in one job, ffmpeg-compress (`-crf 28 -preset slow`), upload both to Supabase Storage, set `render_url`, status → `qa_pending`. The Express layer is tested with the render/supabase boundaries mocked; the real render path is exercised manually at the end.

- [ ] **Step 1: Write the failing tests** — `remotion/render-server/src/app.test.ts`

```ts
import request from 'supertest';
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchVideo: vi.fn(),
  updateVideo: vi.fn(),
  renderVideoJob: vi.fn(),
}));

vi.mock('./supabase', () => ({
  fetchVideo: mocks.fetchVideo,
  updateVideo: mocks.updateVideo,
}));
vi.mock('./render', () => ({
  renderVideoJob: mocks.renderVideoJob,
}));

import {createApp} from './app';

const app = createApp();

const assetsReadyRow = {
  id: 'vid-1',
  status: 'assets_ready',
  template: 'explainer',
  topic: 'Topic',
  script_json: {},
  asset_urls: {},
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe('GET /healthz', () => {
  it('returns ok', async () => {
    const res = await request(app).get('/healthz');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ok: true});
  });
});

describe('POST /render', () => {
  it('400 when video_id missing', async () => {
    const res = await request(app).post('/render').send({});
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/video_id/);
  });

  it('404 when video not found', async () => {
    mocks.fetchVideo.mockResolvedValue(null);
    const res = await request(app).post('/render').send({video_id: 'nope'});
    expect(res.status).toBe(404);
  });

  it('409 when video is not assets_ready', async () => {
    mocks.fetchVideo.mockResolvedValue({...assetsReadyRow, status: 'scripted'});
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(409);
    expect(res.body.error).toMatch(/assets_ready/);
  });

  it('renders, updates row to qa_pending, returns urls', async () => {
    mocks.fetchVideo.mockResolvedValue(assetsReadyRow);
    mocks.renderVideoJob.mockResolvedValue({
      renderUrl: 'https://x/renders/vid-1.mp4',
      thumbnailUrl: 'https://x/renders/vid-1.png',
    });
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      ok: true,
      render_url: 'https://x/renders/vid-1.mp4',
      thumbnail_url: 'https://x/renders/vid-1.png',
    });
    expect(mocks.updateVideo).toHaveBeenCalledWith('vid-1', {
      status: 'qa_pending',
      render_url: 'https://x/renders/vid-1.mp4',
    });
  });

  it('500 + row untouched when render fails', async () => {
    mocks.fetchVideo.mockResolvedValue(assetsReadyRow);
    mocks.renderVideoJob.mockRejectedValue(new Error('chromium crashed'));
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(500);
    expect(mocks.updateVideo).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd remotion && npx vitest run render-server` → FAIL (modules not found)

- [ ] **Step 3: Write `config.ts` and `supabase.ts`**

`remotion/render-server/src/config.ts`:
```ts
const required = (name: string): string => {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
};

export const config = {
  port: Number(process.env.RENDER_SERVER_PORT ?? 3333),
  rendersBucket: process.env.RENDERS_BUCKET ?? 'renders',
  // Lazy so tests never need real credentials.
  supabaseUrl: () => required('SUPABASE_URL'),
  supabaseServiceRoleKey: () => required('SUPABASE_SERVICE_ROLE_KEY'),
};
```

`remotion/render-server/src/supabase.ts`:
```ts
import {createClient, type SupabaseClient} from '@supabase/supabase-js';
import {config} from './config';

export type VideoRow = {
  id: string;
  status: string;
  template: 'explainer' | 'tutorial' | 'listicle' | 'comparison';
  topic: string;
  script_json: unknown;
  asset_urls: unknown;
};

let client: SupabaseClient | null = null;
const getClient = (): SupabaseClient => {
  client ??= createClient(config.supabaseUrl(), config.supabaseServiceRoleKey());
  return client;
};

export const fetchVideo = async (id: string): Promise<VideoRow | null> => {
  const {data, error} = await getClient()
    .from('videos')
    .select('id,status,template,topic,script_json,asset_urls')
    .eq('id', id)
    .maybeSingle();
  if (error) throw new Error(`fetchVideo(${id}): ${error.message}`);
  return data as VideoRow | null;
};

export const updateVideo = async (
  id: string,
  patch: Record<string, unknown>,
): Promise<void> => {
  const {error} = await getClient().from('videos').update(patch).eq('id', id);
  if (error) throw new Error(`updateVideo(${id}): ${error.message}`);
};

export const uploadRender = async (
  path: string,
  body: Buffer,
  contentType: string,
): Promise<string> => {
  const supabase = getClient();
  const {error} = await supabase.storage
    .from(config.rendersBucket)
    .upload(path, body, {contentType, upsert: true});
  if (error) throw new Error(`uploadRender(${path}): ${error.message}`);
  return supabase.storage.from(config.rendersBucket).getPublicUrl(path).data.publicUrl;
};
```

- [ ] **Step 4: Write `render.ts`**

```ts
import {execFile} from 'node:child_process';
import {mkdtemp, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {promisify} from 'node:util';
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {videoAssetsSchema, videoScriptSchema} from '../../src/types/video-script';
import {uploadRender, type VideoRow} from './supabase';

const execFileAsync = promisify(execFile);

const COMPOSITION_BY_TEMPLATE: Record<VideoRow['template'], string> = {
  explainer: 'Explainer',
  tutorial: 'Explainer', // Tutorial.tsx is Phase 6 — falls back to Explainer until then
  listicle: 'Listicle',
  comparison: 'Listicle', // Comparison.tsx is Phase 6
};

let bundlePromise: Promise<string> | null = null;
const getBundle = (): Promise<string> => {
  bundlePromise ??= bundle({entryPoint: join(__dirname, '..', '..', 'src', 'index.ts')});
  return bundlePromise;
};

/** ffmpeg -crf 28 -preset slow (spec §7 Stage 3 post-process, ~80% size cut). */
const compress = async (input: string, output: string): Promise<void> => {
  await execFileAsync('ffmpeg', [
    '-y', '-i', input,
    '-c:v', 'libx264', '-crf', '28', '-preset', 'slow',
    '-c:a', 'copy',
    output,
  ]);
};

export type RenderResult = {renderUrl: string; thumbnailUrl: string};

export const renderVideoJob = async (video: VideoRow): Promise<RenderResult> => {
  const script = videoScriptSchema.parse(video.script_json);
  const assets = videoAssetsSchema.parse(video.asset_urls ?? {});
  const inputProps = {script, assets};

  const serveUrl = await getBundle();
  const workDir = await mkdtemp(join(tmpdir(), `render-${video.id}-`));
  try {
    const composition = await selectComposition({
      serveUrl,
      id: COMPOSITION_BY_TEMPLATE[video.template],
      inputProps,
    });

    const rawPath = join(workDir, 'raw.mp4');
    const finalPath = join(workDir, 'final.mp4');
    const thumbPath = join(workDir, 'thumb.png');

    await renderMedia({
      composition,
      serveUrl,
      codec: 'h264',
      outputLocation: rawPath,
      inputProps,
    });
    await compress(rawPath, finalPath);

    const thumbComposition = await selectComposition({
      serveUrl,
      id: 'Thumbnail',
      inputProps: {headline: script.topic, baseImageUrl: assets.thumbnail_base},
    });
    await renderStill({
      composition: thumbComposition,
      serveUrl,
      output: thumbPath,
      inputProps: {headline: script.topic, baseImageUrl: assets.thumbnail_base},
    });

    const [renderUrl, thumbnailUrl] = await Promise.all([
      uploadRender(`${video.id}/final.mp4`, await readFile(finalPath), 'video/mp4'),
      uploadRender(`${video.id}/thumbnail.png`, await readFile(thumbPath), 'image/png'),
    ]);
    return {renderUrl, thumbnailUrl};
  } finally {
    await rm(workDir, {recursive: true, force: true});
  }
};
```

- [ ] **Step 5: Write `app.ts` and `index.ts`**

`remotion/render-server/src/app.ts`:
```ts
import express, {type Express} from 'express';
import {renderVideoJob} from './render';
import {fetchVideo, updateVideo} from './supabase';

export const createApp = (): Express => {
  const app = express();
  app.use(express.json());

  app.get('/healthz', (_req, res) => {
    res.json({ok: true});
  });

  app.post('/render', async (req, res) => {
    const videoId = req.body?.video_id;
    if (typeof videoId !== 'string' || videoId.length === 0) {
      res.status(400).json({error: 'video_id (string) is required'});
      return;
    }
    try {
      const video = await fetchVideo(videoId);
      if (!video) {
        res.status(404).json({error: `video ${videoId} not found`});
        return;
      }
      if (video.status !== 'assets_ready') {
        res.status(409).json({
          error: `video ${videoId} is '${video.status}', expected 'assets_ready'`,
        });
        return;
      }
      const {renderUrl, thumbnailUrl} = await renderVideoJob(video);
      await updateVideo(videoId, {status: 'qa_pending', render_url: renderUrl});
      res.json({ok: true, render_url: renderUrl, thumbnail_url: thumbnailUrl});
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[render] ${videoId} failed:`, message);
      res.status(500).json({error: message});
    }
  });

  return app;
};
```

`remotion/render-server/src/index.ts`:
```ts
import {config} from './config';
import {createApp} from './app';

const app = createApp();
app.listen(config.port, () => {
  console.log(`render server listening on :${config.port}`);
});
```

- [ ] **Step 6: Run tests to verify pass**

Run: `cd remotion && npx vitest run && npm run typecheck` → PASS / clean

- [ ] **Step 7: Commit**

```bash
git add remotion/render-server/
git commit -m "feat(render-server): POST /render — video+thumbnail job with ffmpeg compress"
```

---

### Task 11: Stage-1 CrewAI agents (trend_scraper, hook_writer, script_writer, pipeline CLI)

**Files:**
- Create: `agents/llm.py`, `agents/db.py`, `agents/trend_scraper.py`, `agents/hook_writer.py`, `agents/script_writer.py`, `agents/pipeline.py`
- Test: `tests/test_trend_scraper.py`, `tests/test_hook_writer.py`, `tests/test_script_writer.py`

Design rule: prompt builders and output parsers are **pure functions** (tested, no network). CrewAI/LLM and Supabase calls are thin, injectable boundaries that tests never hit. All LLM work runs on Claude via one config point (`llm.py`).

Note on sources (spec §7 Stage 1): Reddit has a public JSON endpoint (implemented). YouTube trending uses the YouTube Data API key the pipeline already requires (implemented, optional at runtime). TikTok Creative Center has **no public API** — it is a documented manual input (paste topics into the CLI), recorded in `docs/setup.md`. This is a deliberate decision, not an omission.

- [ ] **Step 1: Write the failing tests**

`tests/test_trend_scraper.py`:
```python
import httpx

from agents.trend_scraper import (
    RedditPost,
    TopicCandidate,
    candidates_from_reddit,
    fetch_subreddit_top,
    rank_topics,
)


def make_candidate(topic: str, score: float) -> TopicCandidate:
    return TopicCandidate(topic=topic, evidence="e", source="reddit:r/ChatGPT", score=score)


class TestRankTopics:
    def test_sorts_by_score_descending(self):
        ranked = rank_topics([make_candidate("a", 1.0), make_candidate("b", 5.0)])
        assert [c.topic for c in ranked] == ["b", "a"]

    def test_dedupes_case_insensitively_keeping_higher_score(self):
        ranked = rank_topics([make_candidate("AI tools", 2.0), make_candidate("ai tools", 9.0)])
        assert len(ranked) == 1
        assert ranked[0].score == 9.0

    def test_respects_top_n(self):
        cands = [make_candidate(f"t{i}", float(i)) for i in range(20)]
        assert len(rank_topics(cands, top_n=5)) == 5


class TestCandidatesFromReddit:
    def test_maps_posts_to_candidates(self):
        posts = [
            RedditPost(
                title="I automated my whole job with Claude",
                score=900,
                num_comments=150,
                url="https://reddit.com/x",
                subreddit="ChatGPT",
            )
        ]
        (cand,) = candidates_from_reddit(posts)
        assert cand.topic == "I automated my whole job with Claude"
        assert cand.source == "reddit:r/ChatGPT"
        assert cand.score == 900 + 2 * 150
        assert "900" in cand.evidence


class TestFetchSubredditTop:
    def test_parses_listing_json(self):
        listing = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "t",
                            "score": 10,
                            "num_comments": 3,
                            "permalink": "/r/ChatGPT/comments/abc/t/",
                        }
                    }
                ]
            }
        }
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=listing))
        client = httpx.Client(transport=transport)
        posts = fetch_subreddit_top("ChatGPT", client=client)
        assert posts == [
            RedditPost(
                title="t",
                score=10,
                num_comments=3,
                url="https://www.reddit.com/r/ChatGPT/comments/abc/t/",
                subreddit="ChatGPT",
            )
        ]

    def test_raises_on_http_error(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(503))
        client = httpx.Client(transport=transport)
        try:
            fetch_subreddit_top("ChatGPT", client=client)
            raise AssertionError("expected an exception")
        except httpx.HTTPStatusError:
            pass
```

`tests/test_hook_writer.py`:
```python
import pytest

from agents.db import TasteExample
from agents.hook_writer import HookVariant, build_hook_prompt, parse_hook_variants

EXAMPLES = [
    TasteExample(
        hook_text="You're using ChatGPT wrong.",
        hook_type="bold_claim",
        why_it_works="Confrontational pattern interrupt",
    )
]


class TestBuildHookPrompt:
    def test_includes_topic_examples_and_count(self):
        prompt = build_hook_prompt("PDF summarization", EXAMPLES)
        assert "PDF summarization" in prompt
        assert "You're using ChatGPT wrong." in prompt
        assert "5" in prompt  # five variants (spec §7)

    def test_works_with_empty_taste_library(self):
        prompt = build_hook_prompt("topic", [])
        assert "topic" in prompt


class TestParseHookVariants:
    def test_parses_plain_json_array(self):
        raw = '[{"text": "Hook one?", "hook_type": "question"}]'
        assert parse_hook_variants(raw) == [HookVariant(text="Hook one?", hook_type="question")]

    def test_parses_fenced_json(self):
        raw = 'Here you go:\n```json\n[{"text": "X", "hook_type": "demo"}]\n```\nEnjoy!'
        assert parse_hook_variants(raw)[0].hook_type == "demo"

    def test_rejects_invalid_hook_type(self):
        with pytest.raises(ValueError):
            parse_hook_variants('[{"text": "X", "hook_type": "clickbait"}]')

    def test_rejects_output_without_json_array(self):
        with pytest.raises(ValueError, match="JSON array"):
            parse_hook_variants("I could not generate hooks.")
```

`tests/test_script_writer.py`:
```python
import json
from pathlib import Path

import pytest

from agents.script_writer import HARD_CONSTRAINTS, build_script_prompt, parse_video_script

FIXTURE = Path(__file__).parent.parent / "schemas" / "fixtures" / "sample_video_script.json"


class TestPrompt:
    def test_hard_constraints_present(self):
        # spec §7 Stage 1: hook ≤ 3s, payoff in first 15s, one idea, plain language
        for phrase in ("3", "15", "one idea", "plain"):
            assert phrase in HARD_CONSTRAINTS.lower() or phrase in HARD_CONSTRAINTS

    def test_prompt_embeds_topic_hook_and_schema(self):
        prompt = build_script_prompt("topic X", "hook Y", template="listicle")
        assert "topic X" in prompt and "hook Y" in prompt
        assert "listicle" in prompt
        assert "visual_type" in prompt  # schema is shown to the model


class TestParseVideoScript:
    def test_parses_valid_fixture_json(self):
        script = parse_video_script(FIXTURE.read_text())
        assert script.template == "explainer"

    def test_parses_fenced_output(self):
        raw = f"```json\n{FIXTURE.read_text()}\n```"
        assert parse_video_script(raw).template == "explainer"

    def test_invalid_schema_raises(self):
        bad = json.loads(FIXTURE.read_text())
        bad["target_duration_s"] = 300
        with pytest.raises(ValueError):
            parse_video_script(json.dumps(bad))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_trend_scraper.py tests/test_hook_writer.py tests/test_script_writer.py -q`
Expected: FAIL — ModuleNotFoundError for `agents.trend_scraper` etc.

- [ ] **Step 3: Write `agents/llm.py` and `agents/db.py`**

`agents/llm.py`:
```python
"""Single LLM config point — all agent work runs on Claude (spec §3: one tool per job)."""

import os

from crewai import LLM

DEFAULT_MODEL = "claude-sonnet-4-6"


def claude_llm(temperature: float = 0.7) -> LLM:
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    return LLM(model=f"anthropic/{model}", temperature=temperature)
```

`agents/db.py`:
```python
"""Supabase access for agents. Every function takes an injectable client for testing."""

import os

from pydantic import BaseModel
from supabase import Client, create_client

from schemas.video_script import VideoScript


class TasteExample(BaseModel):
    hook_text: str
    hook_type: str | None = None
    why_it_works: str | None = None


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def insert_scripted_video(script: VideoScript, client: Client | None = None) -> str:
    """Insert a Stage-1 result as status=scripted. Returns the new video id."""
    client = client or get_client()
    row = {
        "status": "scripted",
        "template": script.template,
        "topic": script.topic,
        "hook": script.hook.text,
        "script_json": script.model_dump(mode="json"),
    }
    result = client.table("videos").insert(row).execute()
    return result.data[0]["id"]


def top_taste_hooks(limit: int = 20, client: Client | None = None) -> list[TasteExample]:
    """Top hooks by views — few-shot examples for the hook writer (spec §7 Stage 1)."""
    client = client or get_client()
    result = (
        client.table("taste_library")
        .select("hook_text,hook_type,why_it_works")
        .not_.is_("hook_text", "null")
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    return [TasteExample.model_validate(r) for r in result.data]
```

- [ ] **Step 4: Write `agents/trend_scraper.py`**

```python
"""Stage 1: ranked topic candidates with evidence (spec §7).

Sources: Reddit public JSON (no key), YouTube trending (uses YOUTUBE_API_KEY,
skipped if unset). TikTok Creative Center has no public API — paste those
topics manually via `pipeline run --topic`. See docs/setup.md.
"""

import os

import httpx
from pydantic import BaseModel

SUBREDDITS: tuple[str, ...] = ("ChatGPT", "ArtificialInteligence", "sidehustle")
USER_AGENT = "build-commons-pipeline/0.1 (trend research)"
COMMENT_WEIGHT = 2


class RedditPost(BaseModel):
    title: str
    score: int
    num_comments: int
    url: str
    subreddit: str


class TopicCandidate(BaseModel):
    topic: str
    evidence: str
    source: str
    score: float


def fetch_subreddit_top(
    subreddit: str, limit: int = 25, client: httpx.Client | None = None
) -> list[RedditPost]:
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20)
    resp = client.get(
        f"https://www.reddit.com/r/{subreddit}/top.json",
        params={"t": "week", "limit": limit},
    )
    resp.raise_for_status()
    children = resp.json().get("data", {}).get("children", [])
    return [
        RedditPost(
            title=c["data"]["title"],
            score=c["data"]["score"],
            num_comments=c["data"]["num_comments"],
            url=f"https://www.reddit.com{c['data']['permalink']}",
            subreddit=subreddit,
        )
        for c in children
    ]


def candidates_from_reddit(posts: list[RedditPost]) -> list[TopicCandidate]:
    return [
        TopicCandidate(
            topic=p.title,
            evidence=f"{p.score} upvotes, {p.num_comments} comments in r/{p.subreddit} ({p.url})",
            source=f"reddit:r/{p.subreddit}",
            score=float(p.score + COMMENT_WEIGHT * p.num_comments),
        )
        for p in posts
    ]


def fetch_youtube_trending(
    api_key: str, region: str = "US", client: httpx.Client | None = None
) -> list[TopicCandidate]:
    """Trending in Science & Tech (category 28). Optional — needs YOUTUBE_API_KEY."""
    client = client or httpx.Client(timeout=20)
    resp = client.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "videoCategoryId": "28",
            "regionCode": region,
            "maxResults": 25,
            "key": api_key,
        },
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        TopicCandidate(
            topic=item["snippet"]["title"],
            evidence=f"{item['statistics'].get('viewCount', '?')} views, YT trending #{i + 1}",
            source="youtube:trending",
            score=float(item["statistics"].get("viewCount", 0)),
        )
        for i, item in enumerate(items)
    ]


def rank_topics(candidates: list[TopicCandidate], top_n: int = 10) -> list[TopicCandidate]:
    """Dedupe (case-insensitive, keep best score) and sort descending."""
    best: dict[str, TopicCandidate] = {}
    for cand in candidates:
        key = cand.topic.strip().lower()
        if key not in best or cand.score > best[key].score:
            best[key] = cand
    return sorted(best.values(), key=lambda c: c.score, reverse=True)[:top_n]


def gather_candidates() -> list[TopicCandidate]:
    """All sources, ranked. Network failures in one source don't kill the run."""
    candidates: list[TopicCandidate] = []
    for sub in SUBREDDITS:
        try:
            candidates.extend(candidates_from_reddit(fetch_subreddit_top(sub)))
        except httpx.HTTPError as exc:
            print(f"[trend_scraper] r/{sub} failed: {exc}")
    yt_key = os.environ.get("YOUTUBE_API_KEY")
    if yt_key:
        try:
            candidates.extend(fetch_youtube_trending(yt_key))
        except httpx.HTTPError as exc:
            print(f"[trend_scraper] youtube trending failed: {exc}")
    return rank_topics(candidates)
```

- [ ] **Step 5: Write `agents/hook_writer.py`**

```python
"""Stage 1: 5 hook variants per topic, few-shot from the taste library (spec §7)."""

import json
import re
from typing import Literal

from crewai import Agent, Task
from pydantic import BaseModel, ValidationError

from agents.db import TasteExample
from agents.llm import claude_llm

HOOK_COUNT = 5


class HookVariant(BaseModel):
    text: str
    hook_type: Literal["question", "bold_claim", "curiosity_gap", "demo"]


def build_hook_prompt(topic: str, examples: list[TasteExample]) -> str:
    example_block = (
        "\n".join(
            f'- "{e.hook_text}" ({e.hook_type or "unknown"}) — {e.why_it_works or "n/a"}'
            for e in examples
        )
        or "- (taste library is empty — rely on the hook types below)"
    )
    return f"""You write 3-second hooks for short-form videos teaching practical AI \
workflows to a non-technical audience.

Topic: {topic}

Hooks that performed well in this niche (steal the *patterns*, never the words):
{example_block}

Write exactly {HOOK_COUNT} hook variants. Mix hook types across: question, bold_claim, \
curiosity_gap, demo. Each must be speakable in under 3 seconds (max ~12 words), concrete, \
and contain zero hype words ("insane", "mind-blowing", "game-changer").

Respond with ONLY a JSON array:
[{{"text": "...", "hook_type": "question|bold_claim|curiosity_gap|demo"}}]"""


def _extract_json_array(raw: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON array found in model output: {raw[:200]!r}")
    return cleaned[start : end + 1]


def parse_hook_variants(raw: str) -> list[HookVariant]:
    try:
        items = json.loads(_extract_json_array(raw))
        return [HookVariant.model_validate(item) for item in items]
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"could not parse hook variants: {exc}") from exc


def build_hook_agent() -> Agent:
    return Agent(
        role="Short-form hook writer",
        goal="Write scroll-stopping 3-second hooks that earn the next 15 seconds",
        backstory="Studied thousands of top-performing shorts in the AI-tools niche.",
        llm=claude_llm(temperature=0.9),
        verbose=False,
    )


def generate_hooks(topic: str, examples: list[TasteExample]) -> list[HookVariant]:
    agent = build_hook_agent()
    task = Task(
        description=build_hook_prompt(topic, examples),
        expected_output="A JSON array of 5 hook variants",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_hook_variants(result.raw)
```

- [ ] **Step 6: Write `agents/script_writer.py`**

```python
"""Stage 1: produce the VideoScript contract JSON (spec §6, §7)."""

import json
import re

from crewai import Agent, Task
from pydantic import ValidationError

from agents.llm import claude_llm
from schemas.video_script import VideoScript

HARD_CONSTRAINTS = """HARD CONSTRAINTS (violating any of these makes the output unusable):
- The hook must be speakable in at most 3 seconds.
- Deliver the payoff within the first 15 seconds.
- Exactly one idea per video. If a second idea appears, cut it.
- Plain language for a non-technical audience: no jargon, no acronyms without expansion.
- Target duration 30-60 seconds total."""

SCHEMA_GUIDE = """Output schema (respond with ONLY this JSON object, no commentary):
{
  "topic": str,
  "template": "explainer" | "tutorial" | "listicle" | "comparison",
  "hook": Segment,        // the provided hook, duration_estimate_s <= 3
  "segments": [Segment],  // 2-5 body segments
  "cta": Segment,
  "target_duration_s": int (30-60),
  "platform_captions": {"youtube": str, "tiktok": str, "instagram": str},
  "hashtags": {"youtube": [str], "tiktok": [str], "instagram": [str]}
}
Segment = {
  "id": str (unique, e.g. "hook", "seg-1", "cta"),
  "text": str (the narration),
  "visual_type": "ai_broll" | "ai_image" | "screen_recording" | "text_card",
  "visual_prompt": str | null (REQUIRED for ai_broll/ai_image; detailed, cinematic),
  "duration_estimate_s": float,
  "caption_emphasis": [str] (words to highlight in captions)
}"""


def build_script_prompt(topic: str, hook_text: str, template: str) -> str:
    return f"""You write scripts for short-form videos teaching practical AI workflows.

Topic: {topic}
Chosen hook (use verbatim as the hook segment text): {hook_text}
Template: {template}

{HARD_CONSTRAINTS}

{SCHEMA_GUIDE}"""


def parse_video_script(raw: str) -> VideoScript:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in model output: {raw[:200]!r}")
    try:
        return VideoScript.model_validate(json.loads(cleaned[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"model output failed VideoScript validation: {exc}") from exc


def build_script_agent() -> Agent:
    return Agent(
        role="Short-form script writer",
        goal="Turn a topic and hook into a tight 30-60s script that holds retention",
        backstory="Writes plainly, cuts ruthlessly, one idea per video.",
        llm=claude_llm(temperature=0.7),
        verbose=False,
    )


def generate_script(topic: str, hook_text: str, template: str = "explainer") -> VideoScript:
    agent = build_script_agent()
    task = Task(
        description=build_script_prompt(topic, hook_text, template),
        expected_output="A single VideoScript JSON object",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_video_script(result.raw)
```

- [ ] **Step 7: Write `agents/pipeline.py`**

```python
"""Stage-1 CLI: topic → hooks → script → videos row (status=scripted).

Usage:
    uv run python -m agents.pipeline run --topic "..."   # manual topic (e.g. TikTok CC)
    uv run python -m agents.pipeline run                  # auto: top trend candidate
    uv run python -m agents.pipeline trends               # just print ranked candidates
"""

import argparse

from agents.db import get_client, insert_scripted_video, top_taste_hooks
from agents.hook_writer import generate_hooks
from agents.script_writer import generate_script
from agents.trend_scraper import gather_candidates


def run_stage1(topic: str | None = None, template: str = "explainer") -> str:
    client = get_client()
    if topic is None:
        candidates = gather_candidates()
        if not candidates:
            raise RuntimeError("no trend candidates found and no --topic given")
        topic = candidates[0].topic
        print(f"[pipeline] auto-selected topic: {topic}")

    examples = top_taste_hooks(client=client)
    hooks = generate_hooks(topic, examples)
    print("[pipeline] hook variants:")
    for i, hook in enumerate(hooks, 1):
        print(f"  {i}. ({hook.hook_type}) {hook.text}")

    script = generate_script(topic, hooks[0].text, template)
    video_id = insert_scripted_video(script, client=client)
    print(f"[pipeline] inserted video {video_id} (status=scripted)")
    return video_id


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="full Stage 1: topic -> scripted row")
    run.add_argument("--topic", default=None, help="manual topic (else top trend)")
    run.add_argument(
        "--template",
        default="explainer",
        choices=["explainer", "tutorial", "listicle", "comparison"],
    )

    sub.add_parser("trends", help="print ranked topic candidates")

    args = parser.parse_args()
    if args.command == "run":
        run_stage1(args.topic, args.template)
    elif args.command == "trends":
        for cand in gather_candidates():
            print(f"{cand.score:>10.0f}  {cand.topic}  [{cand.source}]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run tests to verify pass**

Run: `uv run pytest -q && uv run ruff check .` → all PASS / clean

- [ ] **Step 9: Commit**

```bash
git add agents/ tests/
git commit -m "feat(agents): Stage-1 CrewAI agents — trends, hooks, script, pipeline CLI"
```

---

### Task 12: Analyst agent (Stage 6)

**Files:**
- Create: `agents/analyst.py`
- Test: `tests/test_analyst.py`
- Create: `docs/reports/.gitkeep`

Spec §7 Stage 6: score hooks/templates/topics by 3s-hold and completion rate, promote winning hooks into `taste_library`, flag declining templates, output weekly markdown report. Thresholds come from spec §11 (hold ≥ 70%, completion ≥ 40%).

- [ ] **Step 1: Write the failing tests** — `tests/test_analyst.py`

```python
import pytest

from agents.analyst import (
    COMPLETION_THRESHOLD,
    HOLD_THRESHOLD,
    VideoScore,
    flag_declining_templates,
    fraction_at,
    pick_promotable_hooks,
    render_weekly_report,
    score_video,
)

CURVE = [
    {"t_s": 0.0, "fraction": 1.0},
    {"t_s": 5.0, "fraction": 0.7},
    {"t_s": 30.0, "fraction": 0.45},
]


def make_score(**overrides) -> VideoScore:
    base = dict(
        video_id="v1",
        topic="t",
        template="explainer",
        hook="Stop doing X.",
        hold_rate_3s=0.8,
        completion_rate=0.5,
    )
    base.update(overrides)
    return VideoScore(**base)


class TestFractionAt:
    def test_interpolates_linearly(self):
        assert fraction_at(CURVE, 2.5) == pytest.approx(0.85)  # halfway 0->5s: 1.0 -> 0.7

    def test_clamps_to_endpoints(self):
        assert fraction_at(CURVE, -1) == 1.0
        assert fraction_at(CURVE, 99) == 0.45

    def test_empty_curve_returns_none(self):
        assert fraction_at([], 3.0) is None


class TestScoreVideo:
    def test_computes_hold_and_completion(self):
        row = {"id": "v1", "topic": "t", "template": "explainer", "hook": "h"}
        score = score_video(row, CURVE)
        assert score.hold_rate_3s == fraction_at(CURVE, 3.0)
        assert score.completion_rate == 0.45

    def test_no_curve_gives_none_metrics(self):
        score = score_video({"id": "v1", "topic": "t", "template": None, "hook": None}, None)
        assert score.hold_rate_3s is None and score.completion_rate is None


class TestPromotions:
    def test_promotes_only_above_both_thresholds(self):
        winner = make_score()
        weak_hold = make_score(video_id="v2", hold_rate_3s=HOLD_THRESHOLD - 0.05)
        weak_completion = make_score(video_id="v3", completion_rate=COMPLETION_THRESHOLD - 0.05)
        rows = pick_promotable_hooks([winner, weak_hold, weak_completion])
        assert len(rows) == 1
        assert rows[0]["hook_text"] == "Stop doing X."
        assert rows[0]["added_by"] == "analyst_agent"

    def test_skips_scores_with_missing_metrics_or_hook(self):
        assert pick_promotable_hooks([make_score(hold_rate_3s=None)]) == []
        assert pick_promotable_hooks([make_score(hook=None)]) == []


class TestTemplateFlags:
    def test_flags_template_whose_latest_drops_below_90pct_of_prior_mean(self):
        history = {"explainer": [0.6, 0.6, 0.4], "listicle": [0.5, 0.5, 0.5]}
        assert flag_declining_templates(history) == ["explainer"]

    def test_needs_at_least_three_data_points(self):
        assert flag_declining_templates({"explainer": [0.6, 0.3]}) == []


class TestReport:
    def test_report_contains_sections_and_data(self):
        report = render_weekly_report(
            scores=[make_score()],
            promotions=pick_promotable_hooks([make_score()]),
            flagged=["listicle"],
        )
        assert "# Weekly Content Report" in report
        assert "Stop doing X." in report
        assert "listicle" in report
        assert "Make more" in report and "Kill" in report
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_analyst.py -q` → FAIL (module not found)

- [ ] **Step 3: Write `agents/analyst.py`**

```python
"""Stage 6: weekly analytics scoring, hook promotion, template health (spec §7).

Usage:
    uv run python -m agents.analyst report
"""

import argparse
import datetime as dt
from pathlib import Path

from pydantic import BaseModel
from supabase import Client

from agents.db import get_client

# Success thresholds from spec §11.
HOLD_THRESHOLD = 0.70
COMPLETION_THRESHOLD = 0.40
DECLINE_RATIO = 0.90
MIN_HISTORY_POINTS = 3

Curve = list[dict]  # [{"t_s": float, "fraction": float}, ...] sorted by t_s


class VideoScore(BaseModel):
    video_id: str
    topic: str
    template: str | None
    hook: str | None
    hold_rate_3s: float | None
    completion_rate: float | None


def fraction_at(curve: Curve, t_s: float) -> float | None:
    """Linear interpolation of viewer fraction at time t; clamps to endpoints."""
    if not curve:
        return None
    points = sorted(curve, key=lambda p: p["t_s"])
    if t_s <= points[0]["t_s"]:
        return points[0]["fraction"]
    for prev, nxt in zip(points, points[1:], strict=False):
        if t_s <= nxt["t_s"]:
            span = nxt["t_s"] - prev["t_s"]
            if span == 0:
                return nxt["fraction"]
            ratio = (t_s - prev["t_s"]) / span
            return prev["fraction"] + ratio * (nxt["fraction"] - prev["fraction"])
    return points[-1]["fraction"]


def score_video(video_row: dict, retention_curve: Curve | None) -> VideoScore:
    curve = retention_curve or []
    return VideoScore(
        video_id=str(video_row["id"]),
        topic=video_row.get("topic") or "",
        template=video_row.get("template"),
        hook=video_row.get("hook"),
        hold_rate_3s=fraction_at(curve, 3.0),
        completion_rate=fraction_at(curve, float("inf")) if curve else None,
    )


def pick_promotable_hooks(scores: list[VideoScore]) -> list[dict]:
    """Winning hooks → taste_library rows. Closes the feedback loop."""
    rows = []
    for s in scores:
        if s.hook is None or s.hold_rate_3s is None or s.completion_rate is None:
            continue
        if s.hold_rate_3s >= HOLD_THRESHOLD and s.completion_rate >= COMPLETION_THRESHOLD:
            rows.append(
                {
                    "hook_text": s.hook,
                    "niche": "ai-tools",
                    "why_it_works": (
                        f"Promoted by analyst: 3s-hold {s.hold_rate_3s:.0%}, "
                        f"completion {s.completion_rate:.0%} on '{s.topic}'"
                    ),
                    "added_by": "analyst_agent",
                }
            )
    return rows


def flag_declining_templates(history: dict[str, list[float]]) -> list[str]:
    """Flag templates whose latest avg retention < 90% of the prior mean."""
    flagged = []
    for name, values in history.items():
        if len(values) < MIN_HISTORY_POINTS:
            continue
        prior = values[:-1]
        if values[-1] < DECLINE_RATIO * (sum(prior) / len(prior)):
            flagged.append(name)
    return sorted(flagged)


def render_weekly_report(
    scores: list[VideoScore], promotions: list[dict], flagged: list[str]
) -> str:
    scored = [s for s in scores if s.hold_rate_3s is not None]
    winners = sorted(scored, key=lambda s: s.hold_rate_3s or 0, reverse=True)[:5]
    losers = sorted(scored, key=lambda s: s.hold_rate_3s or 0)[:5]

    def table(rows: list[VideoScore]) -> str:
        if not rows:
            return "_no scored videos this week_"
        lines = ["| Topic | Template | 3s hold | Completion |", "|---|---|---|---|"]
        lines += [
            f"| {s.topic} | {s.template or '-'} | "
            f"{s.hold_rate_3s:.0%} | {(s.completion_rate or 0):.0%} |"
            for s in rows
        ]
        return "\n".join(lines)

    promo_lines = "\n".join(f'- "{p["hook_text"]}" — {p["why_it_works"]}' for p in promotions)
    return f"""# Weekly Content Report — {dt.date.today().isoformat()}

## Make more of this (top 3s-hold)
{table(winners)}

## Kill / rework (bottom 3s-hold)
{table(losers)}

## Hooks promoted to taste library
{promo_lines or "_none met thresholds (hold >= 70%, completion >= 40%)_"}

## Template health
{("Flagged for rebuild: " + ", ".join(flagged)) if flagged else "All templates healthy."}
"""


def run_weekly(client: Client | None = None, reports_dir: Path | None = None) -> Path:
    """Fetch last week's data, score, promote, flag, write the report. Returns report path."""
    client = client or get_client()
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=7)).isoformat()

    videos = (
        client.table("videos").select("id,topic,template,hook")
        .eq("status", "published").execute()
    ).data
    analytics = (
        client.table("analytics")
        .select("video_id,retention_curve,captured_at")
        .gte("captured_at", since)
        .execute()
    ).data

    latest_curve: dict[str, Curve] = {}
    for row in sorted(analytics, key=lambda r: r["captured_at"]):
        if row.get("retention_curve"):
            latest_curve[str(row["video_id"])] = row["retention_curve"]

    scores = [score_video(v, latest_curve.get(str(v["id"]))) for v in videos]
    promotions = pick_promotable_hooks(scores)
    if promotions:
        client.table("taste_library").insert(promotions).execute()

    # Template health: avg retention per template from this week's scores.
    by_template: dict[str, list[float]] = {}
    for s in scores:
        if s.template and s.completion_rate is not None:
            by_template.setdefault(s.template, []).append(s.completion_rate)
    for name, values in by_template.items():
        avg = sum(values) / len(values)
        client.table("templates").update({"avg_retention": avg}).eq("name", name).execute()

    report = render_weekly_report(scores, promotions, flagged=[])
    reports_dir = reports_dir or Path(__file__).parent.parent / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{dt.date.today().isoformat()}-weekly.md"
    path.write_text(report)
    print(f"[analyst] wrote {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents.analyst")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="run the weekly scoring + report")
    args = parser.parse_args()
    if args.command == "report":
        run_weekly()


if __name__ == "__main__":
    main()
```

Note: `run_weekly` passes `flagged=[]` because decline detection needs multi-week history; `flag_declining_templates` is wired for that and unit-tested — feed it once several weeks of `templates.avg_retention` snapshots exist (tracked in TODO.md).

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest -q && uv run ruff check .` → PASS / clean

- [ ] **Step 5: Commit**

```bash
git add agents/analyst.py tests/test_analyst.py docs/reports/.gitkeep
git commit -m "feat(agents): analyst — retention scoring, hook promotion, weekly report"
```

---

### Task 13: n8n workflow exports

**Files:**
- Create: `n8n/workflows/generate.json`, `n8n/workflows/publish.json`, `n8n/workflows/analytics.json`
- Test: `tests/test_n8n_workflows.py`

These are importable skeletons: triggers, Postgres reads/writes, HTTP calls to providers and the render server. Credentials are attached in the n8n UI after import (never in these files). n8n is plumbing only — no content logic. Retry policy (spec §7 Stage 2): `retryOnFail: true, maxTries: 3` (= 2 retries) on every provider HTTP node; failures route to a "flag manual review" Postgres update.

- [ ] **Step 1: Write the failing test** — `tests/test_n8n_workflows.py`

```python
import json
from pathlib import Path

import pytest

WORKFLOWS_DIR = Path(__file__).parent.parent / "n8n" / "workflows"
WORKFLOW_FILES = ["generate.json", "publish.json", "analytics.json"]


@pytest.fixture(params=WORKFLOW_FILES)
def workflow(request):
    return json.loads((WORKFLOWS_DIR / request.param).read_text())


def test_workflow_has_required_shape(workflow):
    assert isinstance(workflow["name"], str)
    assert isinstance(workflow["nodes"], list) and len(workflow["nodes"]) >= 2
    assert isinstance(workflow["connections"], dict)


def test_exactly_one_schedule_trigger(workflow):
    triggers = [n for n in workflow["nodes"] if n["type"].endswith("scheduleTrigger")]
    assert len(triggers) == 1


def test_connections_reference_existing_nodes(workflow):
    names = {n["name"] for n in workflow["nodes"]}
    for source, outputs in workflow["connections"].items():
        assert source in names, f"connection source '{source}' is not a node"
        for branch in outputs.get("main", []):
            for target in branch:
                assert target["node"] in names, f"target '{target['node']}' is not a node"


def test_no_embedded_secrets(workflow):
    text = json.dumps(workflow)
    for marker in ("sk-ant", "sk_live", "Bearer ey", "service_role"):
        assert marker not in text


def test_provider_nodes_have_retries():
    wf = json.loads((WORKFLOWS_DIR / "generate.json").read_text())
    provider_nodes = [
        n for n in wf["nodes"]
        if n["type"] == "n8n-nodes-base.httpRequest" and n["name"] != "Trigger render"
    ]
    assert provider_nodes, "expected provider HTTP nodes in generate.json"
    for node in provider_nodes:
        assert node.get("retryOnFail") is True, f"{node['name']} missing retryOnFail"
        assert node.get("maxTries") == 3, f"{node['name']} should have maxTries=3 (2 retries)"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_n8n_workflows.py -q` → FAIL (FileNotFoundError)

- [ ] **Step 3: Write `n8n/workflows/generate.json`** (Stage 2: asset fan-out + render trigger)

```json
{
  "name": "BC Stage 2 — Generate Assets + Render",
  "nodes": [
    {
      "parameters": {
        "rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}
      },
      "id": "trigger-15min",
      "name": "Every 15 minutes",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "select id, script_json from videos where status = 'scripted' order by created_at limit 2"
      },
      "id": "fetch-scripted",
      "name": "Fetch scripted videos",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [220, 0]
    },
    {
      "parameters": {
        "fieldToSplitOut": "script_json.segments",
        "include": "selectedOtherFields",
        "fieldsToInclude": "id"
      },
      "id": "split-segments",
      "name": "Split segments",
      "type": "n8n-nodes-base.splitOut",
      "typeVersion": 1,
      "position": [440, 0]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://api.elevenlabs.io/v1/text-to-speech/{{ $env.ELEVENLABS_VOICE_ID }}/with-timestamps",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"text\": {{ JSON.stringify($json[\"script_json.segments\"].text) }}, \"model_id\": \"eleven_multilingual_v2\"}"
      },
      "id": "tts",
      "name": "ElevenLabs TTS per segment",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, -160],
      "retryOnFail": true,
      "maxTries": 3,
      "onError": "continueErrorOutput"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpQueryAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"contents\": [{\"parts\": [{\"text\": {{ JSON.stringify($json[\"script_json.segments\"].visual_prompt || \"\") }}}]}]}"
      },
      "id": "nano-banana",
      "name": "Nano Banana image",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, 0],
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
        "jsonBody": "={\"instances\": [{\"prompt\": {{ JSON.stringify($json[\"script_json.segments\"].visual_prompt || \"\") }}}]}"
      },
      "id": "veo",
      "name": "Veo b-roll",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [660, 160],
      "retryOnFail": true,
      "maxTries": 3,
      "onError": "continueErrorOutput"
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "update videos set status = 'assets_ready', asset_urls = $1::jsonb where id = $2",
        "options": {"queryReplacement": "={{ JSON.stringify($json.asset_urls) }},{{ $json.id }}"}
      },
      "id": "save-assets",
      "name": "Save asset_urls",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [880, 0]
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
      "position": [1100, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "update videos set qa_notes = concat(coalesce(qa_notes, ''), ' asset generation failed after retries — manual review') where id = $1",
        "options": {"queryReplacement": "={{ $json.id }}"}
      },
      "id": "flag-manual",
      "name": "Flag manual review",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [880, 240]
    }
  ],
  "connections": {
    "Every 15 minutes": {"main": [[{"node": "Fetch scripted videos", "type": "main", "index": 0}]]},
    "Fetch scripted videos": {"main": [[{"node": "Split segments", "type": "main", "index": 0}]]},
    "Split segments": {
      "main": [[
        {"node": "ElevenLabs TTS per segment", "type": "main", "index": 0},
        {"node": "Nano Banana image", "type": "main", "index": 0},
        {"node": "Veo b-roll", "type": "main", "index": 0}
      ]]
    },
    "ElevenLabs TTS per segment": {
      "main": [
        [{"node": "Save asset_urls", "type": "main", "index": 0}],
        [{"node": "Flag manual review", "type": "main", "index": 0}]
      ]
    },
    "Nano Banana image": {
      "main": [
        [{"node": "Save asset_urls", "type": "main", "index": 0}],
        [{"node": "Flag manual review", "type": "main", "index": 0}]
      ]
    },
    "Veo b-roll": {
      "main": [
        [{"node": "Save asset_urls", "type": "main", "index": 0}],
        [{"node": "Flag manual review", "type": "main", "index": 0}]
      ]
    },
    "Save asset_urls": {"main": [[{"node": "Trigger render", "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}
```

- [ ] **Step 4: Write `n8n/workflows/publish.json`** (Stage 5)

```json
{
  "name": "BC Stage 5 — Publish",
  "nodes": [
    {
      "parameters": {
        "rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}
      },
      "id": "trigger-hourly",
      "name": "Hourly",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "select id, topic, render_url, script_json from videos where status = 'approved' order by created_at limit 1"
      },
      "id": "fetch-approved",
      "name": "Fetch approved video",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [220, 0]
    },
    {
      "parameters": {
        "resource": "video",
        "operation": "upload",
        "title": "={{ $json.topic }}",
        "regionCode": "US",
        "categoryId": "28",
        "options": {
          "description": "={{ $json.script_json.platform_captions.youtube }} {{ ($json.script_json.hashtags.youtube || []).join(' ') }}"
        }
      },
      "id": "yt-upload",
      "name": "YouTube upload",
      "type": "n8n-nodes-base.youTube",
      "typeVersion": 1,
      "position": [440, -120],
      "retryOnFail": true,
      "maxTries": 3
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://open.tiktokapis.com/v2/post/publish/video/init/",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"post_info\": {\"title\": {{ JSON.stringify($json.script_json.platform_captions.tiktok) }}, \"privacy_level\": \"PUBLIC_TO_EVERYONE\"}, \"source_info\": {\"source\": \"PULL_FROM_URL\", \"video_url\": {{ JSON.stringify($json.render_url) }}}}"
      },
      "id": "tiktok-post",
      "name": "TikTok post",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [440, 0],
      "retryOnFail": true,
      "maxTries": 3
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://graph.facebook.com/v21.0/{{ $env.IG_USER_ID }}/media",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpQueryAuth",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\"media_type\": \"REELS\", \"video_url\": {{ JSON.stringify($json.render_url) }}, \"caption\": {{ JSON.stringify($json.script_json.platform_captions.instagram) }}}"
      },
      "id": "ig-reel",
      "name": "Instagram Reel",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [440, 120],
      "retryOnFail": true,
      "maxTries": 3
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "update videos set status = 'published', published_at = now(), platform_ids = $1::jsonb where id = $2",
        "options": {"queryReplacement": "={{ JSON.stringify($json.platform_ids) }},{{ $json.id }}"}
      },
      "id": "mark-published",
      "name": "Mark published",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [660, 0]
    }
  ],
  "connections": {
    "Hourly": {"main": [[{"node": "Fetch approved video", "type": "main", "index": 0}]]},
    "Fetch approved video": {
      "main": [[
        {"node": "YouTube upload", "type": "main", "index": 0},
        {"node": "TikTok post", "type": "main", "index": 0},
        {"node": "Instagram Reel", "type": "main", "index": 0}
      ]]
    },
    "YouTube upload": {"main": [[{"node": "Mark published", "type": "main", "index": 0}]]},
    "TikTok post": {"main": [[{"node": "Mark published", "type": "main", "index": 0}]]},
    "Instagram Reel": {"main": [[{"node": "Mark published", "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}
```

Note: platform stagger (1–2h, spec §7 Stage 5) is configured with Wait nodes or separate schedules in the n8n UI during Phase 3 — the skeleton publishes to all three; AI-disclosure flag for YouTube is set per-video in the upload options once Phase 3 wiring happens (documented in docs/setup.md).

- [ ] **Step 5: Write `n8n/workflows/analytics.json`** (Stage 6 ingest)

```json
{
  "name": "BC Stage 6 — Analytics Ingest",
  "nodes": [
    {
      "parameters": {
        "rule": {"interval": [{"field": "days", "daysInterval": 1, "triggerAtHour": 6}]}
      },
      "id": "trigger-daily",
      "name": "Daily 6am",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0]
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "select id, platform_ids from videos where status = 'published' and published_at > now() - interval '30 days'"
      },
      "id": "fetch-published",
      "name": "Fetch published videos",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [220, 0]
    },
    {
      "parameters": {
        "method": "GET",
        "url": "https://youtubeanalytics.googleapis.com/v2/reports",
        "authentication": "genericCredentialType",
        "genericAuthType": "oAuth2Api",
        "sendQuery": true,
        "queryParameters": {
          "parameters": [
            {"name": "ids", "value": "channel==MINE"},
            {"name": "metrics", "value": "views,averageViewDuration,likes,shares"},
            {"name": "dimensions", "value": "video"},
            {"name": "filters", "value": "=video=={{ $json.platform_ids.youtube }}"},
            {"name": "startDate", "value": "={{ $now.minus({days: 7}).toFormat('yyyy-MM-dd') }}"},
            {"name": "endDate", "value": "={{ $now.toFormat('yyyy-MM-dd') }}"}
          ]
        }
      },
      "id": "yt-analytics",
      "name": "YouTube analytics",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [440, 0],
      "retryOnFail": true,
      "maxTries": 3
    },
    {
      "parameters": {
        "operation": "executeQuery",
        "query": "insert into analytics (video_id, platform, views, avg_view_duration_s, likes, shares) values ($1, 'youtube', $2, $3, $4, $5)",
        "options": {
          "queryReplacement": "={{ $('Fetch published videos').item.json.id }},{{ $json.rows?.[0]?.[1] ?? 0 }},{{ $json.rows?.[0]?.[2] ?? 0 }},{{ $json.rows?.[0]?.[3] ?? 0 }},{{ $json.rows?.[0]?.[4] ?? 0 }}"
        }
      },
      "id": "insert-analytics",
      "name": "Insert analytics rows",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.5,
      "position": [660, 0]
    }
  ],
  "connections": {
    "Daily 6am": {"main": [[{"node": "Fetch published videos", "type": "main", "index": 0}]]},
    "Fetch published videos": {"main": [[{"node": "YouTube analytics", "type": "main", "index": 0}]]},
    "YouTube analytics": {"main": [[{"node": "Insert analytics rows", "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}
```

- [ ] **Step 6: Run tests to verify pass**

Run: `uv run pytest tests/test_n8n_workflows.py -q` → PASS

- [ ] **Step 7: Commit**

```bash
git add n8n/ tests/test_n8n_workflows.py
git commit -m "feat(n8n): generate/publish/analytics workflow exports with retry policy"
```

---

### Task 14: Setup docs, architecture doc, final verification

**Files:**
- Create: `docs/setup.md`
- Modify: `docs/architecture.md` (replace template stub)

- [ ] **Step 1: Write `docs/setup.md`**

````markdown
# Setup Guide

## 1. Accounts & keys (spec §3 — one tool per job)

| Service | Job | Action |
|---|---|---|
| Anthropic API | All LLM work | Create key → `ANTHROPIC_API_KEY` |
| ElevenLabs (Creator) | Voiceover only | Clone OWN voice; keep consent recording; `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| Google AI Studio | All AI visuals (Nano Banana images, Veo 3.1 b-roll) | `GOOGLE_AI_STUDIO_API_KEY` |
| Supabase | State + storage | Project URL + service-role key; create buckets `assets`, `renders` |
| YouTube Data API v3 | Upload + analytics | OAuth client + `YOUTUBE_API_KEY` |
| TikTok Content Posting API | Upload | **Apply Week 1** — approval takes days–weeks |
| Instagram Graph API | Reels | Business/Creator account + Meta app — **apply Week 1** |
| CapCut Pro | Manual polish (Stage 4) | Account only, no API |

Do NOT set up: Canva, Descript, Kling, Ollama-in-pipeline, OpusClip (deliberately cut — spec §3).
Set a **$120/mo budget alert** across providers (spec §10).

## 2. Local environment

```bash
brew install ffmpeg
cp .env.example .env   # fill in keys
uv sync
cd remotion && npm install
```

## 3. Database

Run `supabase/migrations/0001_init.sql` in the Supabase SQL editor (or `supabase db push`).
Create public storage buckets `assets` and `renders`.

## 4. n8n (Docker on the Mac mini)

```bash
docker volume create n8n_data
docker run -d --restart unless-stopped --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE="America/Denver" \
  n8nio/n8n
```

Then in the n8n UI (http://localhost:5678): import the three files from `n8n/workflows/`,
attach credentials (Postgres → Supabase connection string; header auth for ElevenLabs
`xi-api-key`; query auth `key` for Google AI Studio; YouTube OAuth2), and activate.
The render server is reachable from Docker at `http://host.docker.internal:3333`.

Phase-3 wiring still done in the UI: platform stagger Wait nodes (1–2h), asset-URL
assembly into Supabase Storage, and the YouTube **AI-disclosure flag** for videos with
AI b-roll (required — spec §10).

## 5. Render server

```bash
cd remotion && npm run serve     # listens on :3333
curl -s localhost:3333/healthz   # {"ok":true}
```

## 6. Stage 1 (research → scripted row)

```bash
uv run python -m agents.pipeline trends                  # see ranked candidates
uv run python -m agents.pipeline run                     # auto top candidate
uv run python -m agents.pipeline run --topic "..."       # manual (e.g. TikTok Creative Center find)
```

TikTok Creative Center has no public API — browse it manually and feed winners in
via `--topic`.

## 7. Taste library seeding (do not skip — spec §9 Phase 2)

Watch 50 top videos in the niche, annotate each (~3–4 hrs total):

```sql
insert into taste_library (source_url, niche, hook_text, hook_type, why_it_works, views, added_by)
values ('https://...', 'ai-tools', 'You''re using ChatGPT wrong.', 'bold_claim',
        'Confrontational pattern interrupt; implies secret knowledge', 2400000, 'manual');
```

## 8. Stage 4 — human quality gate (~15 min/video)

For each `qa_pending` row: watch the render, then:
1. Hook lands in 3s? Rewrite if weak — highest-leverage edit.
2. No AI artifacts (garbled visual text, voice glitches, caption desync).
3. Factually correct.
4. Pacing — trim dead air in CapCut; trending audio bed where appropriate.
5. Thumbnail strong? Regenerate headline/base only if weak.

Approve: `update videos set status='approved' where id='...';`
Reject: `update videos set status='rejected', qa_notes='...' where id='...';`

## 9. Weekly analyst run

```bash
uv run python -m agents.analyst report   # writes docs/reports/YYYY-MM-DD-weekly.md
```

Schedule it (e.g. Sunday 7am) via launchd or an n8n Execute Command node.
````

- [ ] **Step 2: Replace `docs/architecture.md`**

```markdown
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

**State machine** (`videos.status`): ideation → scripted → assets_ready → rendered →
qa_pending → approved | rejected → published. Definition lives in
`supabase/migrations/0001_init.sql`.

**Key decisions** (spec §3): one tool per job; single b-roll provider (Veo) unless
failure rate >5%; no content logic in n8n; renders local on the Mac mini, Remotion
Lambda only if >10 videos/week.
```

- [ ] **Step 3: Full-suite final verification**

```bash
cd /Users/tannerkunz/coding/build-commons-pipeline
uv run pytest -q                      # all green
uv run ruff check .                   # clean
cd remotion && npm run typecheck && npx vitest run && cd ..
grep -rn "__[A-Z_]\+__" . --exclude-dir=node_modules --exclude-dir=.git | grep -v docs/superpowers || true   # no template placeholders
cmp CLAUDE.md AGENTS.md               # silent
git status --short                    # only the files from this task
```

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit -m "docs: setup guide + architecture map"
```

---

## Out of scope for this plan (tracked in TODO.md)

Account creation/API approvals, voice cloning, Supabase project provisioning, taste-library seeding (manual, 50 videos), n8n credential attachment, Phase-4 prompt tuning, Tutorial/Comparison compositions, OpusClip, Remotion Lambda.

