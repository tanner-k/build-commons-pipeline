# Setup Guide

## 1. Accounts & keys (spec §3 — one tool per job)

| Service | Job | Action |
|---|---|---|
| Anthropic API | All LLM work | Create key → `ANTHROPIC_API_KEY` |
| ElevenLabs (Creator) | Voiceover only | Clone OWN voice; keep consent recording; `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| Google AI Studio | All AI visuals (Nano Banana images, Veo 3.1 b-roll) | `GOOGLE_AI_STUDIO_API_KEY` |
| Supabase | State + storage | Project URL + service-role key; create buckets `assets`, `renders` |
| YouTube Data API v3 | Upload + analytics | OAuth client + `YOUTUBE_API_KEY` |
| TikTok Content Posting API | Upload | **Apply Week 1** — approval takes days–weeks |
| Instagram Graph API | Reels | Business/Creator account + Meta app — **apply Week 1** |
| CapCut Pro | Manual polish (Stage 4) | Account only, no API |

Do NOT set up: Canva, Descript, Kling, Ollama-in-pipeline, OpusClip (deliberately cut — spec §3).
Set a **$120/mo budget alert** across providers (spec §10).

## 2. Local environment

```bash
brew install ffmpeg
cp .env.example .env   # fill in keys
uv sync
cd remotion && npm install
```

## 3. Database

Run `supabase/migrations/0001_init.sql` in the Supabase SQL editor (or `supabase db push`).
Create public storage buckets `assets` and `renders`.

## 4. n8n (Docker on the Mac mini)

```bash
docker volume create n8n_data
docker run -d --restart unless-stopped --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE="America/Denver" \
  n8nio/n8n
```

Then in the n8n UI (http://localhost:5678): import the three files from `n8n/workflows/`,
attach credentials (Postgres → Supabase connection string; header auth for ElevenLabs
`xi-api-key`; query auth `key` for Google AI Studio; YouTube OAuth2), and activate.
The render server is reachable from Docker at `http://host.docker.internal:3333`.

### Phase-3 wiring checklist (n8n UI work — the committed JSONs are skeletons)

The exported workflows import cleanly but are NOT functional end-to-end until these are
wired in the n8n UI (intentional: credentials and response-shape mapping live in n8n):

- [ ] **Asset-URL assembly** — collect ElevenLabs/Nano Banana/Veo responses, upload binaries
      to the `assets` bucket, and build the unified `asset_urls` jsonb (incl. word timestamps
      under `timings`) before the `Save asset_urls` write. Today each provider branch
      triggers the save node independently with a partial payload.
- [ ] **Hook + CTA voiceover** — `Split segments` only splits `script_json.segments`; the
      `hook` and `cta` segments are separate top-level fields and need TTS too (the hook is
      the highest-leverage audio — captions sync from its timestamps).
- [ ] **Filter providers by visual_type** — only `ai_image` segments go to Nano Banana and
      only `ai_broll` to Veo (add an If/Switch node; today every segment hits every provider).
- [ ] **YouTube upload binary** — the YouTube node needs a preceding HTTP node downloading
      `render_url` as binary; TikTok/IG pull from URL, YouTube does not.
- [ ] **platform_ids assembly** — add Merge + Set nodes collecting the three platform
      response IDs into one object before `Mark published`.
- [ ] **Platform stagger** — Wait nodes (1–2h) between platforms (spec §7 Stage 5).
- [ ] **YouTube AI-disclosure flag** — set for videos containing AI b-roll (spec §10).
- [ ] **TikTok + IG analytics** — analytics.json only ingests YouTube today; add the other
      two platforms' analytics calls in Phase 3 (schema already supports them). Also extend
      the YouTube query to ingest retention curve + CTR (only views/duration/likes/shares now).

## 5. Render server

```bash
cd remotion && npm run serve     # listens on :3333
curl -s localhost:3333/healthz   # {"ok":true}
```

The endpoint has no auth — it must stay bound to localhost / the Docker bridge.
Never port-forward or expose :3333 beyond the machine.

## 6. Stage 1 (research → scripted row)

```bash
uv run python -m agents.pipeline trends                  # see ranked candidates
uv run python -m agents.pipeline run                     # auto top candidate
uv run python -m agents.pipeline run --topic "..."       # manual (e.g. TikTok Creative Center find)
```

TikTok Creative Center has no public API — browse it manually and feed winners in
via `--topic`.

Note: Reddit rate-limits unknown user agents aggressively. If `pipeline trends` starts
returning 429s, set a personalized UA (reddit format: `platform:app:version (by /u/you)`)
in `agents/trend_scraper.py:USER_AGENT`.

## 7. Taste library seeding (do not skip — spec §9 Phase 2)

Watch 50 top videos in the niche, annotate each (~3–4 hrs total):

```sql
insert into taste_library (source_url, niche, hook_text, hook_type, why_it_works, views, added_by)
values ('https://...', 'ai-tools', 'You''re using ChatGPT wrong.', 'bold_claim',
        'Confrontational pattern interrupt; implies secret knowledge', 2400000, 'manual');
```

## 8. Stage 4 — human quality gate (~15 min/video)

For each `qa_pending` row: watch the render, then:
1. Hook lands in 3s? Rewrite if weak — highest-leverage edit.
2. No AI artifacts (garbled visual text, voice glitches, caption desync).
3. Factually correct.
4. Pacing — trim dead air in CapCut; trending audio bed where appropriate.
5. Thumbnail strong? Regenerate headline/base only if weak.

Approve: `update videos set status='approved' where id='...';`
Reject: `update videos set status='rejected', qa_notes='...' where id='...';`

## 9. Weekly analyst run

```bash
uv run python -m agents.analyst report   # writes docs/reports/YYYY-MM-DD-weekly.md
```

Schedule it (e.g. Sunday 7am) via launchd or an n8n Execute Command node.

## Enhance track (auto-composite a talking-head video)

1. Apply migration `supabase/migrations/0002_enhancement.sql` (adds `kind`, `source_video_url`, `transcript`, `enhancement_json` + the `uploaded`/`plan_ready`/`plan_approved` statuses).
2. First run downloads a Whisper model (~150 MB) to cache; subsequent runs are offline.
3. `uv run python -m agents.enhance plan --video <url> --local <path>` → review the printed plan → `... approve --id <id>`.
4. Phase-3 n8n wiring for `enhance.json`: map each generated overlay asset back into `enhancement_json.overlays[].asset_url` before the `Save overlay asset_urls` write (the committed workflow is a skeleton, same as generate/publish). Screen-recording and text_effect overlays need no generated asset.
