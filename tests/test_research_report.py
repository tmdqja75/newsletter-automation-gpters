"""Pure rendering and parsing of research candidates. No mocks needed."""

import pytest

from src.tools.research_report import (
    auto_select,
    parse_selection,
    render_research_results,
    render_selection_list,
)


def _candidate(n: int, **overrides) -> dict:
    base = {
        "title": f"토픽 {n}",
        "url": f"https://example.com/{n}",
        "source": "example.com",
        "published_at": "2026-08-01",
        "summary": f"요약 {n}",
        "key_facts": [f"사실 {n}"],
        "why_it_matters": f"중요성 {n}",
        "topic_type": "main",
        "category": "agents_automation",
        "score": 0.5,
        "fetched": True,
    }
    base.update(overrides)
    return base


def test_render_numbers_every_candidate_and_keeps_urls():
    result = {"publication_date": "2026-08-05", "candidates": [_candidate(i) for i in range(1, 4)]}
    out = render_research_results(result)
    assert "## 1. 토픽 1" in out
    assert "## 2. 토픽 2" in out
    assert "## 3. 토픽 3" in out
    assert "https://example.com/3" in out


def test_render_surfaces_errors_block():
    result = {"publication_date": "2026-08-05", "candidates": [], "errors": ["tavily: timeout"]}
    assert "tavily: timeout" in render_research_results(result)


def test_render_omits_errors_block_when_clean():
    result = {"publication_date": "2026-08-05", "candidates": [_candidate(1)]}
    assert "수집 중 오류" not in render_research_results(result)


def test_render_shows_original_url_only_when_different():
    same = _candidate(1, original_url="https://example.com/1")
    diff = _candidate(2, original_url="https://origin.example.com/2")
    assert "원문 URL" not in render_research_results({"candidates": [same]})
    assert "https://origin.example.com/2" in render_research_results({"candidates": [diff]})


def test_selection_list_numbering_matches_full_report():
    """The regression test for the drift bug: both renderers agree on numbering."""
    candidates = [_candidate(i) for i in range(1, 6)]
    report = render_research_results({"publication_date": "2026-08-05", "candidates": candidates})
    listing = render_selection_list(candidates)
    for i in range(1, 6):
        assert f"## {i}. 토픽 {i}" in report
        assert f"{i}. [" in listing and f"토픽 {i}" in listing


def test_parse_selection_returns_the_indexed_candidates():
    candidates = [_candidate(i) for i in range(1, 6)]
    picked = parse_selection("3,5", candidates, expected=2)
    assert [c["url"] for c in picked] == ["https://example.com/3", "https://example.com/5"]


@pytest.mark.parametrize("raw", ["3, 5", "3번,5번", "3，5", " 3 5 "])
def test_parse_selection_tolerates_messy_input(raw):
    candidates = [_candidate(i) for i in range(1, 6)]
    assert [c["title"] for c in parse_selection(raw, candidates, expected=2)] == ["토픽 3", "토픽 5"]


def test_parse_selection_rejects_wrong_count():
    with pytest.raises(ValueError, match="2개"):
        parse_selection("1,2,3", [_candidate(i) for i in range(1, 6)], expected=2)


def test_parse_selection_rejects_out_of_range():
    with pytest.raises(ValueError, match="범위"):
        parse_selection("1,99", [_candidate(i) for i in range(1, 6)], expected=2)


def test_parse_selection_rejects_empty():
    with pytest.raises(ValueError):
        parse_selection("", [_candidate(1)], expected=1)


def test_auto_select_takes_top_n_in_order():
    candidates = [_candidate(i) for i in range(1, 6)]
    assert [c["title"] for c in auto_select(candidates, 3)] == ["토픽 1", "토픽 2", "토픽 3"]


def test_auto_select_reserves_a_study_cafe_slot_last():
    candidates = [_candidate(i) for i in range(1, 5)] + [_candidate(9, topic_type="study_cafe")]
    picked = auto_select(candidates, 3)
    assert [c["title"] for c in picked] == ["토픽 1", "토픽 2", "토픽 9"]
    assert picked[-1]["topic_type"] == "study_cafe"


def test_auto_select_handles_n_larger_than_pool_and_zero():
    candidates = [_candidate(1), _candidate(2)]
    assert len(auto_select(candidates, 10)) == 2
    assert auto_select(candidates, 0) == []
