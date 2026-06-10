"""Pipeline contract (spec §6). Source of truth.

Mirror: remotion/src/types/video-script.ts (zod). Shared fixture:
schemas/fixtures/sample_video_script.json is validated by both sides.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VisualType = Literal["ai_broll", "ai_image", "screen_recording", "text_card"]
TemplateName = Literal["explainer", "tutorial", "listicle", "comparison"]

AI_VISUAL_TYPES: frozenset[str] = frozenset({"ai_broll", "ai_image"})


class Segment(BaseModel):
    """One narrated beat of the video with its visual."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    visual_type: VisualType
    visual_prompt: str | None = None
    duration_estimate_s: float = Field(gt=0)
    caption_emphasis: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ai_visuals_need_prompt(self) -> "Segment":
        if self.visual_type in AI_VISUAL_TYPES and not (self.visual_prompt or "").strip():
            raise ValueError(
                f"visual_prompt is required when visual_type={self.visual_type!r}"
            )
        return self


class VideoScript(BaseModel):
    """Everything downstream stages need to produce one video."""

    model_config = ConfigDict(frozen=True)

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

    model_config = ConfigDict(frozen=True)

    word: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float

    @model_validator(mode="after")
    def _end_after_start(self) -> "WordTiming":
        if self.end_s < self.start_s:
            raise ValueError("end_s must be >= start_s")
        return self


class VideoAssets(BaseModel):
    """Shape of videos.asset_urls jsonb. Keys are segment ids."""

    model_config = ConfigDict(frozen=True)

    voiceover: dict[str, str] = Field(default_factory=dict)
    visuals: dict[str, str] = Field(default_factory=dict)
    timings: dict[str, list[WordTiming]] = Field(default_factory=dict)
    thumbnail_base: str | None = None


# Deliberately NOT validated here (downstream/QA concerns, not contract concerns):
# - platform_captions/hashtags may be empty or have mismatched platform keys;
#   Stage 5 publishing reads each platform independently.
# - Sum of segment durations is not checked against target_duration_s; the
#   estimate is advisory and real timing comes from ElevenLabs word timestamps.
# - WordTiming allows end_s == start_s (zero-width words from TTS edge cases).
