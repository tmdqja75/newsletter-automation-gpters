"""Compact deterministic research collector for newsletter generation.

A single Python-controlled pipeline, not an open-ended model search/fetch
loop: search a fixed set of categories, normalize, deduplicate, date-filter,
rank, fetch top candidates, batch-summarize via a cheap model, persist
artifacts, and return a compact candidate list.
"""

import json
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

from .search_tools import search_ai_news, search_hackernews, search_pytorch_kr_forum, search_github_repos
from .content_tools import fetch_article_content, fetch_official_blog_posts, fetch_github_trending
from ..config import ARTICLES_DIR
from .research_report import render_research_results


_MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DEFAULT_TOPIC_TYPE = "main"

# Query-plan entries across 5 categories that carry a real search query
# (model_releases, agents_automation, research_papers, real_world_usecases,
# github_trending), plus 2 source-routing categories with dedicated
# fetchers and no query (official_blogs, pytorch_kr_community).
# {year}/{month}/{month_en} placeholders are filled by _build_query_plan() from publication_date.
RESEARCH_QUERY_PLAN: list[dict] = [
    {"category": "model_releases", "tool": "tavily", "query": "{year}년 {month}월 AI 모델 출시"},
    {"category": "model_releases", "tool": "tavily", "query": "{month_en} {year} new LLM model release"},
    {"category": "agents_automation", "tool": "hn", "query": "AI agent"},
    {"category": "agents_automation", "tool": "hn", "query": "Claude Code"},
    {"category": "agents_automation", "tool": "hn", "query": "coding agent"},
    {"category": "agents_automation", "tool": "tavily", "query": "AI coding agent harness comparison"},
    {"category": "agents_automation", "tool": "tavily", "query": "AI agent framework launch {month_en} {year}"},
    {"category": "agents_automation", "tool": "tavily", "query": "AI agent startup funding {month_en} {year}"},
    {"category": "research_papers", "tool": "tavily", "query": "arXiv AI agent {month_en} {year}"},
    {"category": "research_papers", "tool": "tavily", "query": "multi-agent orchestration production lessons learned"},
    {"category": "real_world_usecases", "tool": "hn", "query": "Show HN AI agent"},
    {"category": "real_world_usecases", "tool": "tavily", "query": "how teams integrate AI agents into workflow"},
    {"category": "official_blogs", "tool": "blog", "query": None},
    {"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None},
    {"category": "github_trending", "tool": "github_search", "query": "topic:ai-agents"},
    {"category": "github_trending", "tool": "github_search", "query": "agent AI in:name,description"},
    {"category": "github_trending", "tool": "github_search", "query": "token compression OR context compression LLM"},
    {"category": "github_trending", "tool": "github_search", "query": "agent harness"},
    {"category": "github_trending", "tool": "github_trending_scrape", "query": None},
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
                elif isinstance(parsed, list):
                    items = parsed
            elif tool == "hn":
                parsed = json.loads(search_hackernews(query, num_results=6, publication_date=publication_date))
                if isinstance(parsed, dict) and "error" in parsed:
                    errors.append(f"{category}/{tool}: {parsed['error']}")
                elif isinstance(parsed, list):
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
            elif tool == "pytorch_kr":
                forum_result = json.loads(search_pytorch_kr_forum(publication_date))
                for forum_error in forum_result.get("errors", []):
                    errors.append(f"{category}/{tool}: {forum_error}")
                forum_posts = forum_result.get("posts", [])
                if isinstance(forum_posts, list):
                    items = forum_posts
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
        except Exception as exc:
            errors.append(f"{category}/{tool}: {exc}")
            items = []

        raw_results.append({"category": category, "tool": tool, "query": query, "items": items})

    return raw_results, errors


def _parse_hn_date(created_at: str) -> str | None:
    """Parse HN's ISO8601 created_at into YYYY-MM-DD, or None if unparseable."""
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError, TypeError):
        return None


def _parse_tavily_date(raw: str | None) -> str | None:
    """Parse Tavily's published_date (RFC 2822, e.g. 'Tue, 28 Apr 2026 17:00:03 GMT')."""
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


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


_NOVELTY_BOOST_CATEGORIES = {"real_world_usecases", "github_trending"}


_CASE_STUDY_KEYWORDS = ("customer", "story", "case stud")


def _is_case_study_tag(tag: str) -> bool:
    lowered = tag.lower()
    return any(keyword in lowered for keyword in _CASE_STUDY_KEYWORDS)


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
        query_key = f"{tool}:{result['query']}"
        topic_type = DEFAULT_TOPIC_TYPE

        for item in result["items"]:
            original_url = None
            prefetched_content = None
            item_category = category
            if tool == "tavily":
                url = item.get("url", "")
                title = item.get("title", "")
                published_at = _parse_tavily_date(item.get("published_date"))
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
                if _is_case_study_tag(item.get("category", "")):
                    item_category = "real_world_usecases"
            elif tool == "pytorch_kr":
                url = item.get("forum_url", "")
                title = item.get("title", "")
                published_at = item.get("published_at")
                score = 0.0
                summary = item.get("content", "")
                source = "discuss.pytorch.kr"
                original_url = item.get("original_url") or url
                prefetched_content = summary
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
            else:
                continue

            if not url or not title:
                continue
            if _is_listicle_title(title):
                continue

            if item_category in _NOVELTY_BOOST_CATEGORIES:
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
                "_query_key": query_key,
            }
            if original_url is not None:
                candidate["original_url"] = original_url
                candidate["prefetched_content"] = prefetched_content
            candidates.append(candidate)

    return candidates


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


