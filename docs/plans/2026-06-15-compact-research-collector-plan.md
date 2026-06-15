# Compact Deterministic Research Collector — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add a deterministic, Python-controlled `collect_weekly_research()` pipeline that the `research-agent` calls first, replacing its open-ended search/fetch loop while preserving the existing `research_results.md` output format.

**Architecture:** New module `src/tools/research_collector.py` implements a pure pipeline (`_collect_weekly_research_core`) — search 9 categories via existing `search_ai_news`/`search_hackernews`/`fetch_official_blog_posts`, normalize, dedupe, date-filter, rank/truncate, fetch top-N via `fetch_article_content`, batch-summarize via an injectable `summarizer` (default: `RESEARCH_COLLECTOR_MODEL`), persist artifacts under `artifacts/research/{date}/`, and return a compact `ResearchCandidate` list. A thin `@tool`-style wrapper `collect_weekly_research()` returns this as JSON. `research_subagent`'s tools become `[collect_weekly_research, fetch_article_content]`, and `RESEARCH_AGENT_PROMPT` is rewritten to a 3-step collect → optionally verify → write report flow.

**Tech Stack:** Python 3.12, `uv`, `pytest`, `langchain` (`init_chat_model`), existing `httpx`/`tavily`/`bs4` tools.

**Design spec:** `docs/superpowers/specs/2026-06-15-compact-research-collector-design.md`

---

## Task 1: Add `to_model_spec` helper + `RESEARCH_COLLECTOR_MODEL` config

**Objective:** Introduce a shared helper for converting bare model names to provider-prefixed specs, and a new env-configurable model for the research collector's summarizer.

**Files:**
- Modify: `src/config.py` (after `MODEL_NAME` definition, around line 13)
- Test: `tests/test_config.py` (new)

**Step 1: Write failing test**

Create `tests/test_config.py`:

```python
"""Tests for model spec configuration helpers."""

from src.config import to_model_spec


def test_to_model_spec_adds_anthropic_prefix():
    assert to_model_spec("claude-haiku-4-5") == "anthropic:claude-haiku-4-5"


def test_to_model_spec_preserves_existing_prefix():
    assert to_model_spec("openai:gpt-5-mini") == "openai:gpt-5-mini"


def test_to_model_spec_strips_whitespace():
    assert to_model_spec("  claude-haiku-4-5  ") == "anthropic:claude-haiku-4-5"
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'to_model_spec'`

**Step 3: Write minimal implementation**

In `src/config.py`, after the `MODEL_NAME` line (currently line 13):

```python
# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

# Cheap/fast model used by collect_weekly_research for batch summarization.
RESEARCH_COLLECTOR_MODEL = os.getenv("RESEARCH_COLLECTOR_MODEL", "claude-haiku-4-5")


def to_model_spec(model_name: str) -> str:
    """Convert a bare model name into a DeepAgents-compatible model spec.

    Names without a provider prefix (no ':') are assumed to be Anthropic
    models and get an "anthropic:" prefix. Names that already include a
    provider prefix (e.g. "openai:gpt-5-mini") are returned unchanged.
    """
    name = model_name.strip()
    if ":" in name:
        return name
    return f"anthropic:{name}"
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (3 passed)

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add to_model_spec helper and RESEARCH_COLLECTOR_MODEL"
```

---

## Task 2: Refactor `_agent_model_spec` to use `to_model_spec`

**Objective:** Remove duplicated prefix logic from `src/main.py` by delegating to `to_model_spec`.

**Files:**
- Modify: `src/main.py:15-32`

**Step 1: Update the import**

In `src/main.py`, change:

```python
from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
)
```

to:

```python
from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    to_model_spec,
)
```

**Step 2: Simplify `_agent_model_spec`**

Replace:

```python
def _agent_model_spec() -> str:
    """Return a DeepAgents-compatible model spec from MODEL_NAME."""
    model_name = MODEL_NAME.strip()
    if ":" in model_name:
        return model_name
    return f"anthropic:{model_name}"
```

with:

```python
def _agent_model_spec() -> str:
    """Return a DeepAgents-compatible model spec from MODEL_NAME."""
    return to_model_spec(MODEL_NAME)
```

**Step 3: Run existing Phase 1 tests to verify no regression**

Run: `uv run pytest tests/test_phase1_cost_controls.py -v`
Expected: PASS (4 passed) — `monkeypatch.setattr("src.main.MODEL_NAME", ...)` still works because `_agent_model_spec` reads the module-level `MODEL_NAME` name in `src.main`'s namespace.

**Step 4: Commit**

```bash
git add src/main.py
git commit -m "refactor(main): use shared to_model_spec helper"
```

---

## Task 3: Create `research_collector.py` skeleton with query plan

