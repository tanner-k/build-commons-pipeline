from unittest.mock import MagicMock

import pytest

from agents.analyst import (
    COMPLETION_THRESHOLD,
    HOLD_THRESHOLD,
    VideoScore,
    flag_declining_templates,
    fraction_at,
    pick_promotable_hooks,
    render_weekly_report,
    run_weekly,
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


class TestRunWeekly:
    def _mock_client(self) -> tuple[MagicMock, dict[str, MagicMock]]:
        table_names = ("videos", "analytics", "taste_library", "templates")
        tables = {name: MagicMock() for name in table_names}
        videos_result = MagicMock()
        videos_result.data = [
            {"id": "v1", "topic": "PDF workflow", "template": "explainer", "hook": "Stop doing X."}
        ]
        analytics_result = MagicMock()
        analytics_result.data = [
            {"video_id": "v1", "retention_curve": CURVE, "captured_at": "2026-06-10T00:00:00Z"}
        ]
        tables["videos"].select.return_value.eq.return_value.execute.return_value = videos_result
        tables["analytics"].select.return_value.gte.return_value.execute.return_value = (
            analytics_result
        )
        client = MagicMock()
        client.table.side_effect = lambda name: tables[name]
        return client, tables

    def test_promotes_winners_via_upsert_and_writes_report(self, tmp_path):
        client, tables = self._mock_client()

        report_path = run_weekly(client=client, reports_dir=tmp_path)

        # CURVE gives hold 0.82 and completion 0.45 — above both thresholds.
        tables["taste_library"].upsert.assert_called_once()
        rows, kwargs = (
            tables["taste_library"].upsert.call_args.args,
            tables["taste_library"].upsert.call_args.kwargs,
        )
        assert rows[0][0]["hook_text"] == "Stop doing X."
        assert rows[0][0]["added_by"] == "analyst_agent"
        assert kwargs.get("on_conflict") == "hook_text"

        tables["templates"].update.assert_called_once_with({"avg_retention": 0.45})

        assert report_path.exists()
        content = report_path.read_text()
        assert "Stop doing X." in content
        assert "PDF workflow" in content
