"""Stage 1: ranked topic candidates with evidence (spec §7).

Sources: Reddit public JSON (no key), YouTube trending (uses YOUTUBE_API_KEY,
skipped if unset). TikTok Creative Center has no public API — paste those
topics manually via `pipeline run --topic`. See docs/setup.md.
"""

import os

import httpx
from pydantic import BaseModel

SUBREDDITS: tuple[str, ...] = ("ChatGPT", "ArtificialInteligence", "sidehustle")
USER_AGENT = "build-commons-pipeline/0.1 (trend research)"
COMMENT_WEIGHT = 2


class RedditPost(BaseModel):
    title: str
    score: int
    num_comments: int
    url: str
    subreddit: str


class TopicCandidate(BaseModel):
    topic: str
    evidence: str
    source: str
    score: float


def fetch_subreddit_top(
    subreddit: str, limit: int = 25, client: httpx.Client | None = None
) -> list[RedditPost]:
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20)
    resp = client.get(
        f"https://www.reddit.com/r/{subreddit}/top.json",
        params={"t": "week", "limit": limit},
    )
    resp.raise_for_status()
    children = resp.json().get("data", {}).get("children", [])
    return [
        RedditPost(
            title=c["data"]["title"],
            score=c["data"]["score"],
            num_comments=c["data"]["num_comments"],
            url=f"https://www.reddit.com{c['data']['permalink']}",
            subreddit=subreddit,
        )
        for c in children
    ]


def candidates_from_reddit(posts: list[RedditPost]) -> list[TopicCandidate]:
    return [
        TopicCandidate(
            topic=p.title,
            evidence=f"{p.score} upvotes, {p.num_comments} comments in r/{p.subreddit} ({p.url})",
            source=f"reddit:r/{p.subreddit}",
            score=float(p.score + COMMENT_WEIGHT * p.num_comments),
        )
        for p in posts
    ]


def fetch_youtube_trending(
    api_key: str, region: str = "US", client: httpx.Client | None = None
) -> list[TopicCandidate]:
    """Trending in Science & Tech (category 28). Optional — needs YOUTUBE_API_KEY."""
    client = client or httpx.Client(timeout=20)
    resp = client.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "videoCategoryId": "28",
            "regionCode": region,
            "maxResults": 25,
            "key": api_key,
        },
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        TopicCandidate(
            topic=item["snippet"]["title"],
            evidence=f"{item['statistics'].get('viewCount', '?')} views, YT trending #{i + 1}",
            source="youtube:trending",
            score=float(item["statistics"].get("viewCount", 0)),
        )
        for i, item in enumerate(items)
    ]


def rank_topics(candidates: list[TopicCandidate], top_n: int = 10) -> list[TopicCandidate]:
    """Dedupe (case-insensitive, keep best score) and sort descending."""
    best: dict[str, TopicCandidate] = {}
    for cand in candidates:
        key = cand.topic.strip().lower()
        if key not in best or cand.score > best[key].score:
            best[key] = cand
    return sorted(best.values(), key=lambda c: c.score, reverse=True)[:top_n]


def gather_candidates() -> list[TopicCandidate]:
    """All sources, ranked. Network failures in one source don't kill the run."""
    candidates: list[TopicCandidate] = []
    for sub in SUBREDDITS:
        try:
            candidates.extend(candidates_from_reddit(fetch_subreddit_top(sub)))
        except httpx.HTTPError as exc:
            print(f"[trend_scraper] r/{sub} failed: {exc}")
    yt_key = os.environ.get("YOUTUBE_API_KEY")
    if yt_key:
        try:
            candidates.extend(fetch_youtube_trending(yt_key))
        except httpx.HTTPError as exc:
            print(f"[trend_scraper] youtube trending failed: {exc}")
    return rank_topics(candidates)
