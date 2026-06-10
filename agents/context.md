# agents/

CrewAI agents (spec §7 Stage 1 + Stage 6). All LLM calls go through `llm.py` (Claude via CrewAI/LiteLLM; model from $ANTHROPIC_MODEL). All DB access through `db.py`. Prompt builders and output parsers are pure functions — tested without network. `pipeline.py` is the Stage-1 CLI; `analyst.py` is the weekly Stage-6 run.
