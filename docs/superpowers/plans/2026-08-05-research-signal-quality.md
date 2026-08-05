# Research Signal Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the newsletter research pipeline so it surfaces novel AI tool/model launches and viral demos instead of SEO listicles, per `docs/superpowers/specs/2026-08-05-research-signal-quality-design.md`.

**Architecture:** Tightens and re-scopes the existing deterministic Tavily/HN/blog/PyTorch-KR pipeline in `research_collector.py`, adds GitHub (Search API + weekly trending scrape) as two new novelty signals, and rebalances the existing score formula — all within the current search → normalize → dedupe → filter → rank → fetch → summarize shape. No new files except one test file and the plan/spec docs.

**Tech Stack:** Python 3.13, `httpx` + `BeautifulSoup` (already project dependencies), GitHub REST Search API (unauthenticated), Tavily SDK (`topic="news"`), `pytest` + `monkeypatch`.

## Global Constraints

- No new dependencies — `httpx` and `bs4` are already used by the existing PyTorch-KR/Anthropic scrapers.
- No `GITHUB_TOKEN` — unauthenticated GitHub Search API (10 req/min) covers this project's 2 calls/run (verified live during design).
- Tavily domain whitelist, exact values: `anthropic.com`, `openai.com`, `ai.google`, `blog.google`, `huggingface.co`, `arxiv.org`, `techcrunch.com`, `theverge.com`, `venturebeat.com`, `wired.com`, `arstechnica.com`.
- No live network calls in the committed test suite. Mock at the `httpx.Client` construction boundary or at the module-function boundary (`monkeypatch.setattr("src.tools.research_collector.<name>", fake)`), matching every existing test in this codebase. Anything that must hit a real API goes behind `@pytest.mark.integration` (existing convention; not needed by this plan).
- `tests/test_research_collector.py` (476 lines, pre-existing) must keep passing after every task — this plan updates its fixtures in lockstep as the pipeline changes underneath it, never leaves it red between tasks.
- Follow existing test patterns exactly: `monkeypatch.setattr` for module functions, `MagicMock(spec=httpx.Client)` (see `_make_mock_client` in `tests/test_blog_scraping.py`) for HTTP-layer tests, table-driven `@pytest.mark.parametrize` for pure-function edge cases.

---

### Task 1: Tavily quality knobs — `topic="news"` + domain whitelist

**Files:**
- Modify: `src/tools/search_tools.py:76-95` (the `client.search()` call inside `search_ai_news`)
- Test: `tests/test_search_tools.py` (new file)

**Interfaces:**
- Produces: `search_ai_news(query, max_results=10, article_date=None) -> str` — signature unchanged, only the underlying Tavily call changes. Later tasks (2) don't call this function directly; they read whatever it returns via `_run_searches`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_search_tools.py`:

```python
"""Tests for search_ai_news's Tavily call construction."""

import json
from unittest.mock import MagicMock

from src.tools.search_tools import search_ai_news


def test_search_ai_news_requests_news_topic_and_domain_whitelist(monkeypatch):
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}
    monkeypatch.setattr("src.tools.search_tools.TavilyClient", lambda api_key: mock_client)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    search_ai_news("test query", article_date="2026-08-05")

    _, kwargs = mock_client.search.call_args
    assert kwargs["topic"] == "news"
    assert set(kwargs["include_domains"]) == {
        "anthropic.com", "openai.com", "ai.google", "blog.google",
        "huggingface.co", "arxiv.org",
        "techcrunch.com", "theverge.com", "venturebeat.com", "wired.com", "arstechnica.com",
    }
    # exclude_domains stays — these three are covered by official_blogs instead
    assert set(kwargs["exclude_domains"]) == {"openai.com", "anthropic.com", "deepmind.google"}


def test_search_ai_news_returns_valid_json_on_missing_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = json.loads(search_ai_news("test query"))
    assert "error" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_search_tools.py -v`
Expected: FAIL — `include_domains` and `topic` not passed as kwargs yet (current code has `include_domains` commented out and no `topic` param).

- [ ] **Step 3: Write minimal implementation**

In `src/tools/search_tools.py`, replace the `client.search(...)` call inside `search_ai_news` (currently lines 76-95):

```python
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=max_results,
            start_date=two_weeks_ago,  # Filter for content from last 2 weeks
            include_domains=[
                "anthropic.com",
                "openai.com",
                "ai.google",
                "blog.google",
                "huggingface.co",
                "arxiv.org",
                "techcrunch.com",
                "theverge.com",
                "venturebeat.com",
                "wired.com",
                "arstechnica.com",
            ],
            exclude_domains=[
                "openai.com",
                "anthropic.com",
                "deepmind.google",
            ],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_search_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/search_tools.py tests/test_search_tools.py
git commit -m "$(cat <<'EOF'
fix: enable Tavily news topic and domain whitelist for search_ai_news

topic="news" makes Tavily populate published_date (verified live —
default search never returns it at all). include_domains was
commented out, letting SEO content mills outrank real news.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Real Tavily dates, lighter missing-date penalty, wider cutoff

**Files:**
- Modify: `src/tools/research_collector.py` — imports (top), new `_parse_tavily_date` helper (near `_parse_hn_date`, ~line 125), `"tavily"` branch in `_normalize_candidates` (~line 152-158), the `-0.5` penalty line (~line 192-193), `max_search_results` defaults in `_collect_weekly_research_core` (~line 437) and `collect_weekly_research` (~line 485)
- Test: `tests/test_research_collector.py` — modify one existing assertion, add three new tests

**Interfaces:**
- Produces: `_parse_tavily_date(raw: str | None) -> str | None` — used only within `_normalize_candidates`, not exported.

- [ ] **Step 1: Write the failing tests**

In `tests/test_research_collector.py`, first update the existing assertion (the missing-date penalty magnitude changes):

```python
    tavily_c = next(c for c in candidates if c["title"] == "Tavily Item")
    assert tavily_c["source"] == "news.example.com"
    assert tavily_c["published_at"] is None
    # tavily_score (0.75) - 0.2 (missing published_at) = 0.55
    assert tavily_c["score"] == 0.55
```

(Replaces the two lines currently reading `# tavily_score (0.75) - 0.5 (missing published_at) = 0.25` / `assert tavily_c["score"] == 0.25`.)

