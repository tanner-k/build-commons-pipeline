"""Stage 6: weekly analytics scoring, hook promotion, template health (spec §7).

Usage:
    uv run python -m agents.analyst report
"""

import argparse
import datetime as dt
from pathlib import Path

from pydantic import BaseModel

from agents.db import get_client
from supabase import Client

# Success thresholds from spec §11.
HOLD_THRESHOLD = 0.70
COMPLETION_THRESHOLD = 0.40
DECLINE_RATIO = 0.90
MIN_HISTORY_POINTS = 3

Curve = list[dict]  # [{"t_s": float, "fraction": float}, ...] sorted by t_s


class VideoScore(BaseModel):
    video_id: str
    topic: str
    template: str | None
    hook: str | None
    hold_rate_3s: float | None
    completion_rate: float | None


def fraction_at(curve: Curve, t_s: float) -> float | None:
    """Linear interpolation of viewer fraction at time t; clamps to endpoints."""
    if not curve:
        return None
    points = sorted(curve, key=lambda p: p["t_s"])
    if t_s <= points[0]["t_s"]:
        return points[0]["fraction"]
    for prev, nxt in zip(points, points[1:], strict=False):
        if t_s <= nxt["t_s"]:
            span = nxt["t_s"] - prev["t_s"]
            if span == 0:
                return nxt["fraction"]
            ratio = (t_s - prev["t_s"]) / span
            return prev["fraction"] + ratio * (nxt["fraction"] - prev["fraction"])
    return points[-1]["fraction"]


def score_video(video_row: dict, retention_curve: Curve | None) -> VideoScore:
    """Score a single video using its retention curve."""
    curve = retention_curve or []
    return VideoScore(
        video_id=str(video_row["id"]),
        topic=video_row.get("topic") or "",
        template=video_row.get("template"),
        hook=video_row.get("hook"),
        hold_rate_3s=fraction_at(curve, 3.0),
        completion_rate=fraction_at(curve, float("inf")) if curve else None,
    )


def pick_promotable_hooks(scores: list[VideoScore]) -> list[dict]:
    """Winning hooks → taste_library rows. Closes the feedback loop."""
    rows = []
    for s in scores:
        if s.hook is None or s.hold_rate_3s is None or s.completion_rate is None:
            continue
        if s.hold_rate_3s >= HOLD_THRESHOLD and s.completion_rate >= COMPLETION_THRESHOLD:
            rows.append(
                {
                    "hook_text": s.hook,
                    "niche": "ai-tools",
                    "why_it_works": (
                        f"Promoted by analyst: 3s-hold {s.hold_rate_3s:.0%}, "
                        f"completion {s.completion_rate:.0%} on '{s.topic}'"
                    ),
                    "added_by": "analyst_agent",
                }
            )
    return rows


def flag_declining_templates(history: dict[str, list[float]]) -> list[str]:
    """Flag templates whose latest avg retention < 90% of the prior mean."""
    flagged = []
    for name, values in history.items():
        if len(values) < MIN_HISTORY_POINTS:
            continue
        prior = values[:-1]
        if values[-1] < DECLINE_RATIO * (sum(prior) / len(prior)):
            flagged.append(name)
    return sorted(flagged)


def render_weekly_report(
    scores: list[VideoScore], promotions: list[dict], flagged: list[str]
) -> str:
    """Render a markdown weekly report from scored videos, promotions, and flagged templates."""
    scored = [s for s in scores if s.hold_rate_3s is not None]
    winners = sorted(scored, key=lambda s: s.hold_rate_3s or 0, reverse=True)[:5]
    losers = sorted(scored, key=lambda s: s.hold_rate_3s or 0)[:5]

    def table(rows: list[VideoScore]) -> str:
        if not rows:
            return "_no scored videos this week_"
        lines = ["| Topic | Template | 3s hold | Completion |", "|---|---|---|---|"]
        lines += [
            f"| {s.topic} | {s.template or '-'} | "
            f"{s.hold_rate_3s:.0%} | {(s.completion_rate or 0):.0%} |"
            for s in rows
        ]
        return "\n".join(lines)

    promo_lines = "\n".join(f'- "{p["hook_text"]}" — {p["why_it_works"]}' for p in promotions)
    return f"""# Weekly Content Report — {dt.date.today().isoformat()}

## Make more of this (top 3s-hold)
{table(winners)}

## Kill / rework (bottom 3s-hold)
{table(losers)}

## Hooks promoted to taste library
{promo_lines or "_none met thresholds (hold >= 70%, completion >= 40%)_"}

## Template health
{("Flagged for rebuild: " + ", ".join(flagged)) if flagged else "All templates healthy."}
"""


def run_weekly(client: Client | None = None, reports_dir: Path | None = None) -> Path:
    """Fetch last week's data, score, promote, flag, write the report. Returns report path.

    TODO: decline detection needs multi-week history of templates.avg_retention snapshots;
    flag_declining_templates is wired and unit-tested, but fed flagged=[] here until several
    weeks of data exist. See TODO.md for the tracking item.
    """
    client = client or get_client()
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=7)).isoformat()

    videos = (
        client.table("videos")
        .select("id,topic,template,hook")
        .eq("status", "published")
        .execute()
    ).data
    analytics = (
        client.table("analytics")
        .select("video_id,retention_curve,captured_at")
        .gte("captured_at", since)
        .execute()
    ).data

    latest_curve: dict[str, Curve] = {}
    for row in sorted(analytics, key=lambda r: r["captured_at"]):
        if row.get("retention_curve"):
            latest_curve[str(row["video_id"])] = row["retention_curve"]

    scores = [score_video(v, latest_curve.get(str(v["id"]))) for v in videos]
    promotions = pick_promotable_hooks(scores)
    if promotions:
        client.table("taste_library").insert(promotions).execute()

    # Template health: avg retention per template from this week's scores.
    by_template: dict[str, list[float]] = {}
    for s in scores:
        if s.template and s.completion_rate is not None:
            by_template.setdefault(s.template, []).append(s.completion_rate)
    for name, values in by_template.items():
        avg = sum(values) / len(values)
        client.table("templates").update({"avg_retention": avg}).eq("name", name).execute()

    # flag_declining_templates wired here once multi-week snapshots exist (see run_weekly docstring)
    report = render_weekly_report(scores, promotions, flagged=[])
    reports_dir = reports_dir or Path(__file__).parent.parent / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{dt.date.today().isoformat()}-weekly.md"
    path.write_text(report)
    print(f"[analyst] wrote {path}")
    return path


def main() -> None:
    """CLI entry point for the analyst agent."""
    parser = argparse.ArgumentParser(prog="agents.analyst")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="run the weekly scoring + report")
    args = parser.parse_args()
    if args.command == "report":
        run_weekly()


if __name__ == "__main__":
    main()
