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