Then add:

```python
def test_normalize_candidates_parses_tavily_published_date():
    raw_results = [
        {
            "category": "model_releases", "tool": "tavily", "query": "...",
            "items": [{"title": "Dated Item", "url": "https://news.example.com/dated",
                       "content": "snippet", "score": 0.5,
                       "published_date": "Tue, 28 Apr 2026 17:00:03 GMT"}],
        },
    ]

    candidates = _normalize_candidates(raw_results)

    assert candidates[0]["published_at"] == "2026-04-28"
    # tavily_score (0.5), no missing-date penalty since dated
    assert candidates[0]["score"] == 0.5


def test_normalize_candidates_tavily_bad_date_falls_back_to_none():
    raw_results = [
        {
            "category": "model_releases", "tool": "tavily", "query": "...",
            "items": [{"title": "Garbage Date", "url": "https://news.example.com/garbage",
                       "content": "snippet", "score": 0.5,
                       "published_date": "not a date"}],
        },
    ]

    candidates = _normalize_candidates(raw_results)

    assert candidates[0]["published_at"] is None
    # 0.5 - 0.2 (missing/unparseable date penalty)
    assert candidates[0]["score"] == 0.3


def test_max_search_results_default_is_30():
    import inspect
    from src.tools.research_collector import _collect_weekly_research_core, collect_weekly_research

    assert inspect.signature(_collect_weekly_research_core).parameters["max_search_results"].default == 30
    assert inspect.signature(collect_weekly_research).parameters["max_search_results"].default == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_research_collector.py -k "tavily_item or tavily_published_date or tavily_bad_date or max_search_results_default" -v`
Expected: FAIL — `published_at` is still hardcoded to `None`, penalty is still `-0.5`, default is still `20`.

- [ ] **Step 3: Write minimal implementation**

Add the import at the top of `src/tools/research_collector.py` (alongside the existing `from datetime import datetime, timedelta`):

```python
from email.utils import parsedate_to_datetime
```

Add the helper right before `_normalize_candidates` (after `_parse_hn_date`):

```python
def _parse_tavily_date(raw: str | None) -> str | None:
    """Parse Tavily's published_date (RFC 2822, e.g. 'Tue, 28 Apr 2026 17:00:03 GMT')."""
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None
```

In `_normalize_candidates`, change the `"tavily"` branch:

```python
            if tool == "tavily":
                url = item.get("url", "")
                title = item.get("title", "")
                published_at = _parse_tavily_date(item.get("published_date"))
                score = float(item.get("score", 0) or 0)
                summary = item.get("content", "")
                source = urlparse(url).netloc
```

Change the penalty line:

```python
            if not published_at:
                score -= 0.2
```

Change both defaults:

```python
def _collect_weekly_research_core(
    publication_date: str,
    max_search_results: int = 30,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
    summarizer=None,
) -> dict:
```

