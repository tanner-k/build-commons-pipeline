"""Stage: raw video -> reviewable EnhancementPlan, then approval (spec §Data flow).

CLI:
    uv run python -m agents.enhance plan --video <supabase_url> [--local <path>]
    uv run python -m agents.enhance approve --id <video_id>

Pure functions (prompt/parse/summary) are unit-tested. The Claude call and DB
writes are thin boundaries.
"""

import argparse
import json
import re
from pathlib import Path

from crewai import Agent, Task
from pydantic import ValidationError

from agents.db import get_client, insert_enhanced_video, set_video_status
from agents.llm import claude_llm
from agents.transcribe import format_for_prompt, total_duration_s, transcribe
from schemas.enhancement import EnhancementPlan

HARD_CONSTRAINTS = """HARD CONSTRAINTS (violating any makes the plan unusable):
- Suggest 3-8 overlays. Each overlay has a start_s and end_s within the video length.
- Overlays MUST NOT overlap in time. Leave the speaker on screen between overlays.
- Choose placement per overlay: "fullframe" (cutaway covering the picture) or "pip"
  (corner box while the speaker keeps talking). B-roll and screen recordings are
  usually fullframe; diagrams/stills and text effects are usually pip.
- type is one of: ai_broll (generated motion b-roll), ai_image (generated still),
  screen_recording (the creator records their real screen — you only LABEL it),
  text_effect (an on-screen text callout).
- ai_broll/ai_image MUST include a detailed cinematic "prompt" and null "text".
- screen_recording/text_effect MUST include "text" (the label/words) and null "prompt".
- Every overlay needs a one-line "rationale" tied to what is being said at that moment.
- Anchor each overlay to the transcript timestamps — enhance the actual claims, not filler."""

SCHEMA_GUIDE = """Respond with ONLY this JSON object (no commentary):
{
  "overlays": [
    {"id": "ov-1", "start_s": float, "end_s": float,
     "type": "ai_broll|ai_image|screen_recording|text_effect",
     "placement": "fullframe|pip",
     "prompt": str|null, "text": str|null,
     "rationale": str, "asset_url": null}
  ],
  "platform_captions": {"youtube": str, "tiktok": str, "instagram": str},
  "hashtags": {"youtube": [str], "tiktok": [str], "instagram": [str]}
}"""


def build_enhancement_prompt(transcript_text: str, duration_s: float) -> str:
    return f"""You are a short-form video editor. A creator recorded a {duration_s:.0f}-second \
talking-head video explaining a project. Below is the timestamped transcript. Propose timed \
visual overlays that make it more engaging and clearer, anchored to what is said.

Transcript:
{transcript_text}

{HARD_CONSTRAINTS}

{SCHEMA_GUIDE}"""


def _extract_json_object(raw: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in model output: {raw[:200]!r}")
    return cleaned[start : end + 1]


def parse_enhancement_plan(
    raw: str, source_video_url: str, source_duration_s: float
) -> EnhancementPlan:
    """Parse the LLM's {overlays, captions, hashtags} and inject the known source fields."""
    try:
        data = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"model output was not valid JSON: {exc}") from exc
    data["source_video_url"] = source_video_url
    data["source_duration_s"] = source_duration_s
    try:
        return EnhancementPlan.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"model output failed EnhancementPlan validation: {exc}") from exc


def render_plan_summary(plan: EnhancementPlan) -> str:
    """Human-readable review of the plan (printed at the checkpoint)."""
    lines = [
        "# Enhancement plan",
        f"Source: {plan.source_video_url} ({plan.source_duration_s:.0f}s)",
        f"{len(plan.overlays)} overlay(s):",
        "",
    ]
    for o in plan.sorted_overlays():
        detail = o.prompt or o.text or ""
        flag = "  ⚠ SCREEN REC — record + swap in CapCut" if o.type == "screen_recording" else ""
        lines.append(
            f"- [{o.start_s:.1f}-{o.end_s:.1f}s] {o.id} · {o.type} · {o.placement} — "
            f"{detail}  ({o.rationale}){flag}"
        )
    return "\n".join(lines)


def build_enhance_agent() -> Agent:
    return Agent(
        role="Short-form video editor",
        goal="Suggest timed visual overlays that sharpen a talking-head explainer",
        backstory="Edits founder and developer videos; knows when a cutaway earns attention.",
        llm=claude_llm(temperature=0.6),
        verbose=False,
    )


def generate_enhancement_plan(
    transcript_text: str, source_duration_s: float, source_video_url: str
) -> EnhancementPlan:
    agent = build_enhance_agent()
    task = Task(
        description=build_enhancement_prompt(transcript_text, source_duration_s),
        expected_output="A single JSON object of overlays + captions + hashtags",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_enhancement_plan(result.raw, source_video_url, source_duration_s)


def run_plan(video_url: str, local_path: str | None = None) -> str:
    """Transcribe + analyze a raw video, insert a plan_ready row, print the summary."""
    source = Path(local_path) if local_path else None
    if source is None:
        raise RuntimeError("pass --local <downloaded path> for transcription in v1")
    segments = transcribe(source)
    transcript_text = format_for_prompt(segments)
    duration = total_duration_s(segments)
    plan = generate_enhancement_plan(transcript_text, duration, video_url)
    video_id = insert_enhanced_video(
        plan=plan,
        transcript=[s.model_dump(mode="json") for s in segments],
        client=get_client(),
    )
    print(render_plan_summary(plan))
    print(f"\n[enhance] inserted video {video_id} (status=plan_ready)")
    print(f"[enhance] approve with: uv run python -m agents.enhance approve --id {video_id}")
    return video_id


def run_approve(video_id: str) -> None:
    set_video_status(video_id, "plan_approved", client=get_client())
    print(f"[enhance] video {video_id} -> plan_approved (n8n will generate overlays + render)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents.enhance")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="raw video -> reviewable overlay plan")
    plan.add_argument("--video", required=True, help="Supabase URL stored on the row")
    plan.add_argument("--local", default=None, help="local file path to transcribe")
    appr = sub.add_parser("approve", help="approve a plan_ready video")
    appr.add_argument("--id", required=True)
    args = parser.parse_args()
    if args.command == "plan":
        run_plan(args.video, args.local)
    elif args.command == "approve":
        run_approve(args.id)


if __name__ == "__main__":
    main()