**Objective:** Create the new module with imports, the `RESEARCH_QUERY_PLAN` constant (9 categories), and `_build_query_plan()` for filling date placeholders.

**Files:**
- Create: `src/tools/research_collector.py`
- Test: `tests/test_research_collector.py` (new)

**Step 1: Write failing test**

Create `tests/test_research_collector.py`:

```python
"""Tests for the compact deterministic research collector."""

import json

from src.tools.research_collector import (
    RESEARCH_QUERY_PLAN,
    _build_query_plan,
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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.tools.research_collector'`

**Step 3: Write minimal implementation**

Create `src/tools/research_collector.py`:

```python
"""Compact deterministic research collector for newsletter generation.

Replaces the open-ended research-agent search/fetch loop with a single
Python-controlled pipeline: search a fixed set of categories, normalize,
deduplicate, date-filter, rank, fetch top candidates, batch-summarize via a
cheap model, persist artifacts, and return a compact candidate list.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .search_tools import search_ai_news, search_hackernews
from .content_tools import fetch_article_content, fetch_official_blog_posts


_MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Maps research categories to the topic_type assigned during normalization.
# Categories not listed here default to "main". The batch summarizer may
# override topic_type per candidate based on actual content.
CATEGORY_TOPIC_TYPE: dict[str, str] = {
    "study_resources": "study_cafe",
}
DEFAULT_TOPIC_TYPE = "main"

# Query plan derived from the 8 categories in RESEARCH_AGENT_PROMPT, plus a
# 9th "official_blogs" source-routing category. {year}/{month}/{month_en}
# placeholders are filled by _build_query_plan() from publication_date.
RESEARCH_QUERY_PLAN: list[dict] = [
    {"category": "model_releases", "tool": "tavily", "query": "{year}년 {month}월 AI 모델 출시"},
    {"category": "model_releases", "tool": "tavily", "query": "{month_en} {year} new LLM model release"},
    {"category": "agents_automation", "tool": "hn", "query": "AI agent"},
    {"category": "agents_automation", "tool": "tavily", "query": "{year}년 {month}월 AI 에이전트 자동화"},
    {"category": "research_papers", "tool": "tavily", "query": "arXiv AI agent {month_en} {year}"},
    {"category": "tools_infra", "tool": "tavily", "query": "{month_en} {year} AI developer tools"},
    {"category": "industry_business", "tool": "tavily", "query": "{year}년 {month}월 AI 스타트업 산업 동향"},
    {"category": "policy_society", "tool": "tavily", "query": "{month_en} {year} AI policy regulation"},
    {"category": "study_resources", "tool": "tavily", "query": "{month_en} {year} AI agent tutorial course"},
    {"category": "real_world_usecases", "tool": "hn", "query": "Show HN AI agent"},
    {"category": "real_world_usecases", "tool": "tavily", "query": '"AI agent" deployed production results {year}'},
    {"category": "official_blogs", "tool": "blog", "query": None},
]


def _build_query_plan(publication_date: str) -> list[dict]:
    """Fill {year}/{month}/{month_en} placeholders in RESEARCH_QUERY_PLAN."""
    pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
    fmt_kwargs = {
        "year": pub_date.year,
        "month": pub_date.month,
        "month_en": _MONTH_NAMES_EN[pub_date.month - 1],
    }

    plan = []
    for entry in RESEARCH_QUERY_PLAN:
        query = entry["query"]
        if query is not None:
            query = query.format(**fmt_kwargs)
        plan.append({"category": entry["category"], "tool": entry["tool"], "query": query})
    return plan
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (2 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): add research collector query plan"
```

---

## Task 4: Implement `_run_searches`

