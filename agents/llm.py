"""Single LLM config point — all agent work runs on Claude (spec §3: one tool per job)."""

import os

from crewai import LLM

DEFAULT_MODEL = "claude-sonnet-4-6"


def claude_llm(temperature: float = 0.7) -> LLM:
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    return LLM(model=f"anthropic/{model}", temperature=temperature)
