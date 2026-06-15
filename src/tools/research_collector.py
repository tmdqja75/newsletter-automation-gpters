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