**Objective:** Execute the query plan via existing search/fetch tools, tagging results by category and collecting errors without raising.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _run_searches


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_run_searches'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _run_searches(query_plan: list[dict], publication_date: str) -> tuple[list[dict], list[str]]:
    """Execute the query plan and return (raw_results, errors).

    Each raw result is a dict: {"category", "tool", "query", "items"}.
    Per-query failures are captured in errors; that query's items become [].
    """
    raw_results: list[dict] = []
    errors: list[str] = []

    for entry in query_plan:
        category = entry["category"]
        tool = entry["tool"]
        query = entry["query"]
        items: list[dict] = []

        try:
            if tool == "tavily":
                parsed = json.loads(search_ai_news(query, max_results=6, article_date=publication_date))
                if isinstance(parsed, dict) and "error" in parsed:
                    errors.append(f"{category}/{tool}: {parsed['error']}")
                else:
                    items = parsed
            elif tool == "hn":
                parsed = json.loads(search_hackernews(query, num_results=6, publication_date=publication_date))
                if isinstance(parsed, dict) and "error" in parsed:
                    errors.append(f"{category}/{tool}: {parsed['error']}")
                else:
                    items = parsed
            elif tool == "blog":
                blog_result = json.loads(fetch_official_blog_posts(publication_date))
                for blog_error in blog_result.get("errors", []):
                    errors.append(f"official_blogs: {blog_error}")
                items = [
                    post
                    for source_posts in blog_result.get("posts", {}).values()
                    for post in source_posts
                ]
        except Exception as exc:
            errors.append(f"{category}/{tool}: {exc}")
            items = []

        raw_results.append({"category": category, "tool": tool, "query": query, "items": items})

    return raw_results, errors
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (4 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): add deterministic search runner"
```

---

## Task 5: Implement `_normalize_candidates`

**Objective:** Convert raw search results into preliminary `ResearchCandidate` dicts with scoring bonuses applied.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _normalize_candidates


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_normalize_candidates'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _parse_hn_date(created_at: str) -> str | None:
    """Parse HN's ISO8601 created_at into YYYY-MM-DD, or None if unparseable."""
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError, TypeError):
        return None


def _normalize_candidates(raw_results: list[dict]) -> list[dict]:
    """Convert raw search results into preliminary ResearchCandidate dicts.

    Applies the ranking-score formula at normalization time:
        score = tavily_score (0 for HN/blog)
              + 0.3 if category == "real_world_usecases"
              + 0.2 if this is an HN result with points > 50
              - 0.5 if published_at is missing/unparseable
    """
    candidates: list[dict] = []

    for result in raw_results:
        category = result["category"]
        tool = result["tool"]
        topic_type = CATEGORY_TOPIC_TYPE.get(category, DEFAULT_TOPIC_TYPE)

        for item in result["items"]:
            if tool == "tavily":
                url = item.get("url", "")
                title = item.get("title", "")
                published_at = None
                score = float(item.get("score", 0) or 0)
                summary = item.get("content", "")
                source = urlparse(url).netloc
            elif tool == "hn":
                url = item.get("url") or item.get("hn_url", "")
                title = item.get("title", "")
                published_at = _parse_hn_date(item.get("created_at", ""))
                points = item.get("points", 0) or 0
                score = 0.2 if points > 50 else 0.0
                hn_url = item.get("hn_url", "")
                summary = f"HN 토론: {hn_url} (points: {points}, comments: {item.get('num_comments', 0)})"
                source = urlparse(url).netloc or "news.ycombinator.com"
            elif tool == "blog":
                url = item.get("url", "")
                title = item.get("title", "")
                published_at = item.get("date")
                score = 0.0
                summary = item.get("description", "")
                source = item.get("source") or urlparse(url).netloc
            else:
                continue

            if not url or not title:
                continue

            if category == "real_world_usecases":
                score += 0.3
            if not published_at:
                score -= 0.5

            candidates.append({
                "title": title,
                "url": url,
                "source": source,
                "published_at": published_at,
                "summary": summary,
                "key_facts": [],
                "why_it_matters": "",
                "topic_type": topic_type,
                "category": category,
                "score": round(score, 3),
                "fetched": False,
            })

    return candidates
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (7 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): normalize raw results into ResearchCandidate dicts"
```

---

## Task 6: Implement `_canonical_url`, `_normalize_title`, `_dedupe_candidates`

