"""Supabase access for agents. Every function takes an injectable client for testing."""

import os

from pydantic import BaseModel

from schemas.video_script import VideoScript
from supabase import Client, create_client


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