def _interleave(groups: list[list[dict]]) -> list[dict]:
    """Round-robin merge groups, one item from each per pass (each group
    already sorted by priority), so no single group — category or query —
    can crowd out the others just by being larger or declared first.
    """
    result: list[dict] = []
    depth = 0
    while any(depth < len(g) for g in groups):
        for g in groups:
            if depth < len(g):
                result.append(g[depth])
        depth += 1
    return result


def _rank_and_truncate(candidates: list[dict], max_search_results: int) -> list[dict]:
    """Interleave fairly at two levels: queries within a category, then
    categories within the run. Prevents both a high-volume query and a
    high-volume category from crowding out quieter ones. Reduces to a plain
    score sort when every candidate shares one category and one query.
    """
    by_category: dict[object, dict[object, list[dict]]] = {}
    cat_order: list[object] = []
    for c in candidates:
        cat = c.get("category")
        query_key = c.get("_query_key")
        if cat not in by_category:
            by_category[cat] = {}
            cat_order.append(cat)
        by_category[cat].setdefault(query_key, []).append(c)

    category_lists: list[list[dict]] = []
    for cat in cat_order:
        query_groups = list(by_category[cat].values())
        for group in query_groups:
            group.sort(
                key=lambda c: c["relevance_score"] if c.get("relevance_score") is not None else c["score"],
                reverse=True,
            )
        category_lists.append(_interleave(query_groups))

    return _interleave(category_lists)[:max_search_results]


def _fetch_top_candidates(candidates: list[dict], max_fetches: int, max_chars_per_source: int) -> dict[str, str]:
    """Fetch full content for the top max_fetches candidates (already ranked).

    Mutates each successfully-fetched candidate's "fetched" flag to True.
    Returns a dict mapping candidate URL -> truncated fetched content, for
    candidates that were fetched successfully.
    """
    fetched_content: dict[str, str] = {}

    for candidate in candidates[:max_fetches]:
        prefetched_content = candidate.get("prefetched_content")
        if prefetched_content is not None:
            fetched_content[candidate["url"]] = prefetched_content[:max_chars_per_source]
            candidate["fetched"] = True
            continue
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
        content = getattr(response, "content", response)
        text = content if isinstance(content, str) else str(content)
        return json.loads(text)
    except Exception:
        return []


RELEVANCE_RUBRIC = """You score AI-agent-news candidates for a Korean newsletter ("Automata") read by AI agent enthusiasts and builders.

Score each candidate 0-10 on how likely it is to make a genuinely engaging newsletter item, plus whether it's junk.

HIGH value (7-10) — the newsletter's proven winning themes:
- Practical Claude Code / coding-agent tips, workflow hacks, token-saving techniques
- Agent harness or framework comparisons (e.g. two competing open-source agent projects)
- Offbeat or whimsical real-world agent applications with genuine substance (not just a press release)
- Industry drama or controversy involving an AI platform and its developer ecosystem
- Coding/agent benchmark head-to-head comparisons
- Open-source tools solving one concrete, specific developer pain point (not generic model releases)

MEDIUM value (4-6):
- Generic new model release announcements
- Official company blog posts
- Research papers with practical deployment relevance
- General AI industry news

LOW value / JUNK (0-3) — set is_junk=true for these:
- Job postings / recruiting pages
- Bare homepage stubs or link-redirect wrapper pages with no real article content
- Generic benchmark table dumps with no narrative
- Marketing/conference promo pages
- Near-duplicate of a bigger story already covered elsewhere in this same list

Return a JSON object of the form {"results": [...]}, where "results" is an array with one object per input item, in the SAME ORDER as the input, each with exactly these keys:
- "url": string, copied exactly from input
- "score": integer 0-10
- "is_junk": boolean
- "reason": string, one short phrase (<=15 words)

Return ONLY the JSON object. No other text.
"""