**Objective:** Deduplicate candidates by canonical URL and normalized title, keeping the higher-scored duplicate.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _dedupe_candidates


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_dedupe_candidates'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _canonical_url(url: str) -> str:
    """Normalize a URL for deduplication: strip query/fragment, lowercase host, drop trailing slash."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"


def _normalize_title(title: str) -> str:
    """Normalize a title for deduplication: lowercase, strip punctuation, collapse whitespace."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    """Deduplicate candidates by canonical URL, then by normalized title.

    When duplicates are found, keep the one with the higher score.
    """
    best_by_url: dict[str, dict] = {}
    for candidate in candidates:
        key = _canonical_url(candidate["url"])
        existing = best_by_url.get(key)
        if existing is None or candidate["score"] > existing["score"]:
            best_by_url[key] = candidate

    best_by_title: dict[str, dict] = {}
    for candidate in best_by_url.values():
        key = _normalize_title(candidate["title"])
        existing = best_by_title.get(key)
        if existing is None or candidate["score"] > existing["score"]:
            best_by_title[key] = candidate

    return list(best_by_title.values())
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (8 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): dedupe candidates by URL and title"
```

---

## Task 7: Implement `_date_filter`

**Objective:** Drop candidates whose parseable `published_at` falls outside `[publication_date - 14d, publication_date]`; keep undated candidates.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _date_filter


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_date_filter'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _date_filter(candidates: list[dict], publication_date: str) -> list[dict]:
    """Drop candidates whose parseable published_at falls outside
    [publication_date - 14 days, publication_date].

    Candidates with no parseable published_at are kept (already
    score-penalized during normalization).
    """
    pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
    window_start = pub_date - timedelta(days=14)

    filtered = []
    for candidate in candidates:
        published_at = candidate.get("published_at")
        if not published_at:
            filtered.append(candidate)
            continue
        try:
            dt = datetime.strptime(published_at, "%Y-%m-%d")
        except ValueError:
            filtered.append(candidate)
            continue
        if window_start <= dt <= pub_date:
            filtered.append(candidate)

    return filtered
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (9 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): filter candidates by publication date window"
```

---

## Task 8: Implement `_rank_and_truncate`

**Objective:** Sort candidates by score (descending) and truncate to `max_search_results`.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _rank_and_truncate


def test_rank_and_truncate_sorts_by_score_and_limits():
    candidates = [
        {"title": "Low", "score": 0.1},
        {"title": "High", "score": 0.9},
        {"title": "Mid", "score": 0.5},
    ]

    result = _rank_and_truncate(candidates, max_search_results=2)

    assert [c["title"] for c in result] == ["High", "Mid"]
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_rank_and_truncate'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _rank_and_truncate(candidates: list[dict], max_search_results: int) -> list[dict]:
    """Sort candidates by score (descending) and truncate to max_search_results."""
    ranked = sorted(candidates, key=lambda c: c["score"], reverse=True)
    return ranked[:max_search_results]
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (10 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): rank candidates by score and truncate"
```

---

## Task 9: Implement `_fetch_top_candidates`

**Objective:** Fetch full content for the top `max_fetches` candidates via `fetch_article_content`, truncate to `max_chars_per_source`, and mark `fetched`.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _fetch_top_candidates


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_fetch_top_candidates'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _fetch_top_candidates(candidates: list[dict], max_fetches: int, max_chars_per_source: int) -> dict[str, str]:
    """Fetch full content for the top max_fetches candidates (already ranked).

    Mutates each successfully-fetched candidate's "fetched" flag to True.
    Returns a dict mapping candidate URL -> truncated fetched content, for
    candidates that were fetched successfully.
    """
    fetched_content: dict[str, str] = {}

    for candidate in candidates[:max_fetches]:
        try:
            result = json.loads(fetch_article_content(candidate["url"]))
        except Exception:
            continue

        if "error" in result:
            continue

        content = result.get("content", "")
        if not content:
            continue

        fetched_content[candidate["url"]] = content[:max_chars_per_source]
        candidate["fetched"] = True

    return fetched_content
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (12 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): fetch and truncate top-ranked candidates"
```

---

## Task 10: Implement batch summarizer (`_default_summarizer`, `_summarize_candidates`)

**Objective:** Add the injectable batch-summarization step: one LLM call enriches all fetched candidates with `summary`/`key_facts`/`why_it_matters`/`topic_type`, falling back to snippet-based fields on any failure.

**Files:**
- Modify: `pyproject.toml` (add explicit `langchain` dependency)
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Add explicit `langchain` dependency**

`langchain` (v1.3.5) is already installed transitively via `deepagents`, but `research_collector.py` now imports `langchain.chat_models.init_chat_model` directly, so declare it explicitly in `pyproject.toml`'s `dependencies` list (after `"deepagents>=0.1.0"`):

```toml
dependencies = [
    "deepagents>=0.1.0",
    "langchain>=1.0.0",
    "tavily-python>=0.5.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "headroom-ai[langchain]>=0.22.2",
]
```

Run: `uv sync`
Expected: resolves successfully (no version conflicts — `langchain==1.3.5` already satisfies `>=1.0.0`).

**Step 2: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _summarize_candidates


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
```

**Step 3: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_summarize_candidates'`

**Step 4: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
SUMMARIZER_SYSTEM_PROMPT = """당신은 AI 뉴스 리서치 보조입니다. 주어진 각 기사에 대해 다음 정보를 JSON 배열로 반환하세요:
- url: 기사 URL (입력과 동일하게 유지)
- summary: 2-3문장 한국어 요약
- key_facts: 핵심 사실 목록 (문자열 배열, 최대 5개)
- why_it_matters: 이 소식이 왜 중요한지 1-2문장 설명
- topic_type: "main" 또는 "study_cafe" 중 하나 (학습 자료/튜토리얼이면 study_cafe)

