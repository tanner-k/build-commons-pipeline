# 0001 — Initial stack

**Status:** Accepted
**Date:** 2026-06-10

## Context
Day-one decision: pick the stack for build-commons-pipeline.

## Decision
- **Frontend (rendering):** Remotion 4 + React 18 + TypeScript (remotion/)
- **Backend (agents):** Python 3.12 + uv + CrewAI + Pydantic v2 (agents/, schemas/)
- **Data:** Supabase Postgres + Storage
- **Infra:** n8n self-hosted (Docker, Mac mini M4); renders local
- **Package manager:** npm (remotion/) · uv (python)
- **Node version:** 20

## Rationale
One tool per job (spec §3): Claude for all LLM work, Remotion for all branded rendering, n8n for plumbing only, Supabase for state+storage. Deliberately cut: Canva, Descript, Kling, Ollama-in-pipeline, OpusClip.

## Consequences
- (positive) Each layer has a clear owner and boundary; no overlapping services doing the same job
- (tradeoff) Two language runtimes (Python + Node) require separate install steps and CI jobs
- (followup) ADRs 0002+ will refine specific library versions and composition choices within this stack

## Alternatives considered
- All-Node pipeline (Langchain.js): rejected — Python/CrewAI ecosystem for agents is more mature and better supported
- Canva API for rendering: rejected — insufficient programmatic control over brand elements; Remotion gives full React flexibility
- Kling/Runway for video gen: rejected — spec §3 calls for one tool per job; Veo 3.1 via Google AI Studio covers b-roll
- Ollama for local LLM: rejected — spec §3 mandates Claude for consistency and quality; local models add complexity without benefit at this scale
