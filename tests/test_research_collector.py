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
