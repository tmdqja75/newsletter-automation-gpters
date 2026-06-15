"""Tests for the compact deterministic research collector."""

import json

from src.tools.research_collector import (
    RESEARCH_QUERY_PLAN,
    _build_query_plan,
    _run_searches,
    _normalize_candidates,
    _dedupe_candidates,
    _date_filter,
    _rank_and_truncate,
    _fetch_top_candidates,
    _summarize_candidates,
    _persist_artifacts,
)


EXPECTED_CATEGORIES = {
    "model_releases",
    "agents_automation",
    "research_papers",
    "tools_infra",
    "industry_business",
    "policy_society",
    "study_resources",
    "real_world_usecases",
    "official_blogs",
}


def test_query_plan_covers_all_categories():
    categories = {entry["category"] for entry in RESEARCH_QUERY_PLAN}
    assert categories == EXPECTED_CATEGORIES


def test_build_query_plan_fills_placeholders():
    plan = _build_query_plan("2026-06-17")
    by_category: dict[str, list[dict]] = {}
    for entry in plan:
        by_category.setdefault(entry["category"], []).append(entry)

    # Korean date-based query for model_releases
    korean_query = next(
        e["query"] for e in by_category["model_releases"] if "년" in (e["query"] or "")
    )
    assert "2026년 6월" in korean_query

    # English month name substitution
    english_query = next(
        e["query"] for e in by_category["model_releases"] if "년" not in (e["query"] or "")
    )
    assert "June 2026" in english_query

    # HN queries have no placeholders, pass through unchanged
    hn_entry = next(e for e in by_category["agents_automation"] if e["tool"] == "hn")
    assert hn_entry["query"] == "AI agent"

    # official_blogs has no query
    blog_entry = by_category["official_blogs"][0]
    assert blog_entry["query"] is None


def test_run_searches_collects_items_and_tags_category(monkeypatch):
    def fake_search_ai_news(query, max_results=10, article_date=None):
        return json.dumps([
            {"title": "Tavily result", "url": "https://example.com/a", "content": "snippet", "score": 0.9}
        ])

    def fake_search_hackernews(query, num_results=10, publication_date=None):
        return json.dumps([
            {"title": "HN result", "url": "https://example.com/b",
             "hn_url": "https://news.ycombinator.com/item?id=1",
             "points": 80, "num_comments": 10, "author": "x",
             "created_at": "2026-06-10T00:00:00.000Z"}
        ])

    def fake_fetch_official_blog_posts(publication_date):
        return json.dumps({
            "publication_date": publication_date,
            "date_range": {"start": "2026-06-10", "end": "2026-06-17"},
            "posts": {
                "openai": [{"source": "openai", "title": "Blog post", "url": "https://openai.com/news/x",
                             "date": "2026-06-12", "category": "Research", "description": "desc"}],
                "anthropic": [],
                "deepmind": [],
            },
            "total_count": 1,
        })

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", fake_search_ai_news)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", fake_search_hackernews)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", fake_fetch_official_blog_posts)

    plan = _build_query_plan("2026-06-17")
    raw_results, errors = _run_searches(plan, "2026-06-17")

    assert errors == []
    tavily_entries = [r for r in raw_results if r["tool"] == "tavily"]
    assert tavily_entries and all(r["items"] for r in tavily_entries)
    hn_entries = [r for r in raw_results if r["tool"] == "hn"]
    assert hn_entries and all(r["items"] for r in hn_entries)
    blog_entries = [r for r in raw_results if r["tool"] == "blog"]
    assert len(blog_entries) == 1
    assert blog_entries[0]["items"][0]["title"] == "Blog post"


def test_run_searches_captures_errors_without_raising(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", boom)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", boom)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", boom)

    plan = _build_query_plan("2026-06-17")
    raw_results, errors = _run_searches(plan, "2026-06-17")

    assert len(errors) == len(plan)
    assert all(r["items"] == [] for r in raw_results)


