"""Integration contracts for PyTorch-KR records in the research collector."""

import json

from src.tools.research_collector import _fetch_top_candidates, _normalize_candidates, _run_searches


def test_run_searches_routes_pytorch_kr_envelope_to_community_category(monkeypatch):
    def fake_search_pytorch_kr_forum(publication_date):
        return json.dumps({
            "publication_date": publication_date,
            "posts": [{
                "title": "Forum Item",
                "forum_url": "https://discuss.pytorch.kr/t/forum-item/1",
                "original_url": "https://github.com/example/project",
                "content": "첫 문단\n\n둘째 문단",
                "published_at": "2026-06-12",
                "tags": ["llm", "agent"],
            }],
        })

    monkeypatch.setattr(
        "src.tools.research_collector.search_pytorch_kr_forum",
        fake_search_pytorch_kr_forum,
    )

    raw_results, errors = _run_searches(
        [{"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None}],
        "2026-06-17",
    )

    assert errors == []
    assert raw_results == [{
        "category": "pytorch_kr_community",
        "tool": "pytorch_kr",
        "query": None,
        "items": [{
            "title": "Forum Item",
            "forum_url": "https://discuss.pytorch.kr/t/forum-item/1",
            "original_url": "https://github.com/example/project",
            "content": "첫 문단\n\n둘째 문단",
            "published_at": "2026-06-12",
            "tags": ["llm", "agent"],
        }],
    }]


def test_run_searches_prefixes_pytorch_kr_envelope_errors_and_keeps_raw_items(monkeypatch):
    def fake_search_pytorch_kr_forum(publication_date):
        return json.dumps({
            "publication_date": publication_date,
            "posts": [],
            "errors": ["forum backend unavailable"],
        })

    monkeypatch.setattr(
        "src.tools.research_collector.search_pytorch_kr_forum",
        fake_search_pytorch_kr_forum,
    )

    raw_results, errors = _run_searches(
        [{"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None}],
        "2026-06-17",
    )

    assert errors == ["pytorch_kr_community/pytorch_kr: forum backend unavailable"]
    assert raw_results[0]["items"] == []


def test_run_searches_isolates_malformed_pytorch_kr_response(monkeypatch):
    monkeypatch.setattr(
        "src.tools.research_collector.search_pytorch_kr_forum",
        lambda publication_date: "not valid json",
    )

    raw_results, errors = _run_searches(
        [{"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None}],
        "2026-06-17",
    )

    assert raw_results[0]["items"] == []
    assert len(errors) == 1
    assert errors[0].startswith("pytorch_kr_community/pytorch_kr:")


def test_normalize_candidates_preserves_forum_context_and_primary_source():
    candidates = _normalize_candidates([{
        "category": "pytorch_kr_community",
        "tool": "pytorch_kr",
        "query": None,
        "items": [{
            "title": "Forum Item",
            "forum_url": "https://discuss.pytorch.kr/t/forum-item/1",
            "original_url": "https://github.com/example/project",
            "content": "첫 문단\n\n둘째 문단",
            "published_at": "2026-06-12",
            "tags": ["llm", "agent"],
        }],
    }])

    assert candidates == [{
        "title": "Forum Item",
        "url": "https://discuss.pytorch.kr/t/forum-item/1",
        "original_url": "https://github.com/example/project",
        "source": "discuss.pytorch.kr",
        "published_at": "2026-06-12",
        "summary": "첫 문단\n\n둘째 문단",
        "prefetched_content": "첫 문단\n\n둘째 문단",
        "key_facts": [],
        "why_it_matters": "",
        "topic_type": "main",
        "category": "pytorch_kr_community",
        "score": 0.0,
        "fetched": False,
    }]


def test_fetch_top_candidates_uses_prefetched_forum_excerpt_without_refetching(monkeypatch):
    forum_url = "https://discuss.pytorch.kr/t/forum-item/1"
    candidates = [
        {
            "title": "Forum Item",
            "url": forum_url,
            "prefetched_content": "첫 문단\n\n둘째 문단",
            "fetched": False,
        },
        {"title": "Other", "url": "https://example.com/other", "fetched": False},
    ]
    calls = []

    def fake_fetch_article_content(url):
        calls.append(url)
        return json.dumps({"content": "other content"})

    monkeypatch.setattr("src.tools.research_collector.fetch_article_content", fake_fetch_article_content)

    fetched_content = _fetch_top_candidates(candidates, max_fetches=1, max_chars_per_source=8)

    assert fetched_content == {forum_url: "첫 문단\n\n둘째"}
    assert candidates[0]["fetched"] is True
    assert calls == []