반드시 유효한 JSON 배열만 반환하세요. 다른 텍스트를 포함하지 마세요.
"""


def _default_summarizer(items: list[dict]) -> list[dict]:
    """Summarize fetched candidates in a single batch LLM call.

    Args:
        items: list of {"url", "title", "source", "content"} dicts.

    Returns:
        List of {"url", "summary", "key_facts", "why_it_matters", "topic_type"}
        dicts. Returns [] on any error (caller applies snippet fallback).
    """
    from langchain.chat_models import init_chat_model
    from .. import config

    try:
        model = init_chat_model(config.to_model_spec(config.RESEARCH_COLLECTOR_MODEL))
        response = model.invoke([
            {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ])
        text = response.content if hasattr(response, "content") else str(response)
        return json.loads(text)
    except Exception:
        return []


def _summarize_candidates(candidates: list[dict], fetched_content: dict[str, str], summarizer) -> list[str]:
    """Enrich fetched candidates in place via the summarizer.

    Non-fetched candidates are left untouched (they keep their
    snippet-based summary from normalization). Returns a list of error
    messages (empty on full success).
    """
    if not fetched_content:
        return []

    by_url = {c["url"]: c for c in candidates}
    items = [
        {"url": url, "title": by_url[url]["title"], "source": by_url[url]["source"], "content": content}
        for url, content in fetched_content.items()
        if url in by_url
    ]

    errors: list[str] = []
    try:
        enrichments = summarizer(items)
    except Exception as exc:
        enrichments = []
        errors.append(f"summarizer: {exc}")

    enrichment_by_url = {
        e["url"]: e for e in enrichments if isinstance(e, dict) and "url" in e
    } if isinstance(enrichments, list) else {}

    if not enrichment_by_url:
        errors.append("summarizer: no valid enrichment returned, using snippet fallback")

    for candidate in candidates:
        url = candidate["url"]
        if url not in fetched_content:
            continue

        enrichment = enrichment_by_url.get(url)
        if enrichment:
            candidate["summary"] = enrichment.get("summary", candidate["summary"])
            candidate["key_facts"] = enrichment.get("key_facts", [])
            candidate["why_it_matters"] = enrichment.get("why_it_matters", "")
            candidate["topic_type"] = enrichment.get("topic_type", candidate["topic_type"])
        else:
            candidate["summary"] = fetched_content[url][:200]
            candidate["key_facts"] = []
            candidate["why_it_matters"] = ""

    return errors
```

**Step 5: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (15 passed)

**Step 6: Commit**

```bash
git add pyproject.toml src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): add batch summarizer with snippet fallback"
```

---

## Task 11: Implement `_persist_artifacts`

**Objective:** Persist `raw_search_results.json` and `candidates.json` under `artifacts/research/{publication_date}/`.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _persist_artifacts


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
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_persist_artifacts'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _persist_artifacts(publication_date: str, raw_results: list[dict], candidates: list[dict]) -> list[str]:
    """Write raw_search_results.json and candidates.json under
    artifacts/research/{publication_date}/.

    Returns a list of error messages (empty on success). Never raises.
    """
    errors: list[str] = []
    artifacts_dir = Path("artifacts") / "research" / publication_date

    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [f"artifacts: failed to create directory: {exc}"]

    for filename, data in (
        ("raw_search_results.json", raw_results),
        ("candidates.json", candidates),
    ):
        try:
            (artifacts_dir / filename).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            errors.append(f"artifacts: failed to write {filename}: {exc}")

    return errors
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (16 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): persist research artifacts to disk"
```

---

## Task 12: Implement `_collect_weekly_research_core` and `collect_weekly_research`

**Objective:** Wire all pipeline steps together into the core function and the JSON-returning tool wrapper, with full top-level error handling.

**Files:**
- Modify: `src/tools/research_collector.py` (append)
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
from src.tools.research_collector import _collect_weekly_research_core, collect_weekly_research


def test_collect_weekly_research_core_returns_envelope(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def fake_search_ai_news(query, max_results=10, article_date=None):
        return json.dumps([
            {"title": "AI News", "url": "https://example.com/news", "content": "snippet", "score": 0.8}
        ])

    def fake_search_hackernews(query, num_results=10, publication_date=None):
        return json.dumps([])

    def fake_fetch_official_blog_posts(publication_date):
        return json.dumps({
            "publication_date": publication_date,
            "date_range": {"start": "2026-06-03", "end": "2026-06-17"},
            "posts": {"openai": [], "anthropic": [], "deepmind": []},
            "total_count": 0,
        })

    def fake_fetch_article_content(url):
        return json.dumps({"url": url, "domain": "example.com", "title": "AI News",
                            "description": "", "content": "full content " * 50})

    def fake_summarizer(items):
        return [
            {"url": item["url"], "summary": "요약", "key_facts": ["fact"],
             "why_it_matters": "중요", "topic_type": "main"}
            for item in items
        ]

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", fake_search_ai_news)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", fake_search_hackernews)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", fake_fetch_official_blog_posts)
    monkeypatch.setattr("src.tools.research_collector.fetch_article_content", fake_fetch_article_content)

    result = _collect_weekly_research_core("2026-06-17", summarizer=fake_summarizer)

    assert result["publication_date"] == "2026-06-17"
    assert result["total_found"] > 0
    assert result["total_fetched"] > 0
    assert result["candidates"][0]["summary"] == "요약"

    artifacts_dir = tmp_path / "artifacts" / "research" / "2026-06-17"
    assert (artifacts_dir / "raw_search_results.json").exists()
    assert (artifacts_dir / "candidates.json").exists()


def test_collect_weekly_research_wrapper_returns_valid_json_on_search_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", boom)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", boom)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", boom)

    output = collect_weekly_research("2026-06-17")
    parsed = json.loads(output)

    assert parsed["publication_date"] == "2026-06-17"
    assert parsed["candidates"] == []
    assert parsed["errors"]


def test_collect_weekly_research_wrapper_total_failure_returns_valid_json(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("catastrophic")

    monkeypatch.setattr("src.tools.research_collector._build_query_plan", boom)

    output = collect_weekly_research("2026-06-17")
    parsed = json.loads(output)

    assert parsed["candidates"] == []
    assert parsed["errors"]
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `ImportError: cannot import name '_collect_weekly_research_core'`

**Step 3: Write minimal implementation**

Append to `src/tools/research_collector.py`:

```python
def _collect_weekly_research_core(
    publication_date: str,
    max_search_results: int = 20,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
    summarizer=None,
) -> dict:
    """Run the full deterministic research collection pipeline.

    Returns a dict with keys: publication_date, candidates, total_found,
    total_fetched, errors.
    """
    if summarizer is None:
        summarizer = _default_summarizer

    errors: list[str] = []

    query_plan = _build_query_plan(publication_date)
    raw_results, search_errors = _run_searches(query_plan, publication_date)
    errors.extend(search_errors)

    candidates = _normalize_candidates(raw_results)
    total_found = len(candidates)

    candidates = _dedupe_candidates(candidates)
    candidates = _date_filter(candidates, publication_date)
    candidates = _rank_and_truncate(candidates, max_search_results)

    fetched_content = _fetch_top_candidates(candidates, max_fetches, max_chars_per_source)
    total_fetched = len(fetched_content)

    errors.extend(_summarize_candidates(candidates, fetched_content, summarizer))
    errors.extend(_persist_artifacts(publication_date, raw_results, candidates))

    return {
        "publication_date": publication_date,
        "candidates": candidates,
        "total_found": total_found,
        "total_fetched": total_fetched,
        "errors": errors,
    }


def collect_weekly_research(
    publication_date: str,
    max_search_results: int = 20,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
) -> str:
    """Collect and compact this week's AI/LLM research candidates.

    Searches AI news (Tavily), Hacker News, and official AI lab blogs across
    a fixed set of research categories, deduplicates and date-filters the
    results, fetches and summarizes the top-ranked candidates, and persists
    raw and structured artifacts under artifacts/research/{publication_date}/.

    Args:
        publication_date: Newsletter publication date in YYYY-MM-DD format.
        max_search_results: Maximum number of candidates to keep after
            ranking (default: 20).
        max_fetches: Maximum number of candidates to fetch full content for
            (default: 8).
        max_chars_per_source: Maximum characters of fetched content per
            source used for summarization (default: 1500).

    Returns:
        JSON string with keys: publication_date, candidates, total_found,
        total_fetched, and errors (omitted if empty). Each candidate has:
        title, url, source, published_at, summary, key_facts, why_it_matters,
        topic_type, category, score, fetched.
    """
    try:
        result = _collect_weekly_research_core(
            publication_date,
            max_search_results=max_search_results,
            max_fetches=max_fetches,
            max_chars_per_source=max_chars_per_source,
        )
    except Exception as exc:
        return json.dumps({
            "publication_date": publication_date,
            "candidates": [],
            "total_found": 0,
            "total_fetched": 0,
            "errors": [f"collect_weekly_research: {exc}"],
        }, ensure_ascii=False, indent=2)

    if not result.get("errors"):
        result.pop("errors", None)

    return json.dumps(result, ensure_ascii=False, indent=2)
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (19 passed)

**Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat(research): add collect_weekly_research pipeline and tool wrapper"
```

---

## Task 13: Wire `collect_weekly_research` into `research_subagent`

**Objective:** Replace `research_subagent`'s tool list with `[collect_weekly_research, fetch_article_content]`.

**Files:**
- Modify: `src/agents/research.py`
- Test: `tests/test_research_collector.py` (append)

**Step 1: Write failing test**

Append to `tests/test_research_collector.py`:

```python
def test_research_subagent_tools_wiring():
    from src.agents.research import research_subagent
    from src.tools.content_tools import fetch_article_content

    assert research_subagent["tools"] == [collect_weekly_research, fetch_article_content]
```

**Step 2: Run test to verify failure**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `AssertionError` (current tools list is `[search_ai_news, search_hackernews, fetch_article_content, fetch_official_blog_posts]`)

**Step 3: Write minimal implementation**

Replace the contents of `src/agents/research.py`:

```python
"""Research subagent for gathering AI/LLM news and trends."""

from ..tools.content_tools import fetch_article_content
from ..tools.research_collector import collect_weekly_research
from ..config import RESEARCH_AGENT_PROMPT

research_subagent = {
    "name": "research-agent",
    "description": "AI/LLM 뉴스 및 트렌드 리서치 전문가. 최신 모델 발표, HackerNews 논의, 기술 블로그를 검색하고 분석합니다.",
    "system_prompt": RESEARCH_AGENT_PROMPT,
    "tools": [collect_weekly_research, fetch_article_content],
}
```

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS (20 passed)

**Step 5: Commit**

```bash
git add src/agents/research.py tests/test_research_collector.py
git commit -m "feat(research): wire collect_weekly_research into research-agent"
```

---

## Task 14: Rewrite `RESEARCH_AGENT_PROMPT`

**Objective:** Replace the open-ended 8-category search prompt with the 3-step collect → verify → report flow, preserving the existing `research_results.md` output format and the assertions in `tests/test_prompts.py`.

**Files:**
- Modify: `src/config.py:61-133` (the `RESEARCH_AGENT_PROMPT` constant)

**Step 1: Confirm existing prompt tests (should currently pass)**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: PASS (5 passed) — establishes the baseline before the rewrite.

**Step 2: Replace `RESEARCH_AGENT_PROMPT`**

In `src/config.py`, replace the entire `RESEARCH_AGENT_PROMPT = """..."""` block (currently lines 61-133, from `RESEARCH_AGENT_PROMPT = """당신은 AI와 LLM 분야의 리서치 전문가입니다.` through the closing `"""` before `TOPIC_SELECTOR_PROMPT`) with:

```python
RESEARCH_AGENT_PROMPT = """당신은 AI와 LLM 분야의 리서치 전문가입니다.

