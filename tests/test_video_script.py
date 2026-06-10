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
