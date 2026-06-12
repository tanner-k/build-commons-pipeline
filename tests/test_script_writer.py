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