def test_normalize_candidates_handles_tavily_hn_blog():
    raw_results = [
        {
            "category": "model_releases", "tool": "tavily", "query": "...",
            "items": [{"title": "Tavily Item", "url": "https://news.example.com/a",
                       "content": "snippet", "score": 0.75}],
        },
        {
            "category": "real_world_usecases", "tool": "hn", "query": "Show HN AI agent",
            "items": [{"title": "HN Item", "url": "https://maker.example.com/b",
                       "hn_url": "https://news.ycombinator.com/item?id=123",
                       "points": 80, "num_comments": 30, "author": "dev",
                       "created_at": "2026-06-10T12:00:00.000Z"}],
        },
        {
            "category": "official_blogs", "tool": "blog", "query": None,
            "items": [{"source": "openai", "title": "Blog Item", "url": "https://openai.com/news/c",
                       "date": "2026-06-12", "category": "Research", "description": "blog desc"}],
        },
    ]

    candidates = _normalize_candidates(raw_results)
    assert len(candidates) == 3

    tavily_c = next(c for c in candidates if c["title"] == "Tavily Item")
    assert tavily_c["source"] == "news.example.com"
    assert tavily_c["published_at"] is None
    # tavily_score (0.75) - 0.5 (missing published_at) = 0.25
    assert tavily_c["score"] == 0.25
    assert tavily_c["topic_type"] == "main"
    assert tavily_c["fetched"] is False

    hn_c = next(c for c in candidates if c["title"] == "HN Item")
    assert hn_c["published_at"] == "2026-06-10"
    assert hn_c["source"] == "maker.example.com"
    # HN points>50 (+0.2) + real_world_usecases (+0.3) = 0.5
    assert hn_c["score"] == 0.5
    assert "news.ycombinator.com" in hn_c["summary"]

    blog_c = next(c for c in candidates if c["title"] == "Blog Item")
    assert blog_c["source"] == "openai"
    assert blog_c["published_at"] == "2026-06-12"
    assert blog_c["topic_type"] == "main"
    assert blog_c["score"] == 0.0


def test_normalize_candidates_study_resources_topic_type():
    raw_results = [
        {
            "category": "study_resources", "tool": "tavily", "query": "...",
            "items": [{"title": "Tutorial", "url": "https://example.com/tut",
                       "content": "snippet", "score": 0.5}],
        },
    ]

    candidates = _normalize_candidates(raw_results)
    assert candidates[0]["topic_type"] == "study_cafe"


def test_normalize_candidates_skips_missing_url_or_title():
    raw_results = [
        {"category": "model_releases", "tool": "tavily", "query": "...",
         "items": [{"title": "", "url": "https://example.com", "content": "x", "score": 0.5}]},
        {"category": "model_releases", "tool": "tavily", "query": "...",
         "items": [{"title": "No URL", "url": "", "content": "x", "score": 0.5}]},
    ]

    candidates = _normalize_candidates(raw_results)
    assert candidates == []


def test_dedupe_candidates_by_url_and_title():
    candidates = [
        {"title": "Same Title", "url": "https://example.com/page?utm_source=x", "score": 0.5},
        {"title": "Same Title", "url": "https://example.com/page", "score": 0.9},
        {"title": "Different", "url": "https://example.com/other", "score": 0.3},
        {"title": "different", "url": "https://example.com/another", "score": 0.7},
    ]

    result = _dedupe_candidates(candidates)

    assert len(result) == 2

    same_title = next(c for c in result if c["title"] == "Same Title")
    assert same_title["score"] == 0.9
    assert same_title["url"] == "https://example.com/page"

    other = next(c for c in result if c["title"] != "Same Title")
    assert other["score"] == 0.7
    assert other["url"] == "https://example.com/another"


def test_date_filter_drops_out_of_window_and_keeps_undated():
    candidates = [
        {"title": "In window", "url": "https://example.com/in", "published_at": "2026-06-10", "score": 1.0},
        {"title": "Too old", "url": "https://example.com/old", "published_at": "2026-05-01", "score": 1.0},
        {"title": "Future", "url": "https://example.com/future", "published_at": "2026-06-20", "score": 1.0},
        {"title": "Undated", "url": "https://example.com/undated", "published_at": None, "score": -0.5},
        {"title": "Boundary start", "url": "https://example.com/start", "published_at": "2026-06-03", "score": 1.0},
        {"title": "Boundary end", "url": "https://example.com/end", "published_at": "2026-06-17", "score": 1.0},
    ]

    result = _date_filter(candidates, "2026-06-17")
    titles = {c["title"] for c in result}

    assert "In window" in titles
    assert "Undated" in titles
    assert "Boundary start" in titles
    assert "Boundary end" in titles
    assert "Too old" not in titles
    assert "Future" not in titles


def test_rank_and_truncate_sorts_by_score_and_limits():
    candidates = [
        {"title": "Low", "score": 0.1},
        {"title": "High", "score": 0.9},
        {"title": "Mid", "score": 0.5},
    ]

    result = _rank_and_truncate(candidates, max_search_results=2)

    assert [c["title"] for c in result] == ["High", "Mid"]


