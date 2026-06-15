"""Supabase access for agents. Every function takes an injectable client for testing."""

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel

from schemas.video_script import VideoScript
from supabase import Client, create_client

if TYPE_CHECKING:
    from schemas.enhancement import EnhancementPlan


class TasteExample(BaseModel):
    hook_text: str
    hook_type: str | None = None
    why_it_works: str | None = None


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def insert_scripted_video(script: VideoScript, client: Client | None = None) -> str:
    """Insert a Stage-1 result as status=scripted. Returns the new video id."""
    client = client or get_client()
    row = {
        "status": "scripted",
        "template": script.template,
        "topic": script.topic,
        "hook": script.hook.text,
        "script_json": script.model_dump(mode="json"),
    }
    result = client.table("videos").insert(row).execute()
    if not result.data:
        raise RuntimeError(f"Supabase insert returned no data for topic {script.topic!r}")
    return result.data[0]["id"]


def top_taste_hooks(limit: int = 20, client: Client | None = None) -> list[TasteExample]:
    """Top hooks by views — few-shot examples for the hook writer (spec §7 Stage 1)."""
    client = client or get_client()
    result = (
        client.table("taste_library")
        .select("hook_text,hook_type,why_it_works")
        .not_.is_("hook_text", "null")
        .order("views", desc=True)
        .limit(limit)
        .execute()
    )
    return [TasteExample.model_validate(r) for r in result.data]


def insert_enhanced_video(
    plan: "EnhancementPlan", transcript: list[dict], client: Client | None = None
) -> str:
    """Insert an enhance-track row at status=plan_ready. Returns the new video id."""
    client = client or get_client()
    captions = plan.platform_captions
    # Title for the publish/QA lists. Prefer the YouTube caption, else any caption.
    topic = captions.get("youtube") or next(iter(captions.values()), "Enhanced video")
    row = {
        "kind": "enhanced",
        "status": "plan_ready",
        "topic": topic,
        "source_video_url": plan.source_video_url,
        "transcript": transcript,
        "enhancement_json": plan.model_dump(mode="json"),
        # publish.json reads captions/hashtags from script_json — mirror them here so the
        # existing publish workflow serves enhanced rows unchanged (spec: zero publish changes).
        "script_json": {
            "platform_captions": captions,
            "hashtags": plan.hashtags,
        },
    }
    result = client.table("videos").insert(row).execute()
    if not result.data:
        raise RuntimeError("Supabase insert returned no data for enhanced video")
    return result.data[0]["id"]


def set_video_status(video_id: str, status: str, client: Client | None = None) -> None:
    """Move a video to a new status (e.g. plan_approved)."""
    client = client or get_client()
    result = client.table("videos").update({"status": status}).eq("id", video_id).execute()
    if not result.data:
        raise RuntimeError(f"no video found with id {video_id!r}")
