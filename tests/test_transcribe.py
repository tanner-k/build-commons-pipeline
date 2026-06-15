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
