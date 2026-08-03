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
