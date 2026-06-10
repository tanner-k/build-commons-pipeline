# schemas/

Pydantic models — the pipeline contract (spec §6). `video_script.py` is the source of truth; `remotion/src/types/video-script.ts` mirrors it with zod. `fixtures/sample_video_script.json` is validated by BOTH sides (pytest + vitest) — change all three together.
