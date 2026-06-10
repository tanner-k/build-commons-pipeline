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
