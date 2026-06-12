"""Stage-1 CLI: topic → hooks → script → videos row (status=scripted).

Usage:
    uv run python -m agents.pipeline run --topic "..."   # manual topic (e.g. TikTok CC)
    uv run python -m agents.pipeline run                  # auto: top trend candidate
    uv run python -m agents.pipeline trends               # just print ranked candidates
"""

import argparse

from agents.db import get_client, insert_scripted_video, top_taste_hooks
from agents.hook_writer import generate_hooks
from agents.script_writer import generate_script
from agents.trend_scraper import gather_candidates


def run_stage1(topic: str | None = None, template: str = "explainer") -> str:
    client = get_client()
    if topic is None:
        candidates = gather_candidates()
        if not candidates:
            raise RuntimeError("no trend candidates found and no --topic given")
        topic = candidates[0].topic
        print(f"[pipeline] auto-selected topic: {topic}")

    examples = top_taste_hooks(client=client)
    hooks = generate_hooks(topic, examples)
    print("[pipeline] hook variants:")
    for i, hook in enumerate(hooks, 1):
        print(f"  {i}. ({hook.hook_type}) {hook.text}")

    script = generate_script(topic, hooks[0].text, template)
    video_id = insert_scripted_video(script, client=client)
    print(f"[pipeline] inserted video {video_id} (status=scripted)")
    return video_id


def main() -> None:
    parser = argparse.ArgumentParser(prog="agents.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="full Stage 1: topic -> scripted row")
    run.add_argument("--topic", default=None, help="manual topic (else top trend)")
    run.add_argument(
        "--template",
        default="explainer",
        choices=["explainer", "tutorial", "listicle", "comparison"],
    )

    sub.add_parser("trends", help="print ranked topic candidates")

    args = parser.parse_args()
    if args.command == "run":
        run_stage1(args.topic, args.template)
    elif args.command == "trends":
        for cand in gather_candidates():
            print(f"{cand.score:>10.0f}  {cand.topic}  [{cand.source}]")


if __name__ == "__main__":
    main()
