"""Stage 1: produce the VideoScript contract JSON (spec §6, §7)."""

import json
import re

from crewai import Agent, Task
from pydantic import ValidationError

from agents.llm import claude_llm
from schemas.video_script import VideoScript

HARD_CONSTRAINTS = """HARD CONSTRAINTS (violating any of these makes the output unusable):
- The hook must be speakable in at most 3 seconds.
- Deliver the payoff within the first 15 seconds.
- Exactly one idea per video. If a second idea appears, cut it.
- Plain language for a non-technical audience: no jargon, no acronyms without expansion.
- Target duration 30-60 seconds total."""

SCHEMA_GUIDE = """Output schema (respond with ONLY this JSON object, no commentary):
{
  "topic": str,
  "template": "explainer" | "tutorial" | "listicle" | "comparison",
  "hook": Segment,        // the provided hook, duration_estimate_s <= 3
  "segments": [Segment],  // 1-5 body segments (the contract enforces max 5)
  "cta": Segment,
  "target_duration_s": int (30-60),
  "platform_captions": {"youtube": str, "tiktok": str, "instagram": str},
  "hashtags": {"youtube": [str], "tiktok": [str], "instagram": [str]}
}
Segment = {
  "id": str (unique, e.g. "hook", "seg-1", "cta"),
  "text": str (the narration),
  "visual_type": "ai_broll" | "ai_image" | "screen_recording" | "text_card",
  "visual_prompt": str | null (REQUIRED for ai_broll/ai_image; detailed, cinematic),
  "duration_estimate_s": float,
  "caption_emphasis": [str] (words to highlight in captions)
}
visual_type selection guide:
- "text_card": hook and CTA default — needs no generated asset
- "screen_recording": workflow demos (operator records manually)
- "ai_image": static concept illustration (one Nano Banana call)
- "ai_broll": cinematic motion shot — use at most one per video (most expensive asset)
caption_emphasis: pick 1-3 words per segment that carry the payoff \
(verbs and numbers beat adjectives)."""


def build_script_prompt(topic: str, hook_text: str, template: str) -> str:
    return f"""You write scripts for short-form videos teaching practical AI workflows.

Topic: {topic}
Chosen hook (use verbatim as the hook segment text): {hook_text}
Template: {template}

{HARD_CONSTRAINTS}

{SCHEMA_GUIDE}"""


def parse_video_script(raw: str) -> VideoScript:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in model output: {raw[:200]!r}")
    try:
        return VideoScript.model_validate(json.loads(cleaned[start : end + 1]))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"model output failed VideoScript validation: {exc}") from exc


def build_script_agent() -> Agent:
    return Agent(
        role="Short-form script writer",
        goal="Turn a topic and hook into a tight 30-60s script that holds retention",
        backstory="Writes plainly, cuts ruthlessly, one idea per video.",
        llm=claude_llm(temperature=0.7),
        verbose=False,
    )


def generate_script(topic: str, hook_text: str, template: str = "explainer") -> VideoScript:
    agent = build_script_agent()
    task = Task(
        description=build_script_prompt(topic, hook_text, template),
        expected_output="A single VideoScript JSON object",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_video_script(result.raw)
