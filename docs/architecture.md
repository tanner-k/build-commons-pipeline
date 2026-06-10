# Architecture — build-commons-pipeline

## One-line
Semi-automated short-form video pipeline with closed analytics feedback loop

## System diagram
```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  agents/         │ ───▶ │  schemas/         │ ───▶ │  supabase/       │
│  CrewAI + Python │      │  Pydantic + zod   │      │  Postgres + Stor.│
└──────────────────┘      └──────────────────┘      └──────────────────┘
         │                                                    ▲
         ▼                                                    │
┌──────────────────┐      ┌──────────────────┐               │
│  remotion/       │ ───▶ │  n8n/            │ ──────────────┘
│  React + ffmpeg  │      │  Orchestration   │
└──────────────────┘      └──────────────────┘
```

> Replace this ASCII sketch with a real diagram (Excalidraw, Mermaid, etc.) once the shape settles.

## Components

### agents/
Python 3.12 · uv · CrewAI · Pydantic v2 · Claude. See [`../agents/context.md`](../agents/context.md).

### schemas/
Pydantic `VideoScript` contract (source of truth) + zod mirror in remotion/. See [`../schemas/context.md`](../schemas/context.md).

### remotion/
Remotion 4 + React 18 + TypeScript (remotion/). See [`../remotion/context.md`](../remotion/context.md).

### supabase/
Supabase Postgres + Storage. See [`../supabase/context.md`](../supabase/context.md).

### n8n/
n8n self-hosted (Docker, Mac mini M4); renders local. See [`../n8n/context.md`](../n8n/context.md).

## Decisions
See [`./decisions/`](./decisions/) for the running ADR log.

## Open questions
- (Track unresolved design questions here. Move to an ADR once decided.)
