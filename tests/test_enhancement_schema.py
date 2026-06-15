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