## 작업 순서

### 1단계: 압축 리서치 수집 (필수)
`collect_weekly_research(publication_date=...)`를 호출하여 이번 주 AI/LLM 뉴스 후보 목록을 가져오세요.
이 도구는 모델 발표, AI 에이전트/자동화, 연구 논문, 도구/인프라, 산업 동향, 정책/사회, 학습 자료,
그리고 실제 AI 활용 사례(Show HN 검색 포함)와 공식 블로그(OpenAI/Anthropic/DeepMind)를
검색하고, 중복 제거·날짜 필터링·요약을 거친 압축된 후보(candidates) 목록을 반환합니다.
각 후보는 title, url, source, published_at, summary, key_facts, why_it_matters,
topic_type, category 필드를 포함합니다.

### 2단계: 선택적 원문 확인
중요도가 높은 후보 중 `fetched`가 false이거나 summary가 빈약한 후보에 대해서는
`fetch_article_content`를 사용해 원문을 확인하는 것이 필수입니다.
요약, 날짜, 모델명, 수치 등 핵심 사실을 보강해야 하는 경우에만 사용하세요.
원문을 가져올 수 없는 항목은 candidates의 정보만으로 작성하거나 "원문 확인 실패"로 명시하세요.

### 3단계: 최종 리서치 보고서 작성
candidates 목록을 바탕으로 아래 형식의 번호가 매겨진 보고서를 작성하세요.
각 토픽에 대해 다음 정보를 제공하세요:
1. 제목
2. 요약 (2-3문장) — candidates의 summary, key_facts, why_it_matters를 활용하세요
3. 출처 URL
4. 발표/게시 날짜 (published_at)
5. 중요도 (높음/중간/낮음) — category가 real_world_usecases(실제 AI 활용 사례)이거나
   why_it_matters가 강한 후보는 높음으로 표시하세요
