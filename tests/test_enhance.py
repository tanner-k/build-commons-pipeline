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
        assert "null" in low  # asset_url must be null at plan time
        assert "unique" in low  # unique ids

    def test_prompt_embeds_transcript_and_duration(self):
        p = build_enhancement_prompt("[0.0-3.0] hello world", 30.0)
        assert "hello world" in p
        assert "30" in p
        assert "overlays" in p

    def test_prompt_states_concrete_duration_bound(self):
        p = build_enhancement_prompt("[0.0-3.0] hi", 42.0)
        # explicit end_s bound the model can't miss (may wrap across lines)
        assert "end_s must be" in p and "42" in p


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


class TestInsertEnhancedVideo:
    def test_populates_script_json_and_topic_for_publish(self):
        from unittest.mock import MagicMock

        from agents.db import insert_enhanced_video

        plan = parse_enhancement_plan(GOOD_LLM_JSON, SRC, 20.0)
        client = MagicMock()
        result = MagicMock()
        result.data = [{"id": "vid-9"}]
        client.table.return_value.insert.return_value.execute.return_value = result

        video_id = insert_enhanced_video(plan, transcript=[], client=client)

        assert video_id == "vid-9"
        row = client.table.return_value.insert.call_args.args[0]
        assert row["kind"] == "enhanced" and row["status"] == "plan_ready"
        # publish.json reads platform_captions/hashtags from script_json — must be present here
        assert row["script_json"]["platform_captions"] == plan.platform_captions
        assert row["script_json"]["hashtags"] == plan.hashtags
        # topic drives the publish title; never empty for an enhanced row
        assert row["topic"] == "How I built it"
        assert row["enhancement_json"]["source_video_url"] == SRC
