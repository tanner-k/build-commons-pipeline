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
                    f"overlay {o.id} ends at {o.end_s}s, past source_duration_s="
                    f"{self.source_duration_s}"
                )
        ordered = sorted(self.overlays, key=lambda o: o.start_s)
        for prev, nxt in zip(ordered, ordered[1:], strict=False):
            if nxt.start_s < prev.end_s:
                raise ValueError(f"overlays {prev.id} and {nxt.id} overlap in time")
        return self

    def sorted_overlays(self) -> list[Overlay]:
        return sorted(self.overlays, key=lambda o: o.start_s)