```python
def collect_weekly_research(
    publication_date: str,
    max_search_results: int = 30,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
) -> str:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS, full file (this also re-runs the whole 476-line suite — confirm nothing else broke).

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
feat: capture real Tavily dates, ease date penalty, widen candidate cutoff

Depends on topic="news" from the previous commit. -0.5 was larger
than any novelty boost and could flip a good candidate negative on
a missing date alone; -0.2 can't override the boost by itself.
Cutoff 20->30 since boost-based scores cluster more than Tavily's
old spread-out relevance floats.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Listicle title filter

**Files:**
- Modify: `src/tools/research_collector.py` — new `_LISTICLE_TITLE_PATTERNS` + `_is_listicle_title` (near `_parse_tavily_date`), the `if not url or not title:` guard in `_normalize_candidates`
- Test: `tests/test_research_collector.py`

**Interfaces:**
- Produces: `_is_listicle_title(title: str) -> bool`, used only within `_normalize_candidates`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_research_collector.py` (needs `import pytest` at the top of the file if not already present — check first; it currently isn't, add it):

```python
import pytest
```

```python
@pytest.mark.parametrize("title", [
    "10 Best AI Developer Tools in 2026 | Scalable Path",
    "Best AI Developer Tools for 2026 | AI Software Development Tools",
    "I tried 70+ best AI tools in 2026",
    "Top 10 AI Tools Every Developer Must Know in 2026",
    "Top 10 Best AI Tools for 2026 (Q3 Update)",
    "The Definitive Guide to AI Agent Deployment for Small Business in 2026",
    "AI 에이전트 구축: 2026년 지능형 자동화 생성을 위한 완벽 가이드",
])
def test_is_listicle_title_rejects_known_seo_patterns(title):
    from src.tools.research_collector import _is_listicle_title
    assert _is_listicle_title(title) is True


@pytest.mark.parametrize("title", [
    "Anthropic ships Claude Code skill for X",
    "OpenAI announces GPT-5.6",
    "microsoft/skill-recorder",
    "State of AI Agent Security Report 2026",
])
def test_is_listicle_title_keeps_legitimate_titles(title):
    from src.tools.research_collector import _is_listicle_title
    assert _is_listicle_title(title) is False


def test_normalize_candidates_drops_listicle_titles():
    raw_results = [
        {
            "category": "model_releases", "tool": "tavily", "query": "...",
            "items": [
                {"title": "Top 10 AI Tools Every Developer Must Know", "url": "https://example.com/a",
                 "content": "x", "score": 0.9},
                {"title": "Anthropic ships new agent skill", "url": "https://example.com/b",
                 "content": "x", "score": 0.5},
            ],
        },
    ]
    candidates = _normalize_candidates(raw_results)
    titles = [c["title"] for c in candidates]
    assert "Anthropic ships new agent skill" in titles
    assert "Top 10 AI Tools Every Developer Must Know" not in titles
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_research_collector.py -k "listicle" -v`
Expected: FAIL — `_is_listicle_title` doesn't exist yet, both listicle titles currently survive normalization.

- [ ] **Step 3: Write minimal implementation**

Add near `_parse_tavily_date` in `src/tools/research_collector.py` (`re` is already imported at the top of this file):

```python
_LISTICLE_TITLE_PATTERNS = [
    re.compile(r"\btop\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bbest\b.*\b(tools?|ai)\b", re.IGNORECASE),
    re.compile(r"\d+\+?\s*(best|top)\b", re.IGNORECASE),
    re.compile(r"\bguide to\b", re.IGNORECASE),
    re.compile(r"\b(definitive|ultimate) guide\b", re.IGNORECASE),
    re.compile(r"완벽\s*가이드"),
    re.compile(r"가이드$"),
]


def _is_listicle_title(title: str) -> bool:
    """Reject SEO roundup titles ("Top 10...", "Best AI Tools...", "...완벽 가이드")."""
    return any(pattern.search(title) for pattern in _LISTICLE_TITLE_PATTERNS)
```

In `_normalize_candidates`, right after the existing `if not url or not title: continue` guard, add:

```python
            if not url or not title:
                continue
            if _is_listicle_title(title):
                continue
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
feat: reject SEO listicle titles as a structural backstop

Regex deny-list against known roundup patterns (Top N, Best X Tools,
Definitive/Ultimate Guide, 완벽 가이드). Catches content that scores
well but is never what the newsletter wants, regardless of source.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Official blog case-study routing

**Files:**
- Modify: `src/tools/research_collector.py` — new `_CASE_STUDY_KEYWORDS` + `_is_case_study_tag`, the outer/inner loop in `_normalize_candidates` (introduce `item_category`), the `"blog"` branch, the score-boost check, the candidate dict's `"category"` field
- Test: `tests/test_research_collector.py`

**Interfaces:**
- Produces: `_is_case_study_tag(tag: str) -> bool`, used only within `_normalize_candidates`.
- Changes the shape of `_normalize_candidates`'s internal loop: adds a per-item `item_category` variable that can differ from the raw result's `category` field. This is internal to the function — its output shape (`candidate["category"]`) is unchanged, just may now read `"real_world_usecases"` for what was previously always `"official_blogs"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_research_collector.py`:

```python
def test_normalize_candidates_routes_blog_case_studies_to_real_world_usecases():
    raw_results = [
        {
            "category": "official_blogs", "tool": "blog", "query": None,
            "items": [
                {"source": "anthropic", "title": "Customer story: Acme ships agents",
                 "url": "https://anthropic.com/news/acme", "date": "2026-08-01",
                 "category": "Customer story", "description": "desc"},
                {"source": "openai", "title": "Introducing GPT-5.7",
                 "url": "https://openai.com/news/gpt57", "date": "2026-08-01",
                 "category": "Announcements", "description": "desc"},
            ],
        },
    ]

    candidates = _normalize_candidates(raw_results)

    case_study = next(c for c in candidates if "Acme" in c["title"])
    assert case_study["category"] == "real_world_usecases"
    assert case_study["score"] == 0.3  # 0.0 base + 0.3 boost

    announcement = next(c for c in candidates if "GPT-5.7" in c["title"])
    assert announcement["category"] == "official_blogs"
    assert announcement["score"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_research_collector.py -k "case_studies" -v`
Expected: FAIL — both posts currently land in `official_blogs` with `score == 0.0`.

- [ ] **Step 3: Write minimal implementation**

Add near the other small helpers in `src/tools/research_collector.py`:

```python
_CASE_STUDY_KEYWORDS = ("customer", "story", "case stud")


def _is_case_study_tag(tag: str) -> bool:
    lowered = tag.lower()
    return any(keyword in lowered for keyword in _CASE_STUDY_KEYWORDS)
```

In `_normalize_candidates`, the inner loop currently starts:

```python
        for item in result["items"]:
            original_url = None
            prefetched_content = None
            if tool == "tavily":
```

Change to:

```python
        for item in result["items"]:
            original_url = None
            prefetched_content = None
            item_category = category
            if tool == "tavily":
```

In the `"blog"` branch, add the tag check at the end:

```python
            elif tool == "blog":
                url = item.get("url", "")
                title = item.get("title", "")
                published_at = item.get("date")
                score = 0.0
                summary = item.get("description", "")
                source = item.get("source") or urlparse(url).netloc
                if _is_case_study_tag(item.get("category", "")):
                    item_category = "real_world_usecases"
```

Change the score-boost check and the candidate dict to use `item_category` instead of `category`:

```python
            if item_category == "real_world_usecases":
                score += 0.3
            if not published_at:
                score -= 0.2

            candidate = {
                "title": title,
                "url": url,
                "source": source,
                "published_at": published_at,
                "summary": summary,
                "key_facts": [],
                "why_it_matters": "",
                "topic_type": topic_type,
                "category": item_category,
                "score": round(score, 3),
                "fetched": False,
            }
```

(`topic_type` stays keyed by the outer `category`, unchanged — that lookup is being simplified separately in Task 5.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
feat: route official-blog case studies into real_world_usecases

Blog posts already carry a category tag from their source site
(OpenAI/DeepMind RSS <category>, Anthropic's scraped section label).
Customer-story-shaped tags now pick up the same +0.3 novelty boost
as real_world_usecases; other tags (Announcements, Product) unaffected.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Drop the four SEO-listicle-prone categories

**Files:**
- Modify: `src/tools/research_collector.py` — `CATEGORY_TOPIC_TYPE` dict (delete), `RESEARCH_QUERY_PLAN` (trim), the `topic_type = ...` line in `_normalize_candidates`
- Test: `tests/test_research_collector.py` — `EXPECTED_CATEGORIES`, delete one obsolete test

**Interfaces:**
- No public interface change. `topic_type` in every candidate becomes `"main"` at normalize time for every category (the batch summarizer can still tag any candidate `"study_cafe"` based on actual content — unaffected by this change, see `SUMMARIZER_SYSTEM_PROMPT`).

- [ ] **Step 1: Write the failing test**

In `tests/test_research_collector.py`, update `EXPECTED_CATEGORIES` (currently lines 21-32):

```python
EXPECTED_CATEGORIES = {
    "model_releases",
    "agents_automation",
    "research_papers",
    "real_world_usecases",
    "official_blogs",
    "pytorch_kr_community",
}
```

Delete `test_normalize_candidates_study_resources_topic_type` (currently lines 177-187) entirely — `study_resources` no longer exists as a category.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_research_collector.py -k "query_plan_covers_all_categories" -v`
Expected: FAIL — `RESEARCH_QUERY_PLAN` still has the old 10 categories.

- [ ] **Step 3: Write minimal implementation**

In `src/tools/research_collector.py`, delete `CATEGORY_TOPIC_TYPE` entirely (currently):

```python
# Maps research categories to the topic_type assigned during normalization.
# Categories not listed here default to "main". The batch summarizer may
# override topic_type per candidate based on actual content.
CATEGORY_TOPIC_TYPE: dict[str, str] = {
    "study_resources": "study_cafe",
}
DEFAULT_TOPIC_TYPE = "main"
```

becomes just:

```python
DEFAULT_TOPIC_TYPE = "main"
```

Replace `RESEARCH_QUERY_PLAN` (and its header comment) with:

```python
# Query-plan entries across 4 categories that carry a real search query
# (model_releases, agents_automation, research_papers, real_world_usecases),
# plus 2 source-routing categories with dedicated fetchers and no query
# (official_blogs, pytorch_kr_community).
# {year}/{month}/{month_en} placeholders are filled by _build_query_plan() from publication_date.
RESEARCH_QUERY_PLAN: list[dict] = [
    {"category": "model_releases", "tool": "tavily", "query": "{year}년 {month}월 AI 모델 출시"},
    {"category": "model_releases", "tool": "tavily", "query": "{month_en} {year} new LLM model release"},
    {"category": "agents_automation", "tool": "hn", "query": "AI agent"},
    {"category": "research_papers", "tool": "tavily", "query": "arXiv AI agent {month_en} {year}"},
    {"category": "real_world_usecases", "tool": "hn", "query": "Show HN AI agent"},
    {"category": "official_blogs", "tool": "blog", "query": None},
    {"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None},
]
```

In `_normalize_candidates`, change:

```python
        topic_type = CATEGORY_TOPIC_TYPE.get(category, DEFAULT_TOPIC_TYPE)
```

to:

```python
        topic_type = DEFAULT_TOPIC_TYPE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
refactor: drop tools_infra, industry_business, policy_society, study_resources

These four categories existed almost entirely to produce SEO roundup
content — exactly the junk this whole change is trying to remove.
study_resources fed the study_cafe newsletter slot; the summarizer
can still opportunistically tag any candidate study_cafe by content,
just without a dedicated query hunting for tutorials. Accepted tradeoff,
documented in the design spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: GitHub Search API tool — `search_github_repos`

**Files:**
- Modify: `src/tools/search_tools.py` — new `GITHUB_SEARCH_URL` constant + `search_github_repos` function
- Test: `tests/test_search_tools.py` (extend the file from Task 1)

**Interfaces:**
- Produces: `search_github_repos(query: str, publication_date: str, max_results: int = 6) -> str` — JSON string, either a list of `{full_name, url, description, stars, created_at}` dicts or `{"error": str}`. Consumed by Task 8's `_run_searches` dispatch.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_search_tools.py`:

```python
import httpx


def _make_mock_github_search_client(payload: dict) -> httpx.Client:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


def test_search_github_repos_shapes_results_and_builds_query(monkeypatch):
    from src.tools.search_tools import search_github_repos

    payload = {
        "items": [
            {"full_name": "microsoft/skill-recorder",
             "html_url": "https://github.com/microsoft/skill-recorder",
             "description": "Records sessions", "stargazers_count": 1763,
             "created_at": "2026-07-29T00:00:00Z"},
        ]
    }
    mock_client = _make_mock_github_search_client(payload)
    monkeypatch.setattr("src.tools.search_tools.httpx.Client", lambda **kwargs: mock_client)

    result = json.loads(search_github_repos("topic:ai-agents", "2026-08-05"))

    assert result == [{
        "full_name": "microsoft/skill-recorder",
        "url": "https://github.com/microsoft/skill-recorder",
        "description": "Records sessions",
        "stars": 1763,
        "created_at": "2026-07-29T00:00:00Z",
    }]

    call_kwargs = mock_client.get.call_args.kwargs
    assert "created:>2026-07-22" in call_kwargs["params"]["q"]
    assert call_kwargs["params"]["sort"] == "stars"


def test_search_github_repos_handles_network_error(monkeypatch):
    from src.tools.search_tools import search_github_repos

    def boom(**kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr("src.tools.search_tools.httpx.Client", boom)

    result = json.loads(search_github_repos("topic:ai-agents", "2026-08-05"))
    assert "error" in result


def test_search_github_repos_rejects_bad_date():
    from src.tools.search_tools import search_github_repos

    result = json.loads(search_github_repos("topic:ai-agents", "not-a-date"))
    assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_search_tools.py -k github -v`
Expected: FAIL — `search_github_repos` doesn't exist yet.

- [ ] **Step 3: Write minimal implementation**

Add to `src/tools/search_tools.py` (after `search_hackernews`, before the PyTorch-KR section):

```python
GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def search_github_repos(query: str, publication_date: str, max_results: int = 6) -> str:
    """Search GitHub repositories via the public Search API for repos created recently.

    Args:
        query: GitHub search qualifiers/keywords (e.g. "topic:ai-agents")
        publication_date: Newsletter publication date in YYYY-MM-DD format.
            Results are restricted to repos created in the 14 days before this date.
        max_results: Maximum number of results to return (default: 6)

    Returns:
        JSON string containing repo full_name, url, description, stars, created_at
    """
    try:
        pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid publication_date format. Use YYYY-MM-DD."})

    window_start = (pub_date - timedelta(days=14)).strftime("%Y-%m-%d")
    full_query = f"{query} created:>{window_start}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                GITHUB_SEARCH_URL,
                params={
                    "q": full_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": max_results,
                },
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "full_name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "description": item.get("description") or "",
                "stars": item.get("stargazers_count", 0),
                "created_at": item.get("created_at", ""),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_search_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/search_tools.py tests/test_search_tools.py
git commit -m "$(cat <<'EOF'
feat: add search_github_repos for newly-launched AI/agent repos

GitHub Search API, repos created in the 14 days before publication_date,
sorted by stars. Verified live during design: genuinely novel,
non-listicle repos (microsoft/skill-recorder, perplexityai/numbat, etc).
Unauthenticated (10 req/min quota, this project uses 2 calls/run).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: GitHub trending scrape — `fetch_github_trending`

**Files:**
- Modify: `src/tools/content_tools.py` — new `GITHUB_TRENDING_URL`, `_GITHUB_TRENDING_KEYWORDS`, `_matches_ai_keywords`, `_fetch_github_trending_posts`, `fetch_github_trending`
- Test: `tests/test_blog_scraping.py` (extend — this file already tests `content_tools.py`'s scraping functions with the exact `_make_mock_client` pattern needed here)

**Interfaces:**
- Produces: `fetch_github_trending(publication_date: str) -> str` — JSON string `{"publication_date": str, "posts": [...]}` (optionally `"errors": [...]`), each post `{full_name, url, description, stars_this_week}`. Consumed by Task 8's `_run_searches` dispatch.
- Produces (internal): `_fetch_github_trending_posts(client: httpx.Client) -> list[dict]` — pure-ish parsing function taking an already-constructed client, mirroring `_fetch_anthropic_posts(client, start, end)`'s pattern in the same file.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_blog_scraping.py` (after the Anthropic HTML test classes, before the `TestFetchOfficialBlogPostsStructure` section):

```python
# ---------------------------------------------------------------------------
# Unit tests: GitHub trending scrape
# ---------------------------------------------------------------------------

SAMPLE_TRENDING_HTML = """\
<html><body>
<article class="Box-row">
  <h2><a href="/microsoft/AI-For-Beginners">microsoft / AI-For-Beginners</a></h2>
  <p>12 Weeks, 24 Lessons, AI for All!</p>
  <span class="d-inline-block float-sm-right">7,554 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/some-org/unrelated-project">some-org / unrelated-project</a></h2>
  <p>A CLI for managing dotfiles</p>
  <span class="d-inline-block float-sm-right">500 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/block/buzz">block / buzz</a></h2>
  <p>A hive mind communication platform for agents</p>
  <span class="d-inline-block float-sm-right">7,372 stars this week</span>
</article>
</body></html>
"""


class TestFetchGithubTrendingPosts:
    def test_filters_by_ai_keyword(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client(SAMPLE_TRENDING_HTML)
        posts = _fetch_github_trending_posts(client)

        names = [p["full_name"] for p in posts]
        assert "microsoft/AI-For-Beginners" in names
        assert "block/buzz" in names
        assert "some-org/unrelated-project" not in names

    def test_post_fields(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client(SAMPLE_TRENDING_HTML)
        posts = _fetch_github_trending_posts(client)

        post = next(p for p in posts if p["full_name"] == "microsoft/AI-For-Beginners")
        assert post["url"] == "https://github.com/microsoft/AI-For-Beginners"
        assert post["description"] == "12 Weeks, 24 Lessons, AI for All!"
        assert post["stars_this_week"] == "7,554 stars this week"

    def test_no_matching_articles(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client("<html><body>no repos here</body></html>")
        assert _fetch_github_trending_posts(client) == []


class TestFetchGithubTrending:
    def test_output_structure(self, monkeypatch):
        from src.tools.content_tools import fetch_github_trending

        monkeypatch.setattr(
            "src.tools.content_tools._fetch_github_trending_posts",
            lambda client: [{"full_name": "a/b", "url": "https://github.com/a/b",
                              "description": "d", "stars_this_week": "1 stars this week"}],
        )
        result = json.loads(fetch_github_trending("2026-08-05"))
        assert result["publication_date"] == "2026-08-05"
        assert len(result["posts"]) == 1
        assert "errors" not in result

    def test_errors_captured_not_raised(self, monkeypatch):
        from src.tools.content_tools import fetch_github_trending

        def fail(client):
            raise ConnectionError("network down")

        monkeypatch.setattr("src.tools.content_tools._fetch_github_trending_posts", fail)

        result = json.loads(fetch_github_trending("2026-08-05"))
        assert result["posts"] == []
        assert "network down" in result["errors"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_blog_scraping.py -k Trending -v`
Expected: FAIL — `_fetch_github_trending_posts` / `fetch_github_trending` don't exist yet.

- [ ] **Step 3: Write minimal implementation**

Add to `src/tools/content_tools.py` (after `fetch_official_blog_posts`, at the end of the file):

```python
GITHUB_TRENDING_URL = "https://github.com/trending"
_GITHUB_TRENDING_KEYWORDS = ("agent", "ai", "llm", "gpt", "claude", "gemini")  # ponytail: keyword allowlist, misses on-topic repos with none of these words — add NLP classification only if this proves too lossy in practice


def _matches_ai_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _GITHUB_TRENDING_KEYWORDS)


def _fetch_github_trending_posts(client: httpx.Client) -> list[dict]:
    """Fetch github.com/trending (weekly) and keyword-filter to AI/agent repos."""
    response = client.get(GITHUB_TRENDING_URL, params={"since": "weekly"}, headers=_HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts = []
    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if not link or not link.get("href"):
            continue
        full_name = link["href"].strip("/")

        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        if not _matches_ai_keywords(f"{full_name} {description}"):
            continue

        stars_el = article.select_one("span.d-inline-block.float-sm-right")
        stars_this_week = stars_el.get_text(strip=True) if stars_el else ""

        posts.append({
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "stars_this_week": stars_this_week,
        })
    return posts


def fetch_github_trending(publication_date: str) -> str:
    """Scrape github.com/trending (weekly window) for AI/agent-related repos
    gaining stars fast — a "viral this week" signal the Search API can't
    provide (it only exposes total stars, not stars gained).

    Args:
        publication_date: Newsletter publication date in YYYY-MM-DD format.
            Context only — the trending page reflects the current week at
            fetch time, not a lookup for that specific date.

    Returns:
        JSON string with publication_date and a list of
        {full_name, url, description, stars_this_week}, filtered to repos
        whose name or description mentions an AI/agent-related keyword.
    """
    result = {"publication_date": publication_date, "posts": []}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            result["posts"] = _fetch_github_trending_posts(client)
    except Exception as e:
        result["errors"] = [str(e)]
    return json.dumps(result, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_blog_scraping.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add src/tools/content_tools.py tests/test_blog_scraping.py
git commit -m "$(cat <<'EOF'
feat: add fetch_github_trending for real viral-this-week signal

github.com/trending?since=weekly shows stars gained this week, which
the Search API can't expose (only total stars). Global trending page,
not AI-scoped, so results are keyword-filtered post-scrape. Verified
live during design (block/buzz 7,372 stars/week, etc).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Wire GitHub into the query plan and dispatch

**Files:**
- Modify: `src/tools/research_collector.py` — imports, `RESEARCH_QUERY_PLAN`, `_run_searches`
- Test: `tests/test_research_collector.py` — extend 4 existing tests, add 1 new test

**Interfaces:**
- Consumes: `search_github_repos(query, publication_date, max_results=6) -> str` (Task 6), `fetch_github_trending(publication_date) -> str` (Task 7).
- Produces: `_run_searches` output now includes raw-result entries with `tool in {"github_search", "github_trending_scrape"}`. `github_trending_scrape` items each carry an injected `"published_at"` key (the run's `publication_date`) — Task 9's normalize step reads this directly rather than receiving `publication_date` as a parameter.

- [ ] **Step 1: Write the failing tests**

In `tests/test_research_collector.py`, update `EXPECTED_CATEGORIES` (from Task 5) to add the new category:

```python
EXPECTED_CATEGORIES = {
    "model_releases",
    "agents_automation",
    "research_papers",
    "real_world_usecases",
    "official_blogs",
    "pytorch_kr_community",
    "github_trending",
}
```

Update `test_run_searches_collects_items_and_tags_category` — add fakes and assertions for the two new tools:

```python
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

    def fake_search_pytorch_kr_forum(publication_date):
        return json.dumps({"publication_date": publication_date, "posts": []})

    def fake_search_github_repos(query, publication_date, max_results=6):
        return json.dumps([
            {"full_name": "example/repo", "url": "https://github.com/example/repo",
             "description": "desc", "stars": 100, "created_at": "2026-06-10T00:00:00Z"}
        ])

    def fake_fetch_github_trending(publication_date):
        return json.dumps({"publication_date": publication_date, "posts": []})

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", fake_search_ai_news)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", fake_search_hackernews)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", fake_fetch_official_blog_posts)
    monkeypatch.setattr("src.tools.research_collector.search_pytorch_kr_forum", fake_search_pytorch_kr_forum)
    monkeypatch.setattr("src.tools.research_collector.search_github_repos", fake_search_github_repos)
    monkeypatch.setattr("src.tools.research_collector.fetch_github_trending", fake_fetch_github_trending)

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
    github_search_entries = [r for r in raw_results if r["tool"] == "github_search"]
    assert github_search_entries and all(r["items"] for r in github_search_entries)
```

Update `test_run_searches_captures_errors_without_raising` — add the two new `boom` patches:

```python
def test_run_searches_captures_errors_without_raising(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr("src.tools.research_collector.search_ai_news", boom)
    monkeypatch.setattr("src.tools.research_collector.search_hackernews", boom)
    monkeypatch.setattr("src.tools.research_collector.fetch_official_blog_posts", boom)
    monkeypatch.setattr("src.tools.research_collector.search_pytorch_kr_forum", boom)
    monkeypatch.setattr("src.tools.research_collector.search_github_repos", boom)
    monkeypatch.setattr("src.tools.research_collector.fetch_github_trending", boom)

    plan = _build_query_plan("2026-06-17")
    raw_results, errors = _run_searches(plan, "2026-06-17")

    assert len(errors) == len(plan)
    assert all(r["items"] == [] for r in raw_results)
```

In `test_collect_weekly_research_core_returns_envelope`, insert these two lines directly after the existing `monkeypatch.setattr("src.tools.research_collector.fetch_article_content", fake_fetch_article_content)` line, before `result = _collect_weekly_research_core(...)`:

```python
    monkeypatch.setattr("src.tools.research_collector.search_github_repos",
                         lambda query, publication_date, max_results=6: json.dumps([]))
    monkeypatch.setattr("src.tools.research_collector.fetch_github_trending",
                         lambda publication_date: json.dumps({"publication_date": publication_date, "posts": []}))
```

In `test_collect_weekly_research_wrapper_returns_valid_json_on_search_failure`, insert these two lines directly after the existing `monkeypatch.setattr("src.tools.research_collector.search_pytorch_kr_forum", boom)` line, before `output = collect_weekly_research(...)` — `boom`, not the empty-result fakes, since this test's whole point is every source failing at once:

```python
    monkeypatch.setattr("src.tools.research_collector.search_github_repos", boom)
    monkeypatch.setattr("src.tools.research_collector.fetch_github_trending", boom)
```

Add a new test for the `published_at` injection:

```python
def test_run_searches_injects_publication_date_into_trending_items(monkeypatch):
    def fake_fetch_github_trending(publication_date):
        return json.dumps({"publication_date": publication_date,
                            "posts": [{"full_name": "a/b", "url": "https://github.com/a/b",
                                       "description": "d", "stars_this_week": "1 stars this week"}]})

    monkeypatch.setattr("src.tools.research_collector.fetch_github_trending", fake_fetch_github_trending)
    monkeypatch.setattr("src.tools.research_collector.search_github_repos",
                         lambda query, publication_date, max_results=6: json.dumps([]))
    monkeypatch.setattr("src.tools.research_collector.search_ai_news",
                         lambda query, max_results=10, article_date=None: json.dumps([]))
    monkeypatch.setattr("src.tools.research_collector.search_hackernews",
                         lambda query, num_results=10, publication_date=None: json.dumps([]))
    monkeypatch.setattr(
        "src.tools.research_collector.fetch_official_blog_posts",
        lambda publication_date: json.dumps({"posts": {"openai": [], "anthropic": [], "deepmind": []}}),
    )
    monkeypatch.setattr(
        "src.tools.research_collector.search_pytorch_kr_forum",
        lambda publication_date: json.dumps({"posts": []}),
    )

    plan = _build_query_plan("2026-06-17")
    raw_results, errors = _run_searches(plan, "2026-06-17")

    trending_entry = next(r for r in raw_results if r["tool"] == "github_trending_scrape")
    assert trending_entry["items"][0]["published_at"] == "2026-06-17"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: FAIL — `search_github_repos`/`fetch_github_trending` aren't imported into `research_collector.py` yet, `RESEARCH_QUERY_PLAN` has no `github_trending` entries, `_run_searches` has no dispatch branches for the two new tool names.

- [ ] **Step 3: Write minimal implementation**

In `src/tools/research_collector.py`, update the imports:

```python
from .search_tools import search_ai_news, search_hackernews, search_pytorch_kr_forum, search_github_repos
from .content_tools import fetch_article_content, fetch_official_blog_posts, fetch_github_trending
```

Append to `RESEARCH_QUERY_PLAN` (after the `pytorch_kr_community` entry) and update the header comment:

```python
# Query-plan entries across 5 categories that carry a real search query
# (model_releases, agents_automation, research_papers, real_world_usecases,
# github_trending), plus 2 source-routing categories with dedicated
# fetchers and no query (official_blogs, pytorch_kr_community).
# {year}/{month}/{month_en} placeholders are filled by _build_query_plan() from publication_date.
RESEARCH_QUERY_PLAN: list[dict] = [
    {"category": "model_releases", "tool": "tavily", "query": "{year}년 {month}월 AI 모델 출시"},
    {"category": "model_releases", "tool": "tavily", "query": "{month_en} {year} new LLM model release"},
    {"category": "agents_automation", "tool": "hn", "query": "AI agent"},
    {"category": "research_papers", "tool": "tavily", "query": "arXiv AI agent {month_en} {year}"},
    {"category": "real_world_usecases", "tool": "hn", "query": "Show HN AI agent"},
    {"category": "official_blogs", "tool": "blog", "query": None},
    {"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None},
    {"category": "github_trending", "tool": "github_search", "query": "topic:ai-agents"},
    {"category": "github_trending", "tool": "github_search", "query": "agent AI in:name,description"},
    {"category": "github_trending", "tool": "github_trending_scrape", "query": None},
]
```

In `_run_searches`, add two `elif` branches after the existing `elif tool == "pytorch_kr":` block, before `except Exception as exc:`:

```python
            elif tool == "github_search":
                parsed = json.loads(search_github_repos(query, publication_date, max_results=6))
                if isinstance(parsed, dict) and "error" in parsed:
                    errors.append(f"{category}/{tool}: {parsed['error']}")
                elif isinstance(parsed, list):
                    items = parsed
            elif tool == "github_trending_scrape":
                trending_result = json.loads(fetch_github_trending(publication_date))
                for trending_error in trending_result.get("errors", []):
                    errors.append(f"{category}/{tool}: {trending_error}")
                items = trending_result.get("posts", [])
                for trending_item in items:
                    trending_item["published_at"] = publication_date
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
feat: wire GitHub search + trending scrape into the query plan

Two github_search queries (topic:ai-agents, keyword) plus one
github_trending_scrape entry under the new github_trending category.
Trending items get publication_date injected as their published_at
approximation (the weekly page has no per-repo date).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Normalize GitHub candidates, extend the novelty score boost

**Files:**
- Modify: `src/tools/research_collector.py` — new `_NOVELTY_BOOST_CATEGORIES`, two new branches in `_normalize_candidates`, the score-boost check
- Test: `tests/test_research_collector.py`

**Interfaces:**
- Produces: `_normalize_candidates` now handles `tool in {"github_search", "github_trending_scrape"}`, emitting candidates with `category == "github_trending"`, `source == "github.com"`, and the `+0.3` novelty boost applied.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_research_collector.py`:

```python
def test_normalize_candidates_github_search_branch():
    raw_results = [
        {
            "category": "github_trending", "tool": "github_search", "query": "topic:ai-agents",
            "items": [{"full_name": "microsoft/skill-recorder",
                       "url": "https://github.com/microsoft/skill-recorder",
                       "description": "Records sessions", "stars": 1763,
                       "created_at": "2026-07-29T00:00:00Z"}],
        },
    ]

    candidates = _normalize_candidates(raw_results)

    assert len(candidates) == 1
    c = candidates[0]
    assert c["title"] == "microsoft/skill-recorder"
    assert c["category"] == "github_trending"
    assert c["published_at"] == "2026-07-29"
    assert c["source"] == "github.com"
    assert c["score"] == 0.3  # 0.0 base + 0.3 novelty boost


def test_normalize_candidates_github_trending_scrape_branch():
    raw_results = [
        {
            "category": "github_trending", "tool": "github_trending_scrape", "query": None,
            "items": [{"full_name": "block/buzz", "url": "https://github.com/block/buzz",
                       "description": "A hive mind communication platform",
                       "stars_this_week": "7,372 stars this week",
                       "published_at": "2026-08-05"}],
        },
    ]

    candidates = _normalize_candidates(raw_results)

    assert len(candidates) == 1
    c = candidates[0]
    assert c["title"] == "block/buzz"
    assert c["published_at"] == "2026-08-05"
    assert "7,372 stars this week" in c["summary"]
    assert c["score"] == 0.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_research_collector.py -k "github_search_branch or github_trending_scrape_branch" -v`
Expected: FAIL — `_normalize_candidates` has no branches for these two tool names yet, falls through to `else: continue`, producing zero candidates.

- [ ] **Step 3: Write minimal implementation**

Add near the other small helpers in `src/tools/research_collector.py` (this replaces the plain `if item_category == "real_world_usecases":` check from Task 4):

```python
_NOVELTY_BOOST_CATEGORIES = {"real_world_usecases", "github_trending"}
```

Add two branches in `_normalize_candidates`, after the `elif tool == "pytorch_kr":` branch and before `else: continue`:

```python
            elif tool == "github_search":
                url = item.get("url", "")
                title = item.get("full_name", "")
                created_at = item.get("created_at", "")
                published_at = created_at[:10] if created_at else None
                score = 0.0
                summary = item.get("description", "")
                source = "github.com"
            elif tool == "github_trending_scrape":
                url = item.get("url", "")
                title = item.get("full_name", "")
                published_at = item.get("published_at")  # ponytail: approximation — trending page has no per-repo date, this is the run's publication_date
                score = 0.0
                description = item.get("description", "")
                stars_note = item.get("stars_this_week", "")
                summary = f"{description} ({stars_note})" if stars_note else description
                source = "github.com"
```

Change the score-boost check:

```python
            if item_category in _NOVELTY_BOOST_CATEGORIES:
                score += 0.3
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "$(cat <<'EOF'
feat: normalize GitHub candidates, extend novelty boost to github_trending

Both github_search and github_trending_scrape items now produce
correctly-shaped candidates. The +0.3 boost that previously only
applied to real_world_usecases now applies to both.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Update category labels and importance rule

**Files:**
- Modify: `src/tools/research_report.py` — `CATEGORY_LABELS_KO`, `_importance`
- Test: `tests/test_research_report.py`

**Interfaces:**
- No signature changes. `_label`/`_importance` output changes for the `github_trending` category and no longer recognize the four dropped categories (they'll fall back to the `category or "기타"` default in `_label`, which is already the existing behavior for any unknown category — not a new code path).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_research_report.py`:

```python
def test_render_labels_github_trending_as_high_importance():
    candidate = _candidate(1, category="github_trending", score=0.3)
    out = render_research_results({"publication_date": "2026-08-05", "candidates": [candidate]})
    assert "카테고리: 오픈소스" in out
    assert "중요도: 높음" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_research_report.py -k github_trending -v`
Expected: FAIL — `github_trending` isn't in `CATEGORY_LABELS_KO` (falls back to `"github_trending"` as its own label) and isn't in the "always 높음" rule (score 0.3 is below the 0.4 중간 threshold, so it'd currently render 낮음).

- [ ] **Step 3: Write minimal implementation**

Replace `CATEGORY_LABELS_KO` in `src/tools/research_report.py`:

```python
CATEGORY_LABELS_KO = {
    "model_releases": "모델발표",
    "agents_automation": "에이전트",
    "research_papers": "연구",
    "real_world_usecases": "활용사례",
    "official_blogs": "공식블로그",
    "pytorch_kr_community": "커뮤니티",
    "github_trending": "오픈소스",
}
```

Update `_importance`:

```python
_NOVELTY_CATEGORIES = {"real_world_usecases", "github_trending"}


def _importance(candidate: dict) -> str:
    """Apply the rule the old research prompt asked a model to eyeball.

    The score formula in research_collector already encodes it:
    real_world_usecases/github_trending +0.3, HN >50 points +0.2, missing date -0.2.
    """
    score = candidate.get("score") or 0
    if candidate.get("category") in _NOVELTY_CATEGORIES or score >= 0.8:
        return "높음"
    return "중간" if score >= 0.4 else "낮음"
```

(`research_report.py` deliberately doesn't import `_NOVELTY_BOOST_CATEGORIES` from `research_collector.py` — that module stays stdlib-only per the existing architecture, so the two-category set is duplicated here rather than shared. Low drift risk at two entries.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_research_report.py -v`
Expected: PASS, full file.

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_report.py tests/test_research_report.py
git commit -m "$(cat <<'EOF'
feat: label github_trending candidates, surface them as high-importance

CATEGORY_LABELS_KO drops the four removed categories, adds
github_trending -> 오픈소스. _importance's always-높음 rule now
covers github_trending alongside real_world_usecases.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:77`, `CLAUDE.md:100-121` (directory structure), `CLAUDE.md:193-207` (Search Tools section)

**Interfaces:** None — documentation only, no test cycle.

- [ ] **Step 1: Update the category count**

Change line 77 from:

```
- `run_weekly_research(date)` searches 10 categories, dedupes, date-filters,
```

to:

```
- `run_weekly_research(date)` searches 7 categories, dedupes, date-filters,
```

- [ ] **Step 2: Update the directory structure comments**

Change:

```
│   ├── search_tools.py       # Tavily, HackerNews, PyTorch-KR forum
│   ├── content_tools.py      # Article fetching, official blog RSS
```

to:

```
│   ├── search_tools.py       # Tavily, HackerNews, PyTorch-KR forum, GitHub search
│   ├── content_tools.py      # Article fetching, official blog RSS, GitHub trending
```

- [ ] **Step 3: Update the Search Tools section**

Change:

```
### Tavily Search (`search_ai_news`)

Whitelisted domains:
- Official blogs: anthropic.com, openai.com, ai.google, blog.google
- Tech platforms: huggingface.co, arxiv.org
- News outlets: techcrunch.com, theverge.com, venturebeat.com, wired.com, arstechnica.com

Uses `search_depth="advanced"` for comprehensive results.

### HackerNews Search (`search_hackernews`)

Uses Algolia HN API with `tags=story` filter.
Returns: title, URL, HN discussion URL, points, comment count, author, timestamp.
```

to:

```
### Tavily Search (`search_ai_news`)

Whitelisted domains:
- Official blogs: anthropic.com, openai.com, ai.google, blog.google
- Tech platforms: huggingface.co, arxiv.org
- News outlets: techcrunch.com, theverge.com, venturebeat.com, wired.com, arstechnica.com

Uses `search_depth="advanced"` and `topic="news"` (required for Tavily to
populate `published_date` — the default topic never returns it) for
recent, dated results.

### HackerNews Search (`search_hackernews`)

Uses Algolia HN API with `tags=story` filter.
Returns: title, URL, HN discussion URL, points, comment count, author, timestamp.

### GitHub (`search_github_repos`, `fetch_github_trending`)

Two signals under the `github_trending` category:
- `search_github_repos`: GitHub Search API, repos created in the last 14 days, sorted by stars — "just launched."
- `fetch_github_trending`: scrapes `github.com/trending?since=weekly`, keyword-filtered to AI/agent-related repos — "viral this week" (stars gained, not total; the Search API can't expose this).

No `GITHUB_TOKEN` required — unauthenticated rate limit (10 req/min) comfortably covers this project's usage.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: update CLAUDE.md for the research signal quality changes

Category count, directory structure comments, and Search Tools
section now reflect topic="news", the domain whitelist actually
being enforced, and the new GitHub source.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Post-plan verification

After Task 11, run the full suite once more to confirm nothing drifted across tasks:

```bash
uv run pytest tests/ -v
```

Expected: all tests pass (the `@pytest.mark.integration`-marked tests in `test_blog_scraping.py` are skipped by default — that's expected and matches existing CI behavior).
