import httpx
import pytest

from agents.trend_scraper import (
    RedditPost,
    TopicCandidate,
    candidates_from_reddit,
    fetch_subreddit_top,
    rank_topics,
)


def make_candidate(topic: str, score: float) -> TopicCandidate:
    return TopicCandidate(topic=topic, evidence="e", source="reddit:r/ChatGPT", score=score)


class TestRankTopics:
    def test_sorts_by_score_descending(self):
        ranked = rank_topics([make_candidate("a", 1.0), make_candidate("b", 5.0)])
        assert [c.topic for c in ranked] == ["b", "a"]

    def test_dedupes_case_insensitively_keeping_higher_score(self):
        ranked = rank_topics([make_candidate("AI tools", 2.0), make_candidate("ai tools", 9.0)])
        assert len(ranked) == 1
        assert ranked[0].score == 9.0

    def test_respects_top_n(self):
        cands = [make_candidate(f"t{i}", float(i)) for i in range(20)]
        assert len(rank_topics(cands, top_n=5)) == 5


class TestCandidatesFromReddit:
    def test_maps_posts_to_candidates(self):
        posts = [
            RedditPost(
                title="I automated my whole job with Claude",
                score=900,
                num_comments=150,
                url="https://reddit.com/x",
                subreddit="ChatGPT",
            )
        ]
        (cand,) = candidates_from_reddit(posts)
        assert cand.topic == "I automated my whole job with Claude"
        assert cand.source == "reddit:r/ChatGPT"
        assert cand.score == 900 + 2 * 150
        assert "900" in cand.evidence


class TestFetchSubredditTop:
    def test_parses_listing_json(self):
        listing = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "t",
                            "score": 10,
                            "num_comments": 3,
                            "permalink": "/r/ChatGPT/comments/abc/t/",
                        }
                    }
                ]
            }
        }
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=listing))
        client = httpx.Client(transport=transport)
        posts = fetch_subreddit_top("ChatGPT", client=client)
        assert posts == [
            RedditPost(
                title="t",
                score=10,
                num_comments=3,
                url="https://www.reddit.com/r/ChatGPT/comments/abc/t/",
                subreddit="ChatGPT",
            )
        ]

    def test_raises_on_http_error(self):
        transport = httpx.MockTransport(lambda req: httpx.Response(503))
        client = httpx.Client(transport=transport)
        with pytest.raises(httpx.HTTPStatusError):
            fetch_subreddit_top("ChatGPT", client=client)
