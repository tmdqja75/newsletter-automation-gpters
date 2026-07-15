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

from .search_tools import search_ai_news, search_hackernews, search_pytorch_kr_forum
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
    {"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None},
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
            original_url = None
            prefetched_content = None
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
            elif tool == "pytorch_kr":
                url = item.get("forum_url", "")
                title = item.get("title", "")
                published_at = item.get("published_at")
                score = 0.0
                summary = item.get("content", "")
                source = "discuss.pytorch.kr"
                original_url = item.get("original_url") or url
                prefetched_content = summary
            else:
                continue

            if not url or not title:
                continue

            if category == "real_world_usecases":
                score += 0.3
            if not published_at:
                score -= 0.5

            candidate = {
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


def _rank_and_truncate(candidates: list[dict], max_search_results: int) -> list[dict]:
    """Sort candidates by score (descending) and truncate to max_search_results."""
    ranked = sorted(candidates, key=lambda c: c["score"], reverse=True)
    return ranked[:max_search_results]


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