def test_fetch_top_candidates_limits_and_truncates(monkeypatch):
    candidates = [
        {"title": f"T{i}", "url": f"https://example.com/{i}", "source": "example.com",
         "published_at": "2026-06-10", "summary": "snippet", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "model_releases",
         "score": 1.0, "fetched": False}
        for i in range(5)
    ]

    calls = []

    def fake_fetch_article_content(url):
        calls.append(url)
        return json.dumps({"url": url, "domain": "example.com", "title": "T",
                            "description": "", "content": "x" * 100})

    monkeypatch.setattr("src.tools.research_collector.fetch_article_content", fake_fetch_article_content)

    fetched_content = _fetch_top_candidates(candidates, max_fetches=2, max_chars_per_source=10)

    assert calls == ["https://example.com/0", "https://example.com/1"]
    assert all(len(content) == 10 for content in fetched_content.values())
    assert candidates[0]["fetched"] is True
    assert candidates[1]["fetched"] is True
    assert candidates[2]["fetched"] is False


def test_fetch_top_candidates_handles_failure(monkeypatch):
    candidates = [
        {"title": "T0", "url": "https://example.com/0", "source": "example.com",
         "published_at": "2026-06-10", "summary": "snippet", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "model_releases",
         "score": 1.0, "fetched": False},
    ]

    def fake_fetch_article_content(url):
        return json.dumps({"error": "boom", "url": url})

    monkeypatch.setattr("src.tools.research_collector.fetch_article_content", fake_fetch_article_content)

    fetched_content = _fetch_top_candidates(candidates, max_fetches=2, max_chars_per_source=10)

    assert fetched_content == {}
    assert candidates[0]["fetched"] is False


def test_summarize_candidates_merges_enrichment_by_url():
    candidates = [
        {"title": "A", "url": "https://example.com/a", "source": "example.com",
         "published_at": "2026-06-10", "summary": "snippet a", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "model_releases",
         "score": 1.0, "fetched": True},
        {"title": "B", "url": "https://example.com/b", "source": "example.com",
         "published_at": None, "summary": "snippet b", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "tools_infra",
         "score": -0.5, "fetched": False},
    ]
    fetched_content = {"https://example.com/a": "full content a"}

    def fake_summarizer(items):
        assert items == [{"url": "https://example.com/a", "title": "A",
                           "source": "example.com", "content": "full content a"}]
        return [{"url": "https://example.com/a", "summary": "요약 A", "key_facts": ["fact1"],
                 "why_it_matters": "중요함", "topic_type": "main"}]

    errors = _summarize_candidates(candidates, fetched_content, fake_summarizer)

    assert errors == []
    assert candidates[0]["summary"] == "요약 A"
    assert candidates[0]["key_facts"] == ["fact1"]
    assert candidates[0]["why_it_matters"] == "중요함"
    assert candidates[1]["summary"] == "snippet b"  # unfetched candidate untouched


def test_summarize_candidates_falls_back_on_summarizer_error():
    candidates = [
        {"title": "A", "url": "https://example.com/a", "source": "example.com",
         "published_at": "2026-06-10", "summary": "snippet a", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "model_releases",
         "score": 1.0, "fetched": True},
    ]
    fetched_content = {"https://example.com/a": "full content a"}

    def broken_summarizer(items):
        raise RuntimeError("model unavailable")

    errors = _summarize_candidates(candidates, fetched_content, broken_summarizer)

    assert any("summarizer" in e for e in errors)
    assert candidates[0]["summary"] == "full content a"[:200]
    assert candidates[0]["key_facts"] == []


def test_summarize_candidates_noop_when_nothing_fetched():
    candidates = [
        {"title": "A", "url": "https://example.com/a", "source": "example.com",
         "published_at": None, "summary": "snippet a", "key_facts": [],
         "why_it_matters": "", "topic_type": "main", "category": "model_releases",
         "score": -0.5, "fetched": False},
    ]

    errors = _summarize_candidates(candidates, {}, lambda items: [])

    assert errors == []
    assert candidates[0]["summary"] == "snippet a"


def test_persist_artifacts_writes_expected_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    raw_results = [{"category": "model_releases", "tool": "tavily", "query": "q", "items": []}]
    candidates = [{"title": "A", "url": "https://example.com/a", "score": 1.0}]

    errors = _persist_artifacts("2026-06-17", raw_results, candidates)

    assert errors == []

    artifacts_dir = tmp_path / "artifacts" / "research" / "2026-06-17"
    raw_path = artifacts_dir / "raw_search_results.json"
    candidates_path = artifacts_dir / "candidates.json"

    assert raw_path.exists()
    assert candidates_path.exists()

    saved_raw = json.loads(raw_path.read_text(encoding="utf-8"))
    saved_candidates = json.loads(candidates_path.read_text(encoding="utf-8"))

    assert saved_raw == raw_results
    assert saved_candidates == candidates