6. 카테고리 (모델발표/에이전트/연구/도구/산업동향/정책/학습자료)

## 우선순위
실제 AI 활용 사례(개인·기업이 AI 에이전트/LLM으로 구체적 문제를 해결한 사례)는
가장 높은 우선순위로 다루세요. collect_weekly_research가 Show HN 검색 등을 통해
이미 이런 후보를 수집해 둡니다.
"""
```

**Step 3: Run prompt tests to verify pass**

Run: `uv run pytest tests/test_prompts.py -v`
Expected: PASS (5 passed) — verify specifically:
- `test_research_prompt_requires_fetch`: `"fetch_article_content"` and `"필수"` both present ✓
- `test_research_prompt_has_usecase_category`: `"실제 AI"`/`"활용 사례"` and `"Show HN"` both present ✓

**Step 4: Run the full research collector test suite**

Run: `uv run pytest tests/test_research_collector.py tests/test_prompts.py -v`
Expected: PASS (25 passed)

**Step 5: Commit**

```bash
git add src/config.py
git commit -m "feat(research): rewrite RESEARCH_AGENT_PROMPT for collect-then-report flow"
```

---

## Task 15: Document Phase 2 implementation in the optimization strategy doc

**Objective:** Add an "Implemented changes" subsection to `docs/cost-time-optimization-strategy.md`'s Phase 2 section, matching the style of the existing Phase 1 section.

**Files:**
- Modify: `docs/cost-time-optimization-strategy.md` (after the "### Expected benefit" list under "## Phase 2: Compact Deterministic Research Collector")

**Step 1: Insert "Implemented changes" subsection**

After the Phase 2 "### Expected benefit" bullet list (the one ending with "Easier reuse when HITL rejects selected topics.") and before "## Phase 3: Python-Controlled Pipeline", insert:

```markdown
### Implemented changes (this PR)

- Added `collect_weekly_research()` in `src/tools/research_collector.py`: a
  deterministic pipeline covering 9 source-routing categories (the original
  8 `RESEARCH_AGENT_PROMPT` categories plus `official_blogs`), with
  dedup-by-URL/title, a 14-day date filter, score-based ranking/truncation,
  top-N fetching via `fetch_article_content`, and a single batch-summarizer
  LLM call (`RESEARCH_COLLECTOR_MODEL`, default `claude-haiku-4-5`).
- `research-agent`'s tools are now `[collect_weekly_research,
  fetch_article_content]` — `search_ai_news`, `search_hackernews`, and
  `fetch_official_blog_posts` are called internally by the collector instead
  of by the agent directly.
- `RESEARCH_AGENT_PROMPT` now describes a 3-step collect → optionally verify
  → write report flow, producing the same numbered
  제목/요약/출처/날짜/중요도/카테고리 format as before.
- Raw search results and structured candidates are persisted to
  `artifacts/research/{publication_date}/raw_search_results.json` and
  `candidates.json` for debugging and reuse.
- Added shared `to_model_spec()` helper in `src/config.py`, used by both
  `MODEL_NAME` (top-level model) and `RESEARCH_COLLECTOR_MODEL` (collector
  summarizer model).
```

**Step 2: Commit**

```bash
git add docs/cost-time-optimization-strategy.md
git commit -m "docs: record Phase 2 research collector implementation"
```

---

## Task 16: Full test suite verification

**Objective:** Confirm the complete non-integration test suite passes with the new collector in place, with no new failures beyond the pre-existing `test_email_flow.py` errors (unrelated `src.api` module, present before this work).

**Files:** None (verification only)

**Step 1: Run the full suite excluding integration tests**

Run: `uv run pytest -q -m "not integration"`

Expected:
- All `tests/test_research_collector.py`, `tests/test_config.py`, `tests/test_phase1_cost_controls.py`, `tests/test_prompts.py`, `tests/test_blog_scraping.py` tests pass.
- `tests/test_email_flow.py` continues to show the same 8 pre-existing errors (missing `src.api` module) — unrelated to this change, not introduced by it.
- No new failures.

**Step 2: Spot-check artifact output (optional manual run)**

If `TAVILY_API_KEY`/`ANTHROPIC_API_KEY` are configured, optionally run the integration test for a manual sanity check:

Run: `uv run pytest tests/test_research_collector.py -m integration -v`
Expected: PASS — `collect_weekly_research` returns non-empty candidates and writes
`artifacts/research/{date}/raw_search_results.json` and `candidates.json`.

(Note: this integration test should be added in Task 12 as
`@pytest.mark.integration`-marked, mirroring `tests/test_blog_scraping.py`'s
`TestIntegration` class — if not already covered by the project's
`pyproject.toml` `integration` marker config.)

**Step 3: No commit needed** — this is a verification-only task. If any
regressions are found, fix them in the relevant task's files and amend that
task's commit (or add a small fix-up commit), then re-run this task.

---

## Notes for the implementer

- All new tests follow `tests/test_blog_scraping.py`'s conventions:
  `monkeypatch.setattr("src.tools.research_collector.<name>", fake)` to stub
  the imported names inside `research_collector.py`, and `tmp_path` +
  `monkeypatch.chdir(tmp_path)` for artifact-writing tests.
- `_default_summarizer` is never exercised by unit tests (only via the
  injectable `summarizer` parameter) — it requires `ANTHROPIC_API_KEY` and
  is only covered by the optional `@pytest.mark.integration` test.
- Keep `src/tools/__init__.py` unchanged — `collect_weekly_research` is
  imported directly from `..tools.research_collector` in
  `src/agents/research.py`, matching how `fetch_article_content` is already
  imported from `..tools.content_tools`.
