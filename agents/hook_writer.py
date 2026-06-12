"""Stage 1: 5 hook variants per topic, few-shot from the taste library (spec §7)."""

import json
import re
from typing import Literal

from crewai import Agent, Task
from pydantic import BaseModel, ValidationError

from agents.db import TasteExample
from agents.llm import claude_llm

HOOK_COUNT = 5


class HookVariant(BaseModel):
    text: str
    hook_type: Literal["question", "bold_claim", "curiosity_gap", "demo"]


def build_hook_prompt(topic: str, examples: list[TasteExample]) -> str:
    example_block = (
        "\n".join(
            f'- "{e.hook_text}" ({e.hook_type or "unknown"}) — {e.why_it_works or "n/a"}'
            for e in examples
        )
        or "- (taste library is empty — rely on the hook types below)"
    )
    return f"""You write 3-second hooks for short-form videos teaching practical AI \
workflows to a non-technical audience.

Topic: {topic}

Hooks that performed well in this niche (steal the *patterns*, never the words):
{example_block}

Write exactly {HOOK_COUNT} hook variants. Mix hook types across: question, bold_claim, \
curiosity_gap, demo. Each must be speakable in under 3 seconds (strictly 12 words or \
fewer), concrete, and free of hype adjectives (no "insane", "incredible", "wild", \
"mind-blowing", "game-changer", or anything in that register). Use each hook_type at \
least once across the {HOOK_COUNT} variants.

Respond with ONLY a JSON array:
[{{"text": "...", "hook_type": "question|bold_claim|curiosity_gap|demo"}}]"""


def _extract_json_array(raw: str) -> str:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON array found in model output: {raw[:200]!r}")
    return cleaned[start : end + 1]


def parse_hook_variants(raw: str) -> list[HookVariant]:
    try:
        items = json.loads(_extract_json_array(raw))
        return [HookVariant.model_validate(item) for item in items]
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"could not parse hook variants: {exc}") from exc


def build_hook_agent() -> Agent:
    return Agent(
        role="Short-form hook writer",
        goal="Write scroll-stopping 3-second hooks that earn the next 15 seconds",
        backstory="Studied thousands of top-performing shorts in the AI-tools niche.",
        llm=claude_llm(temperature=0.9),
        verbose=False,
    )


def generate_hooks(topic: str, examples: list[TasteExample]) -> list[HookVariant]:
    agent = build_hook_agent()
    task = Task(
        description=build_hook_prompt(topic, examples),
        expected_output="A JSON array of 5 hook variants",
        agent=agent,
    )
    result = task.execute_sync(agent=agent)
    return parse_hook_variants(result.raw)
