"""run_weekly_research writes the file and returns only a receipt."""

import json
from pathlib import Path

from src.tools import research_collector


def _candidate(n: int) -> dict:
    return {
        "title": f"토픽 {n}",
        "url": f"https://example.com/{n}",
        "source": "example.com",
        "published_at": "2026-08-01",
        "summary": f"요약 {n}",
        "key_facts": [],
        "why_it_matters": "",
        "topic_type": "main",
        "category": "agents_automation",
        "score": 0.5,
        "fetched": True,
    }


def _write_cache(date: str, candidates: list[dict]) -> None:
    path = Path("artifacts") / "research" / date / "candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")


def test_load_candidates_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert research_collector.load_candidates("2026-08-05") == []


def test_load_candidates_reads_the_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1)])
    assert research_collector.load_candidates("2026-08-05")[0]["title"] == "토픽 1"


def test_load_candidates_survives_corrupt_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path("artifacts") / "research" / "2026-08-05" / "candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json", encoding="utf-8")
    assert research_collector.load_candidates("2026-08-05") == []


def test_run_weekly_research_writes_file_and_returns_receipt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        research_collector,
        "collect_weekly_research",
        lambda date: json.dumps({"publication_date": date, "candidates": [_candidate(1), _candidate(2)]}),
    )

    receipt = research_collector.run_weekly_research("2026-08-05")

    written = Path("articles/2026-08-05/research_results.md").read_text(encoding="utf-8")
    assert "## 1. 토픽 1" in written
    assert "후보 2개" in receipt
    assert "articles/2026-08-05/research_results.md" in receipt


def test_run_weekly_research_receipt_never_leaks_candidates(tmp_path, monkeypatch):
    """Regression guard: the candidate payload must not re-enter the model context."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        research_collector,
        "collect_weekly_research",
        lambda date: json.dumps({"publication_date": date, "candidates": [_candidate(1)]}),
    )

    receipt = research_collector.run_weekly_research("2026-08-05")

    assert "https://example.com/1" not in receipt
    assert "요약 1" not in receipt
    assert len(receipt) < 200


def test_run_weekly_research_reuses_cache_without_searching(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1)])

    def explode(date):
        raise AssertionError("collect_weekly_research must not run when cache exists")

    monkeypatch.setattr(research_collector, "collect_weekly_research", explode)

    assert "후보 1개" in research_collector.run_weekly_research("2026-08-05")


def test_run_weekly_research_reports_error_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        research_collector,
        "collect_weekly_research",
        lambda date: json.dumps({"publication_date": date, "candidates": [], "errors": ["tavily: timeout"]}),
    )

    receipt = research_collector.run_weekly_research("2026-08-05")

    assert "후보 0개" in receipt
    assert "오류 1건" in receipt


def _raw_item(n: int, published: str = "2026-08-01") -> dict:
    return {
        "category": "agents_automation",
        "tool": "tavily",
        "query": "q",
        "items": [{
            "url": f"https://example.com/raw{n}",
            "title": f"원본 토픽 {n}",
            "published_date": published,
            "score": 0.5,
            "content": f"요약 {n}",
        }],
    }


def _write_raw(date: str, raw: list[dict]) -> None:
    path = Path("artifacts") / "research" / date / "raw_search_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")


def test_load_more_candidates_returns_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert research_collector.load_more_candidates("2026-08-05", set(), 5) == []


def test_load_more_candidates_excludes_seen_urls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_raw("2026-08-05", [_raw_item(1), _raw_item(2)])

    more = research_collector.load_more_candidates(
        "2026-08-05", {"https://example.com/raw1"}, 5
    )

    assert [c["url"] for c in more] == ["https://example.com/raw2"]


def test_load_more_candidates_respects_count_cap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_raw("2026-08-05", [_raw_item(i) for i in range(1, 6)])

    more = research_collector.load_more_candidates("2026-08-05", set(), 2)

    assert len(more) == 2


from src.tools import interrupt_tools


def test_request_topic_selection_resolves_numbers_in_python(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(i) for i in range(1, 6)])
    monkeypatch.setattr(interrupt_tools, "interrupt", lambda payload: "2,4")

    picked = json.loads(interrupt_tools.request_topic_selection("2026-08-05", 2, []))

    assert [c["url"] for c in picked] == ["https://example.com/2", "https://example.com/4"]


def test_request_topic_selection_payload_comes_from_disk(tmp_path, monkeypatch):
    """The list the user sees is rendered from the cache, not from a model argument."""
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1), _candidate(2)])
    seen = {}

    def capture(payload):
        seen.update(payload)
        return "1"

    monkeypatch.setattr(interrupt_tools, "interrupt", capture)
    interrupt_tools.request_topic_selection("2026-08-05", 1, ["확정 토픽"])

    assert seen["type"] == "topic_selection"
    assert "토픽 1" in seen["topics"]
    assert seen["confirmed"] == ["확정 토픽"]
    assert seen["open_slots"] == 1
    assert seen["total"] == 2


def test_request_topic_selection_guards_empty_candidates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def explode(payload):
        raise AssertionError("must not interrupt against an empty list")

    monkeypatch.setattr(interrupt_tools, "interrupt", explode)

    assert interrupt_tools.request_topic_selection("2026-08-05", 2, []).startswith("오류:")


def test_request_topic_selection_retries_on_bad_input_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1), _candidate(2)])
    answers = iter(["99", "1"])
    monkeypatch.setattr(interrupt_tools, "interrupt", lambda payload: next(answers))

    picked = json.loads(interrupt_tools.request_topic_selection("2026-08-05", 1, []))

    assert [c["url"] for c in picked] == ["https://example.com/1"]


def test_request_topic_selection_supports_partial_pick_then_cycle(tmp_path, monkeypatch):
    """User picks 1 from the first batch, cycles, then picks the rest from a new batch."""
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1), _candidate(2)])
    monkeypatch.setattr(
        interrupt_tools, "load_more_candidates", lambda date, seen, count: [_candidate(3)]
    )
    answers = iter(["1", "c", "1"])
    monkeypatch.setattr(interrupt_tools, "interrupt", lambda payload: next(answers))

    picked = json.loads(interrupt_tools.request_topic_selection("2026-08-05", 2, []))

    assert [c["url"] for c in picked] == ["https://example.com/1", "https://example.com/3"]


def test_request_topic_selection_cycle_exhausted_shows_message_and_recovers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1), _candidate(2)])
    monkeypatch.setattr(interrupt_tools, "load_more_candidates", lambda date, seen, count: [])
    captured = []
    answers = iter(["c", "1"])

    def fake_interrupt(payload):
        captured.append(payload)
        return next(answers)

    monkeypatch.setattr(interrupt_tools, "interrupt", fake_interrupt)

    picked = json.loads(interrupt_tools.request_topic_selection("2026-08-05", 1, []))

    assert [c["url"] for c in picked] == ["https://example.com/1"]
    assert captured[1]["message"] == "더 이상 보여줄 후보가 없습니다."


def test_auto_select_topics_matches_hitl_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(i) for i in range(1, 6)])

    picked = json.loads(interrupt_tools.auto_select_topics("2026-08-05", 2))

    assert len(picked) == 2
    assert picked[0]["url"] == "https://example.com/1"


def test_auto_select_topics_guards_empty_candidates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert interrupt_tools.auto_select_topics("2026-08-05", 2).startswith("오류:")
