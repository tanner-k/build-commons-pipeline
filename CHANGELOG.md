# Changelog

> Shipped work, newest first. Promoted from `TODO.md` via `python3 scripts/done.py "description"`.

## Conventions
1. Group by date (ISO `YYYY-MM-DD`).
2. Each entry = one shipped change, written in past tense.
3. The top 5 entries get pulled into `README.md`'s "Recent updates" section (between the `<!-- BEGIN:RECENT-UPDATES -->` / `<!-- END:RECENT-UPDATES -->` markers).
4. Never edit historical entries — append a follow-up entry instead.

<!-- Newest first -->

## 2026-06-12
- Shipped n8n workflow skeletons (generate/publish/analytics) with retry policy and structural tests
- Shipped analyst agent: retention scoring, idempotent hook promotion, weekly markdown report
- Wrote setup guide (accounts, n8n Phase-3 wiring checklist) and architecture map

## 2026-06-11
- Shipped Explainer/Listicle compositions + branded Thumbnail still with word-synced captions
- Shipped Express render server: POST /render renders video+thumbnail, compresses, updates Supabase
- Shipped Stage-1 CrewAI agents (trends, hooks, script) + pipeline CLI

## 2026-06-10
- Shipped VideoScript contract (Pydantic + zod mirror + shared fixtures) and Supabase schema
- Scaffolded project from the Tree template