_JUNK_SCORE_THRESHOLD = 3  # drop candidates scored <= this, matching the rubric's JUNK band (0-3)


def _default_relevance_scorer(items: list[dict]) -> list[dict]:
    """Score candidates for newsletter relevance in a single batch LLM call.

    Args:
        items: list of {"url", "title", "source", "category", "snippet"} dicts.

    Returns:
        List of {"url", "score", "is_junk", "reason"} dicts. Returns [] on
        any error (caller keeps existing heuristic scores unchanged).
    """
    from openai import OpenAI
    from .. import config

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.RESEARCH_RELEVANCE_MODEL,
            messages=[
                {"role": "system", "content": RELEVANCE_RUBRIC},
                {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        return parsed["results"]
    except Exception:
        return []


def _score_relevance(candidates: list[dict], scorer) -> list[str]:
    """Score every candidate's newsletter relevance in place via `scorer`,
    then drop candidates scored at or below `_JUNK_SCORE_THRESHOLD`.

    Uses the model's numeric score against a fixed threshold to decide what
    counts as junk, NOT the model's own is_junk boolean — testing showed the
    boolean cutoff disagreed with the score-based judgment more often than
    the underlying reasoning actually differed (boundary noise, not a real
    quality signal). is_junk is still stored on the candidate for visibility.

    Returns a list of error messages (empty on full success). Never raises;
    on any failure, candidates keep score=None and nothing is dropped, so
    the pipeline falls back to the existing heuristic-score ranking.
    """
    if not candidates:
        return []

    items = [
        {
            "url": c["url"],
            "title": c["title"],
            "source": c["source"],
            "category": c["category"],
            "snippet": (c.get("summary") or "")[:300],
        }
        for c in candidates
    ]

    errors: list[str] = []
    try:
        results = scorer(items)
    except Exception as exc:
        results = []
        errors.append(f"relevance_scorer: {exc}")

    by_url = {r["url"]: r for r in results if isinstance(r, dict) and "url" in r}
    if not by_url:
        errors.append("relevance_scorer: no valid scores returned, skipping relevance filter")
        for c in candidates:
            c["relevance_score"] = None
            c["is_junk"] = False
        return errors

    for c in candidates:
        r = by_url.get(c["url"])
        c["relevance_score"] = r.get("score") if r else None
        c["is_junk"] = bool(r.get("is_junk")) if r else False

    return errors


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


def _collect_weekly_research_core(
    publication_date: str,
    max_search_results: int = 30,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
    summarizer=None,
    relevance_scorer=None,
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

    # Score relevance on the full deduped/date-filtered pool, before
    # truncation, so the LLM judgment actually drives what survives.
    if relevance_scorer is None:
        relevance_scorer = _default_relevance_scorer
    errors.extend(_score_relevance(candidates, relevance_scorer))
    candidates = [
        c for c in candidates
        if not (c.get("relevance_score") is not None and c["relevance_score"] <= _JUNK_SCORE_THRESHOLD)
    ]

    candidates = _rank_and_truncate(candidates, max_search_results)

    fetched_content = _fetch_top_candidates(candidates, max_fetches, max_chars_per_source)
    total_fetched = len(fetched_content)

    # prefetched_content duplicates summary for PyTorch-KR candidates; drop it
    # before persisting so the forum text does not ship twice.
    for candidate in candidates:
        candidate.pop("prefetched_content", None)
        candidate.pop("_query_key", None)

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
    max_search_results: int = 30,
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


def load_candidates(publication_date: str) -> list[dict]:
    """Read cached candidates for a date. Returns [] if absent or unreadable."""
    path = Path("artifacts") / "research" / publication_date / "candidates.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def run_weekly_research(publication_date: str) -> str:
    """이번 주 AI/LLM 뉴스 후보를 수집해 research_results.md 파일로 저장합니다.

    후보 목록 자체는 반환하지 않습니다. 사용자가 파일과 토픽 선택 화면에서 직접 확인합니다.
    이전에 같은 날짜로 수집한 결과가 있으면 재사용합니다.

    Args:
        publication_date: 뉴스레터 발행일 (YYYY-MM-DD 형식)

    Returns:
        수집 결과 한 줄 요약 (후보 개수와 저장 경로)
    """
    cached = load_candidates(publication_date)
    if cached:
        result = {"publication_date": publication_date, "candidates": cached}
    else:
        result = json.loads(collect_weekly_research(publication_date))

    path = Path(ARTICLES_DIR) / publication_date / "research_results.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_research_results(result), encoding="utf-8")

    errors = result.get("errors") or []
    note = f" (오류 {len(errors)}건)" if errors else ""
    return f"후보 {len(result.get('candidates', []))}개 수집 완료{note}. {path}"