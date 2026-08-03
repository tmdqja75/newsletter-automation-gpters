# Research Process Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four-hop LLM transcription chain between `collect_weekly_research()` and HITL topic selection with Python rendering, and add a schema-backed `topic-researcher` subagent for user-named topics.

**Architecture:** `collect_weekly_research()` already returns ranked structured candidates. A new stdlib-only module renders them to markdown and parses selections back to dicts, so the number the user picks indexes the same list that was rendered. The orchestrator calls `run_weekly_research` (returns a one-line receipt, never the candidates) concurrently with `topic-researcher` calls, then one selection tool that resolves numbers to topics in Python.

**Tech Stack:** Python 3.11+, `deepagents` 0.6.8, `langgraph` 1.2.4, `pydantic` (transitive via langchain), `pytest`, `uv`.

**Spec:** `docs/superpowers/specs/2026-08-03-research-process-cleanup-design.md`

## Global Constraints

- Package manager is `uv`. Run tests with `uv run pytest`. Never use pip or poetry.
- All user-facing strings and prompts are Korean. Docstrings on agent tools are Korean (the model reads them); docstrings on internal helpers are English.
- Do not modify the collector pipeline itself (`_run_searches`, `_normalize_candidates`, `_dedupe_candidates`, `_date_filter`, `_rank_and_truncate`, `_fetch_top_candidates`, `_summarize_candidates`, `_persist_artifacts`). The only change to existing collector code is a one-line `prefetched_content` pop.
- `src/tools/research_report.py` must import only from the standard library. No filesystem, no network, no model calls. This is what makes its tests mock-free.
- `candidates.json` stays at `artifacts/research/{date}/candidates.json`. Do not move it — `tests/test_research_collector.py:363` asserts the path.
- The candidate dict shape is fixed: `title, url, source, published_at, summary, key_facts, why_it_matters, topic_type, category, score, fetched`, plus optional `original_url`. `TopicResearch` mirrors it.
- Existing tests in `tests/test_research_collector.py` (476 lines), `tests/test_pytorch_kr_*.py`, `tests/test_blog_scraping.py`, `tests/test_email_flow.py` must keep passing untouched.
- No new third-party dependencies.

## File Structure

**Create:**
- `src/tools/research_report.py` — pure render/parse (~90 lines)
- `src/agents/topic_researcher.py` — `TopicResearch` schema + subagent dict (~35 lines)
- `tests/test_research_report.py`
- `tests/test_topic_selection.py`
- `tests/test_interrupt_loop.py`

**Modify:**
- `src/tools/research_collector.py` — `+load_candidates`, `+run_weekly_research`, one pop
- `src/tools/interrupt_tools.py` — rewritten (20 → ~45 lines)
- `src/config.py` — `-RESEARCH_AGENT_PROMPT`, `-TOPIC_SELECTOR_PROMPT`, `+TOPIC_RESEARCHER_PROMPT`, shrink `ORCHESTRATOR_PROMPT`
- `src/agents/__init__.py` — export swap
- `src/main.py` — flat interrupt loop, tool registration by mode (507 → ~300 lines)
- `run.py` — `--count`, `--refresh`
- `tests/test_agents_wiring.py`, `tests/test_prompts.py`, `tests/test_research_collector.py:472`
- `CLAUDE.md`, `README.md`

**Delete:**
- `src/agents/research.py`
- `src/agents/topic_selector.py`

---

### Task 1: Pure render and parse module

The foundation. Everything else consumes these functions. Zero dependencies means zero mocks.

**Files:**
- Create: `src/tools/research_report.py`
- Test: `tests/test_research_report.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `CATEGORY_LABELS_KO: dict[str, str]`
  - `render_research_results(result: dict) -> str`
  - `render_selection_list(candidates: list[dict]) -> str`
  - `parse_selection(text, candidates: list[dict], expected: int) -> list[dict]` — raises `ValueError`
  - `auto_select(candidates: list[dict], n: int) -> list[dict]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_research_report.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_research_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.tools.research_report'`

- [ ] **Step 3: Write minimal implementation**

Create `src/tools/research_report.py`:

```python
"""Render research candidates to text and parse selections back to candidates.

Pure: stdlib only, no filesystem, no network, no model. render_research_results
and render_selection_list both enumerate the same list, and parse_selection
indexes back into it, so the numbering the user sees is the numbering they get.
"""

import re

CATEGORY_LABELS_KO = {
    "model_releases": "모델발표",
    "agents_automation": "에이전트",
    "research_papers": "연구",
    "tools_infra": "도구",
    "industry_business": "산업동향",
    "policy_society": "정책",
    "study_resources": "학습자료",
    "real_world_usecases": "활용사례",
    "official_blogs": "공식블로그",
    "pytorch_kr_community": "커뮤니티",
}


def _importance(candidate: dict) -> str:
    """Apply the rule the old research prompt asked a model to eyeball.

    The score formula in research_collector already encodes it:
    real_world_usecases +0.3, HN >50 points +0.2, missing date -0.5.
    """
    score = candidate.get("score") or 0
    if candidate.get("category") == "real_world_usecases" or score >= 0.8:
        return "높음"
    return "중간" if score >= 0.4 else "낮음"


def _label(candidate: dict) -> str:
    category = candidate.get("category", "")
    return CATEGORY_LABELS_KO.get(category, category or "기타")


def render_research_results(result: dict) -> str:
    """Render the full candidate report written to articles/{date}/research_results.md."""
    lines = [f"# 리서치 결과 ({result.get('publication_date', '')})", ""]

    if result.get("errors"):
        lines.append("> 수집 중 오류:")
        lines += [f"> - {error}" for error in result["errors"]]
        lines.append("")

    for i, candidate in enumerate(result.get("candidates", []), 1):
        cafe = " / 스터디카페" if candidate.get("topic_type") == "study_cafe" else ""
        lines.append(f"## {i}. {candidate['title']}")
        lines.append(f"- 카테고리: {_label(candidate)}{cafe}")
        lines.append(f"- 중요도: {_importance(candidate)}")
        lines.append(f"- 게시일: {candidate.get('published_at') or '날짜 미상'}")
        lines.append(f"- URL: {candidate['url']}")
        original = candidate.get("original_url")
        if original and original != candidate["url"]:
            lines.append(f"- 원문 URL: {original}  (사실 검증은 이 URL 우선)")
        lines.append(f"- 요약: {candidate.get('summary', '')}")
        for fact in candidate.get("key_facts") or []:
            lines.append(f"  - {fact}")
        if candidate.get("why_it_matters"):
            lines.append(f"- 왜 중요한가: {candidate['why_it_matters']}")
        lines.append("")

    return "\n".join(lines)


def render_selection_list(candidates: list[dict]) -> str:
    """Render the compact one-line-per-candidate list shown at the interrupt."""
    return "\n".join(
        f"{i:2}. [{_label(c)}] {c['title']}"
        f"  ({c.get('published_at') or '날짜 미상'}, 중요도 {_importance(c)})"
        for i, c in enumerate(candidates, 1)
    )


def parse_selection(text, candidates: list[dict], expected: int) -> list[dict]:
    """Resolve a user's "3,7" into candidate dicts. Raises ValueError on bad input."""
    numbers = [int(n) for n in re.findall(r"\d+", str(text))]

    if len(numbers) != expected:
        raise ValueError(f"토픽 {expected}개를 선택해야 합니다 (입력: {len(numbers)}개)")

    out_of_range = [n for n in numbers if not 1 <= n <= len(candidates)]
    if out_of_range:
        raise ValueError(f"1~{len(candidates)} 범위를 벗어난 번호: {out_of_range}")

    return [candidates[n - 1] for n in numbers]


def auto_select(candidates: list[dict], n: int) -> list[dict]:
    """Pick the top n (already score-sorted), reserving a study_cafe slot last."""
    if n <= 0:
        return []

    cafe = next((c for c in candidates if c.get("topic_type") == "study_cafe"), None)
    if cafe is None or n == 1:
        return candidates[:n]

    mains = [c for c in candidates if c is not cafe]
    return mains[: n - 1] + [cafe]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_research_report.py -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Commit**

```bash
git add src/tools/research_report.py tests/test_research_report.py
git commit -m "feat: add pure render/parse module for research candidates"
```

---

### Task 2: Collector cache reader and the receipt tool

`run_weekly_research` is the orchestrator's only entry to research. It writes the file and returns a receipt — the candidates never enter the model's context.

**Files:**
- Modify: `src/tools/research_collector.py` (add imports, `load_candidates`, `run_weekly_research`; one pop in `_collect_weekly_research_core`)
- Test: `tests/test_topic_selection.py`

**Interfaces:**
- Consumes: `render_research_results` from Task 1
- Produces:
  - `load_candidates(publication_date: str) -> list[dict]` — `[]` when absent or unreadable
  - `run_weekly_research(publication_date: str) -> str` — receipt string

- [ ] **Step 1: Write the failing test**

Create `tests/test_topic_selection.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_topic_selection.py -v`
Expected: FAIL — `AttributeError: module 'src.tools.research_collector' has no attribute 'load_candidates'`

- [ ] **Step 3: Write minimal implementation**

In `src/tools/research_collector.py`, extend the existing import block near the top (after `from .content_tools import ...`):

```python
from ..config import ARTICLES_DIR
from .research_report import render_research_results
```

Append at the end of the file:

```python
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
```

In `_collect_weekly_research_core`, drop the duplicated forum text right after the fetch call. Change:

```python
    fetched_content = _fetch_top_candidates(candidates, max_fetches, max_chars_per_source)
    total_fetched = len(fetched_content)
```

to:

```python
    fetched_content = _fetch_top_candidates(candidates, max_fetches, max_chars_per_source)
    total_fetched = len(fetched_content)

    # prefetched_content duplicates summary for PyTorch-KR candidates; drop it
    # before persisting so the forum text does not ship twice.
    for candidate in candidates:
        candidate.pop("prefetched_content", None)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_topic_selection.py tests/test_research_collector.py -v`
Expected: PASS — 7 new tests plus the existing 20 still green

- [ ] **Step 5: Add the pop regression assertion**

Append to `tests/test_research_collector.py`:

Note: this file imports names directly (`from src.tools.research_collector import ...`), not the module object, so monkeypatch targets use the string form.

```python
def test_core_strips_prefetched_content(monkeypatch, tmp_path):
    """prefetched_content duplicates summary and must not reach the model or disk."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.tools.research_collector._run_searches",
        lambda plan, date: (
            [{
                "category": "pytorch_kr_community",
                "tool": "pytorch_kr",
                "query": None,
                "items": [{
                    "forum_url": "https://discuss.pytorch.kr/t/1",
                    "title": "포럼 글",
                    "published_at": "2026-08-01",
                    "content": "본문" * 100,
                    "original_url": "https://origin.example.com/1",
                }],
            }],
            [],
        ),
    )
    monkeypatch.setattr("src.tools.research_collector._summarize_candidates", lambda *a, **k: [])

    result = _collect_weekly_research_core("2026-08-05")

    assert all("prefetched_content" not in c for c in result["candidates"])
```

Run: `uv run pytest tests/test_research_collector.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tools/research_collector.py tests/test_topic_selection.py tests/test_research_collector.py
git commit -m "feat: add run_weekly_research receipt tool and candidate cache reader"
```

---

### Task 3: Selection tools

Exactly one of these is registered per run. Both return the same JSON shape so the orchestrator prompt describes one flow.

**Files:**
- Modify: `src/tools/interrupt_tools.py` (full rewrite)
- Test: `tests/test_topic_selection.py` (append)

**Interfaces:**
- Consumes: `load_candidates` (Task 2); `render_selection_list`, `parse_selection`, `auto_select` (Task 1)
- Produces:
  - `request_topic_selection(publication_date: str, open_slots: int, confirmed_titles: list[str]) -> str`
  - `auto_select_topics(publication_date: str, open_slots: int) -> str`
  - Both return a JSON array of candidate dicts, or a Korean error string starting with `"오류:"`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_topic_selection.py`:

```python
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


def test_request_topic_selection_returns_error_on_bad_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(1), _candidate(2)])
    monkeypatch.setattr(interrupt_tools, "interrupt", lambda payload: "99")

    assert interrupt_tools.request_topic_selection("2026-08-05", 1, "").startswith("오류:")


def test_auto_select_topics_matches_hitl_shape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_cache("2026-08-05", [_candidate(i) for i in range(1, 6)])

    picked = json.loads(interrupt_tools.auto_select_topics("2026-08-05", 2))

    assert len(picked) == 2
    assert picked[0]["url"] == "https://example.com/1"


def test_auto_select_topics_guards_empty_candidates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert interrupt_tools.auto_select_topics("2026-08-05", 2).startswith("오류:")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_topic_selection.py -v`
Expected: FAIL — `AttributeError: module 'src.tools.interrupt_tools' has no attribute 'auto_select_topics'`

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `src/tools/interrupt_tools.py`:

```python
"""Topic selection tools. Exactly one is registered per run (HITL vs automatic).

Both load candidates from disk and resolve the user's numbers in Python, so the
list the user approves is the list that reaches the writer.
"""

import json

from langgraph.types import interrupt

from .research_collector import load_candidates
from .research_report import auto_select, parse_selection, render_selection_list

_NO_CANDIDATES = "오류: 후보가 없습니다. run_weekly_research를 먼저 호출하세요."


def request_topic_selection(publication_date: str, open_slots: int,
                            confirmed_titles: list[str]) -> str:
    """리서치 후보 목록을 사용자에게 보여주고 토픽을 직접 고르게 합니다.

    반드시 run_weekly_research가 끝난 뒤에 호출하세요.

    Args:
        publication_date: 뉴스레터 발행일 (YYYY-MM-DD 형식)
        open_slots: 사용자가 골라야 할 토픽 개수
        confirmed_titles: 이미 확정된 사용자 지정 토픽 제목 목록 (화면 표시용)

    Returns:
        선택된 토픽 정보 JSON 배열. 실패 시 "오류:"로 시작하는 문자열.
    """
    candidates = load_candidates(publication_date)
    if not candidates:
        return _NO_CANDIDATES

    selection = interrupt({
        "type": "topic_selection",
        "topics": render_selection_list(candidates),
        "confirmed": confirmed_titles,
        "open_slots": open_slots,
        "total": len(candidates),
    })

    try:
        picked = parse_selection(selection, candidates, open_slots)
    except ValueError as exc:
        return f"오류: {exc}. 이 도구를 다시 호출하세요."

    return json.dumps(picked, ensure_ascii=False)


def auto_select_topics(publication_date: str, open_slots: int) -> str:
    """리서치 후보 중 상위 토픽을 자동으로 선택합니다 (비대화형 모드).

    반드시 run_weekly_research가 끝난 뒤에 호출하세요.

    Args:
        publication_date: 뉴스레터 발행일 (YYYY-MM-DD 형식)
        open_slots: 자동으로 선택할 토픽 개수

    Returns:
        선택된 토픽 정보 JSON 배열. 실패 시 "오류:"로 시작하는 문자열.
    """
    candidates = load_candidates(publication_date)
    if not candidates:
        return _NO_CANDIDATES

    return json.dumps(auto_select(candidates, open_slots), ensure_ascii=False)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_topic_selection.py -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add src/tools/interrupt_tools.py tests/test_topic_selection.py
git commit -m "feat: resolve topic selection in python instead of model memory"
```

---

### Task 4: topic-researcher subagent, prompt rewrites, dead code removal

Swaps the transcribing `research-agent` for a schema-backed single-topic researcher, and deletes `topic-selector`, which was never registered.

**Files:**
- Create: `src/agents/topic_researcher.py`
- Delete: `src/agents/research.py`, `src/agents/topic_selector.py`
- Modify: `src/agents/__init__.py`, `src/config.py`, `tests/test_prompts.py`, `tests/test_research_collector.py:472`

**Interfaces:**
- Consumes: `search_ai_news`, `fetch_article_content` (existing)
- Produces:
  - `TopicResearch` — pydantic model mirroring the candidate dict
  - `topic_researcher_agent: dict` with `name="topic-researcher"` and `response_format=TopicResearch`
  - `config.TOPIC_RESEARCHER_PROMPT`
  - `config.ORCHESTRATOR_PROMPT` (rewritten)

- [ ] **Step 1: Write the failing test**

Replace the two prompt tests in `tests/test_prompts.py` that reference deleted prompts. Change the import block at the top from:

```python
from src.config import (
    RESEARCH_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
    TOPIC_SELECTOR_PROMPT,
)
```

to:

```python
from src.config import (
    TOPIC_RESEARCHER_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
)
```

Replace `test_research_prompt_requires_fetch` with:

```python
def test_topic_researcher_prompt_requires_fetch():
    """The researcher must be told to fetch primary sources, not just search."""
    assert "fetch_article_content" in TOPIC_RESEARCHER_PROMPT
    assert "반드시" in TOPIC_RESEARCHER_PROMPT or "필수" in TOPIC_RESEARCHER_PROMPT


def test_topic_researcher_prompt_scopes_to_one_topic():
    """It must not re-run weekly research; that is the collector's job."""
    assert "하나" in TOPIC_RESEARCHER_PROMPT
```

Delete the two tests referencing `TOPIC_SELECTOR_PROMPT` (currently at `tests/test_prompts.py:69` and `:71`); the topic-selector agent no longer exists.

Add to `tests/test_prompts.py`:

```python
def test_orchestrator_forbids_inventing_topics():
    """Zero research results must stop the run, not trigger hallucinated topics."""
    assert "지어내지" in ORCHESTRATOR_PROMPT
```

Create the agent test — append to `tests/test_agents_wiring.py`:

```python
from src.agents import topic_researcher_agent
from src.agents.topic_researcher import TopicResearch


def test_topic_researcher_returns_structured_output():
    assert topic_researcher_agent["name"] == "topic-researcher"
    assert topic_researcher_agent["response_format"] is TopicResearch
    assert search_ai_news in topic_researcher_agent["tools"]
    assert fetch_article_content in topic_researcher_agent["tools"]


def test_topic_research_schema_mirrors_candidate_shape():
    """A researched topic and a picked candidate must be the same shape downstream."""
    fields = set(TopicResearch.model_fields)
    assert fields == {
        "title", "url", "original_url", "published_at",
        "summary", "key_facts", "why_it_matters", "topic_type",
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_prompts.py tests/test_agents_wiring.py -v`
Expected: FAIL — `ImportError: cannot import name 'TOPIC_RESEARCHER_PROMPT' from 'src.config'`

- [ ] **Step 3: Rewrite the prompts**

In `src/config.py`, delete `RESEARCH_AGENT_PROMPT` (lines 69–106) and `TOPIC_SELECTOR_PROMPT` (lines 108–146) entirely. Add in their place:

```python
TOPIC_RESEARCHER_PROMPT = """당신은 AI/LLM 분야 리서치 전문가입니다.
사용자가 자연어로 지정한 토픽 **하나**만 조사합니다.

## 작업 순서
1. search_ai_news로 해당 토픽을 검색하세요. 발행 예정일의 연도와 월을 쿼리에 포함하세요.
   예: "2026년 8월 Claude Agent SDK", "August 2026 Claude Agent SDK release"
2. 검색 결과 중 가장 신뢰할 만한 1차 출처 1~3개를 fetch_article_content로 **반드시** 가져오세요.
3. 가져온 원문에 실제로 있는 내용만으로 결과를 채우세요.

## 규칙
- 공식 블로그, 논문, 1차 발표문을 요약 기사나 애그리게이터보다 우선하세요.
- 원문에 없는 수치, 날짜, 모델명은 추측하지 말고 해당 필드를 비워 두세요.
- url에는 사실 검증에 실제로 사용한 1차 출처를 넣으세요.
- 주간 전체 리서치를 하지 마세요. 지정된 토픽 하나만 깊이 조사합니다.
- 학습 자료나 튜토리얼 성격이면 topic_type을 study_cafe로 설정하세요.
"""
```

Replace `ORCHESTRATOR_PROMPT` (lines 35–67) with:

```python
ORCHESTRATOR_PROMPT = """당신은 '오토마타' AI 뉴스레터 작성을 조율하는 메인 에이전트입니다.

## 워크플로우
1. **첫 turn에서 아래를 한 번에(병렬로) 호출하세요.** 순차 호출하지 말고
   한 turn에서 tool call을 함께 내보내세요.
   - 사용자 지정 토픽이 있으면 토픽 수만큼 topic-researcher를 동시에 호출
   - 후보에서 선택할 토픽이 있으면 run_weekly_research를 호출
2. 리서치가 모두 끝난 뒤에 토픽 선택 도구를 호출하세요.
   도구가 반환한 JSON이 최종 토픽 정보입니다. 번호를 직접 해석하지 마세요.
3. 확정된 모든 토픽에 대해 article-writer를 **동시에(병렬로)** 호출하세요.
   각 호출에 제목, 요약, 출처 URL을 그대로 전달하세요.
   출처를 찾지 못한 토픽은 제목만 전달하면 article-writer가 직접 조사합니다.
4. save_article로 순서대로 저장하세요 (01_[토픽명].md, 02_[토픽명].md, ...).
   스터디 카페 토픽은 마지막 번호로 study_cafe.md에 저장하세요.
5. merge_newsletter를 호출해 최종 뉴스레터를 생성하세요.

## 금지
- 리서치 결과가 없거나 도구가 "오류:"를 반환하면 토픽을 **지어내지** 말고
  그대로 보고하고 중단하세요.
"""
```

- [ ] **Step 4: Create the subagent and delete the dead ones**

Create `src/agents/topic_researcher.py`:

```python
"""Topic research subagent: one user-named topic to a validated structured result."""

from typing import Literal

from pydantic import BaseModel, Field

from ..config import TOPIC_RESEARCHER_PROMPT
from ..tools.content_tools import fetch_article_content
from ..tools.search_tools import search_ai_news


class TopicResearch(BaseModel):
    """사용자가 지정한 토픽 하나의 리서치 결과.

    Fields mirror a collect_weekly_research candidate so a researched topic and
    a picked candidate are interchangeable downstream.
    """

    title: str = Field(description="정확한 한국어 제목")
    url: str = Field(description="사실 검증에 사용한 1차 출처 URL")
    original_url: str | None = Field(default=None, description="다른 원문 출처가 있으면")
    published_at: str | None = Field(default=None, description="YYYY-MM-DD, 모르면 null")
    summary: str = Field(description="2-3문장 한국어 요약")
    key_facts: list[str] = Field(default_factory=list, description="원문에서 확인된 사실, 최대 5개")
    why_it_matters: str = Field(default="", description="왜 중요한지 1-2문장")
    topic_type: Literal["main", "study_cafe"] = "main"


topic_researcher_agent = {
    "name": "topic-researcher",
    "description": "사용자가 자연어로 지정한 단일 토픽을 리서치해 구조화된 결과를 반환합니다.",
    "system_prompt": TOPIC_RESEARCHER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
    "response_format": TopicResearch,
}
```

Replace `src/agents/__init__.py`:

```python
"""Agent definitions for newsletter automation."""

from .topic_researcher import topic_researcher_agent
from .article_writer import article_writer_agent

__all__ = ["topic_researcher_agent", "article_writer_agent"]
```

Delete the dead agents:

```bash
git rm src/agents/research.py src/agents/topic_selector.py
```

Retarget the collector's wiring test. In `tests/test_research_collector.py`, replace `test_research_subagent_tools_wiring` (line 472) with:

```python
def test_collect_weekly_research_is_not_an_agent_tool():
    """Research is Python-driven now; no subagent should hold the collector."""
    from src.agents import article_writer_agent, topic_researcher_agent

    for agent in (article_writer_agent, topic_researcher_agent):
        assert collect_weekly_research not in agent["tools"]
```

The old test imported `src.agents.research` inside the function body, so deleting that module does not break test collection in this file.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_prompts.py tests/test_agents_wiring.py tests/test_research_collector.py -v`
Expected: `test_prompts.py` and `test_research_collector.py` PASS. `test_create_newsletter_agent_uses_article_writer` in `test_agents_wiring.py` still FAILS — it asserts `{"research-agent", "article-writer"}`, and `src/main.py` has not been updated yet. Task 5 fixes it.

- [ ] **Step 6: Commit**

```bash
git add -A src/agents src/config.py tests/test_prompts.py tests/test_agents_wiring.py tests/test_research_collector.py
git commit -m "feat: replace research-agent with schema-backed topic-researcher"
```

---

### Task 5: Flat interrupt loop and mode-based tool registration

Collapses `src/main.py:276–392` — three nested stream loops capped at two reject rounds — into one `while` loop with unbounded retries, and makes tool availability encode the run mode.

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_interrupt_loop.py`, `tests/test_agents_wiring.py`

**Interfaces:**
- Consumes: `run_weekly_research` (Task 2); `request_topic_selection`, `auto_select_topics` (Task 3); `topic_researcher_agent` (Task 4)
- Produces:
  - `create_newsletter_agent(target_date: str, open_slots: int = 4, use_hitl: bool = False)`
  - `run_newsletter_generation(target_date=None, use_hitl=False, user_topics=None, count=4) -> dict | None`
  - `_handle_event(event, metrics, final) -> tuple[Any, dict | None]`
  - `_run_with_interrupts(agent, initial, config, metrics) -> Any`

- [ ] **Step 1: Write the failing test**

Create `tests/test_interrupt_loop.py`:

```python
"""The interrupt loop must handle unbounded reject rounds, unlike the old
three-level nesting that dead-ended after two."""

from types import SimpleNamespace

import src.main as main


class _Metrics:
    def __init__(self):
        self.events = 0

    def record_stream_event(self, event):
        self.events += 1

    def record_model_message(self, msg):
        pass

    def record_tool_result(self, name):
        pass


class _ScriptedAgent:
    """Yields one interrupt per scripted round, then a final message."""

    def __init__(self, rounds: int):
        self.rounds = rounds
        self.resumes = []

    def stream(self, stream_input, config=None):
        if not isinstance(stream_input, dict):
            self.resumes.append(stream_input.resume)
        if len(self.resumes) < self.rounds:
            payload = SimpleNamespace(value={
                "type": "topic_selection",
                "topics": " 1. [에이전트] 토픽 1\n 2. [연구] 토픽 2",
                "confirmed": [],
                "open_slots": 1,
                "total": 2,
            })
            yield {"__interrupt__": [payload]}
        else:
            yield {"model": {"messages": [SimpleNamespace(content="완료", tool_calls=[])]}}


def test_loop_handles_three_interrupt_rounds(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "1")
    agent = _ScriptedAgent(rounds=3)

    final = main._run_with_interrupts(agent, {"messages": []}, {}, _Metrics())

    assert final == "완료"
    assert agent.resumes == ["1", "1", "1"]


def test_loop_returns_without_interrupts(monkeypatch):
    agent = _ScriptedAgent(rounds=0)
    assert main._run_with_interrupts(agent, {"messages": []}, {}, _Metrics()) == "완료"


def test_prompt_user_rejects_wrong_count_then_accepts(monkeypatch, capsys):
    answers = iter(["1,2", "9", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    resume = main._prompt_user({
        "type": "topic_selection",
        "topics": " 1. 토픽 1\n 2. 토픽 2",
        "confirmed": [],
        "open_slots": 1,
        "total": 2,
    })

    assert resume == "2"
    assert "1개" in capsys.readouterr().out


def test_create_agent_registers_hitl_tool_only_with_hitl(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=True)
    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "request_topic_selection" in names
    assert "auto_select_topics" not in names
    assert "checkpointer" in captured

    captured.clear()
    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=False)
    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "auto_select_topics" in names
    assert "request_topic_selection" not in names
    assert "checkpointer" not in captured


def test_create_agent_omits_research_tools_when_no_open_slots(monkeypatch):
    """Every topic named by the user means the run cannot reach Tavily."""
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    main.create_newsletter_agent("2026-08-05", open_slots=0, use_hitl=True)

    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "run_weekly_research" not in names
    assert "request_topic_selection" not in names
    assert "save_article" in names
```

Update the stale assertion in `tests/test_agents_wiring.py` — change:

```python
    assert subagent_names == {"research-agent", "article-writer"}
```

to:

```python
    assert subagent_names == {"topic-researcher", "article-writer"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_interrupt_loop.py tests/test_agents_wiring.py -v`
Expected: FAIL — `AttributeError: module 'src.main' has no attribute '_run_with_interrupts'`

- [ ] **Step 3: Rewrite the imports and agent construction**

In `src/main.py`, replace the import block at lines 15–25 with:

```python
import re

from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    to_model_spec,
)
from .agents import topic_researcher_agent, article_writer_agent
from .tools.research_collector import run_weekly_research
from .tools.interrupt_tools import auto_select_topics, request_topic_selection
from .utils.merge_articles import merge_newsletter
```

Replace `create_newsletter_agent` (lines 173–229) with:

```python
def create_newsletter_agent(target_date: str, open_slots: int = 4, use_hitl: bool = False):
    """Create the newsletter orchestrator.

    Tool registration encodes the run mode, so "should I ask the user?" and
    "should I research?" are never model decisions:
      open_slots == 0  -> no research or selection tools at all
      use_hitl         -> request_topic_selection (interrupts)
      otherwise        -> auto_select_topics (no interrupts)
    """
    Path(ARTICLES_DIR).mkdir(parents=True, exist_ok=True)

    tools = [save_article, merge_newsletter]
    if open_slots > 0:
        tools.append(run_weekly_research)
        tools.append(request_topic_selection if use_hitl else auto_select_topics)

    agent_config = {
        "model": _agent_model_spec(),
        "system_prompt": ORCHESTRATOR_PROMPT,
        "tools": tools,
        "subagents": [topic_researcher_agent, article_writer_agent],
        "backend": FilesystemBackend(root_dir=".", virtual_mode=True),
    }

    if use_hitl and open_slots > 0:
        agent_config["checkpointer"] = MemorySaver()

    return create_deep_agent(**agent_config)
```

- [ ] **Step 4: Replace the nested loops with the flat one**

Replace `run_newsletter_generation` (lines 232–417) and `run_quick_test` (lines 420–507) with:

```python
def _handle_event(event: dict, metrics, final):
    """Print one stream event. Returns (final_content, interrupt_payload_or_None)."""
    pending = None

    for key, value in event.items():
        messages = value.get("messages", []) if isinstance(value, dict) else []

        if key in ("model", "agent"):
            for msg in messages:
                metrics.record_model_message(msg)
                if getattr(msg, "content", None):
                    final = msg.content
                    print(f"📝 응답 수신 ({len(str(msg.content))} 글자)")
                for tool_call in getattr(msg, "tool_calls", None) or []:
                    print(f"🔨 도구 호출: {tool_call.get('name', 'unknown')}")

        elif key == "tools":
            for msg in messages:
                name = getattr(msg, "name", "tool")
                metrics.record_tool_result(name)
                print(f"✅ {name} 완료")

        elif key == "__interrupt__":
            for item in value:
                pending = getattr(item, "value", item)

    return final, pending


def _prompt_user(payload) -> str:
    """Render an interrupt and read a valid selection. Loops until input is sane."""
    if not isinstance(payload, dict) or payload.get("type") != "topic_selection":
        return input(f"⏸️ {payload}\n입력: ").strip()

    print("\n" + "=" * 50)
    for title in payload.get("confirmed") or []:
        print(f"✅ 확정된 토픽: {title}")
    print(payload.get("topics", ""))
    print("=" * 50)

    slots = payload.get("open_slots", 1)
    total = payload.get("total", 0)

    while True:
        raw = input(f"토픽 {slots}개를 선택하세요 (예: 3,7): ").strip()
        numbers = [int(n) for n in re.findall(r"\d+", raw)]
        if len(numbers) != slots:
            print(f"❌ {slots}개를 입력하세요 (입력: {len(numbers)}개)")
        elif any(not 1 <= n <= total for n in numbers):
            print(f"❌ 1~{total} 범위의 번호만 입력하세요")
        else:
            return raw


def _run_with_interrupts(agent, initial, config, metrics):
    """Stream the agent, pausing for input on each interrupt. Unbounded rounds."""
    stream_input, final = initial, None

    while True:
        pending = None
        for event in agent.stream(stream_input, config=config):
            metrics.record_stream_event(event)
            final, payload = _handle_event(event, metrics, final)
            pending = payload or pending
            sys.stdout.flush()

        if pending is None:
            return final

        stream_input = Command(resume=_prompt_user(pending))


def _build_prompt(target_date: str, topics: list[str], open_slots: int) -> str:
    lines = [f"{target_date} 발행 오토마타 뉴스레터를 작성해주세요.", ""]
    if topics:
        lines.append("사용자 지정 토픽 (각각 topic-researcher로 조사하세요):")
        lines += [f"- {topic}" for topic in topics]
        lines.append("")
    lines.append(f"후보에서 추가로 선택할 토픽 수: {open_slots}")
    lines.append(f"아티클 저장 디렉토리: articles/{target_date}/")
    return "\n".join(lines)


def run_newsletter_generation(target_date: str = None, use_hitl: bool = False,
                              user_topics: str = None, count: int = 4):
    """Run the full newsletter generation workflow.

    Args:
        target_date: Publication date (YYYY-MM-DD). Defaults to today.
        use_hitl: Ask the user to pick topics instead of auto-selecting.
        user_topics: Comma-separated topics to research and include.
        count: Total articles in the issue.

    Returns:
        {"final_content": ..., "metrics_path": ...} or None on failure.
    """
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    topics = [t.strip() for t in (user_topics or "").split(",") if t.strip()]
    open_slots = count - len(topics)

    print("🔧 에이전트 초기화 중...")
    if use_hitl and open_slots > 0:
        print("👤 Human-in-the-Loop 모드 활성화")

    agent = create_newsletter_agent(target_date, open_slots=open_slots, use_hitl=use_hitl)
    prompt = _build_prompt(target_date, topics, open_slots)

    print("🤖 에이전트 실행 중 (스트리밍)...\n")
    metrics = NewsletterRunMetrics(target_date, "full", _agent_model_spec())
    final_content = None

    try:
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}
        final_content = _run_with_interrupts(
            agent, {"messages": [{"role": "user", "content": prompt}]}, config, metrics
        )

        print("\n" + "=" * 40)
        print("📋 최종 결과:")
        print("=" * 40)
        print(final_content or "(응답 없음)")

        metrics_path = metrics.save("completed", final_content=final_content)
        print(f"📊 실행 메트릭 저장: {metrics_path}")
        return {"final_content": final_content, "metrics_path": metrics_path}

    except Exception as e:
        metrics_path = metrics.save("failed", final_content=final_content, error=str(e))
        print(f"\n❌ 에이전트 실행 중 오류: {e}", file=sys.stderr)
        print(f"📊 실행 메트릭 저장: {metrics_path}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def run_quick_test(target_date: str = None, use_hitl: bool = False,
                   user_topics: str = None, count: int = 1):
    """Generate a single article to smoke-test the pipeline."""
    topic = (user_topics or "AI 에이전트 최신 소식").split(",")[0].strip()
    return run_newsletter_generation(target_date, use_hitl=False, user_topics=topic, count=1)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_interrupt_loop.py tests/test_agents_wiring.py -v`
Expected: PASS, 8 tests

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -m "not integration" -v`
Expected: PASS with no edits to `tests/test_phase1_cost_controls.py`. It calls `create_newsletter_agent("2026-06-17")` positionally and only asserts on `captured["model"]`; the new `open_slots=4, use_hitl=False` defaults keep that call valid.

- [ ] **Step 7: Commit**

```bash
git add src/main.py tests/test_interrupt_loop.py tests/test_agents_wiring.py
git commit -m "refactor: flatten interrupt loop and gate tools by run mode"
```

---

### Task 6: CLI flags

`--count` sizes the issue; `--refresh` deletes the cache file rather than threading a flag through the model.

**Files:**
- Modify: `run.py`
- Test: `tests/test_interrupt_loop.py` (append)

**Interfaces:**
- Consumes: `run_newsletter_generation(target_date, use_hitl, user_topics, count)` (Task 5)
- Produces:
  - `validate_topic_count(count: int, topics: str | None) -> int` — returns `open_slots`, raises `ValueError`
  - `count_articles(target_date: str) -> int` — article files written, excluding `newsletter.md` and `research_results.md`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_interrupt_loop.py`:

```python
import pytest

import run as cli


def test_validate_topic_count_returns_open_slots():
    assert cli.validate_topic_count(4, "X, Y") == 2
    assert cli.validate_topic_count(4, None) == 4
    assert cli.validate_topic_count(2, "X, Y") == 0


def test_validate_topic_count_rejects_too_many_topics():
    with pytest.raises(ValueError, match="--count"):
        cli.validate_topic_count(2, "X, Y, Z")


def test_count_articles_ignores_generated_files(tmp_path, monkeypatch):
    """The success backstop must not count the newsletter or the research dump."""
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "articles" / "2026-08-05"
    d.mkdir(parents=True)
    for name in ("01_a.md", "02_b.md", "newsletter.md", "research_results.md"):
        (d / name).write_text("x", encoding="utf-8")

    assert cli.count_articles("2026-08-05") == 2


def test_count_articles_returns_zero_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.count_articles("2026-08-05") == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_interrupt_loop.py::test_validate_topic_count_returns_open_slots -v`
Expected: FAIL — `AttributeError: module 'run' has no attribute 'validate_topic_count'`

- [ ] **Step 3: Write minimal implementation**

In `run.py`, add after `get_next_wednesday`:

```python
def validate_topic_count(count: int, topics: str | None) -> int:
    """Return the number of slots left for candidate selection."""
    named = len([t for t in (topics or "").split(",") if t.strip()])
    if count < named:
        raise ValueError(f"--count({count})가 --topics 개수({named})보다 작습니다. --count를 늘리세요.")
    return count - named


def count_articles(target_date: str) -> int:
    """Article files actually written, excluding generated non-articles."""
    skip = {"newsletter.md", "research_results.md"}
    return len([p for p in Path(f"articles/{target_date}").glob("*.md") if p.name not in skip])
```

`Path` is already imported at `run.py:7`.

Add the two flags after the existing `--topics` argument:

```python
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=4,
        help="뉴스레터에 포함할 총 아티클 수 (기본값: 4)",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="캐시된 리서치 후보를 버리고 다시 수집",
    )
```

Replace the full-generation block (lines 102–126) with:

```python
    target_date = args.date or get_next_wednesday()

    try:
        open_slots = validate_topic_count(args.count, args.topics)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if args.refresh:
        Path(f"artifacts/research/{target_date}/candidates.json").unlink(missing_ok=True)
        print("🔄 캐시된 리서치 후보를 삭제했습니다")

    print(f"🚀 오토마타 뉴스레터 생성 시작")
    print(f"📅 발행 예정일: {target_date}")
    print(f"📝 아티클 {args.count}개 (지정 {args.count - open_slots}개 + 후보 선택 {open_slots}개)")
    print("-" * 40)

    if args.quick:
        from src.main import run_quick_test
        run_func = run_quick_test
        print("⚡ 빠른 테스트 모드 (아티클 1개만 생성)")
    else:
        from src.main import run_newsletter_generation
        run_func = run_newsletter_generation

    try:
        result = run_func(target_date, use_hitl=args.hitl, user_topics=args.topics, count=args.count)
        print("-" * 40)
        if result is None:
            print("❌ 뉴스레터 생성 실패")
            return 1

        expected = 1 if args.quick else args.count   # quick mode forces a single article
        written = count_articles(target_date)
        if written < expected:
            print(f"❌ 아티클 {expected}개 중 {written}개만 생성되었습니다", file=sys.stderr)
            print(f"📁 부분 결과: articles/{target_date}/", file=sys.stderr)
            return 1

        print("✅ 뉴스레터 생성 완료!")
        print(f"📁 결과 위치: articles/{target_date}/")
        return 0
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
        return 130
    except Exception as e:
        print(f"❌ 오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
```

Update the epilog examples:

```python
        epilog="""
예시:
  python run.py                                    # 다음 수요일 발행용, 아티클 4개
  python run.py --hitl                             # 토픽을 직접 선택
  python run.py --topics "X, Y" --count 4 --hitl   # X, Y 조사 + 후보에서 2개 선택
  python run.py --refresh                          # 리서치 캐시 무시하고 재수집
  python run.py --preview 2026-01-15               # 기존 아티클 미리보기
        """,
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_interrupt_loop.py -v`
Expected: PASS

- [ ] **Step 5: Smoke-test the CLI without spending tokens**

Run: `uv run python run.py --topics "X, Y, Z" --count 2`
Expected: exits 1 with `❌ --count(2)가 --topics 개수(3)보다 작습니다.`

Run: `uv run python run.py --help`
Expected: `--count` and `--refresh` appear in the help output

- [ ] **Step 6: Commit**

```bash
git add run.py tests/test_interrupt_loop.py
git commit -m "feat: add --count and --refresh flags"
```

---

### Task 7: Documentation

`CLAUDE.md` currently documents two agents that no longer exist and an `interrupt_on` config that never existed.

**Files:**
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Fix the agent list in CLAUDE.md**

In the "Multi-Agent System" section, delete the `Research Subagent` and `Topic Selection Agent` entries and replace with:

```markdown
2. **Topic Researcher Subagent** (`src/agents/topic_researcher.py`)
   - Researches ONE user-named topic given in natural language (`--topics`)
   - Returns a validated `TopicResearch` object via deepagents `response_format`
   - Tools: `search_ai_news`, `fetch_article_content`

3. **Weekly Research** (`src/tools/research_collector.py`) — not an agent
   - `run_weekly_research(date)` searches 10 categories, dedupes, date-filters,
     ranks, fetches, and batch-summarizes with a cheap model
   - Writes `articles/{date}/research_results.md` and caches candidates to
     `artifacts/research/{date}/candidates.json`
   - Returns only a one-line receipt; candidates never enter the model's context
```

- [ ] **Step 2: Replace the Human-in-the-Loop section**

Delete the `interrupt_on` block at `CLAUDE.md:139-147` — that config was never in the code. Replace with:

```markdown
### Human-in-the-Loop

`--hitl` swaps which selection tool is registered on the orchestrator:

| Run config | Selection tool |
|---|---|
| `--hitl`, open slots > 0 | `request_topic_selection` — interrupts, user picks by number |
| no `--hitl`, open slots > 0 | `auto_select_topics` — top-N by score |
| open slots == 0 | neither; no research tools registered at all |

`request_topic_selection` loads `candidates.json`, renders the list itself, and
resolves the user's numbers to candidate dicts in Python. The orchestrator never
sees the candidate list and never maps numbers to topics.

HITL requires a checkpointer (`MemorySaver`), wired automatically.
```

- [ ] **Step 3: Update the workflow and commands sections**

Replace the "Workflow" list with:

```markdown
1. `run.py` computes `open_slots = --count - len(--topics)`
2. Orchestrator concurrently: `topic-researcher` per named topic + `run_weekly_research`
3. Selection tool returns resolved topic dicts (user-picked or auto)
4. `article-writer` drafts all topics in parallel (research + draft + tone in one pass)
5. Articles saved to `articles/{YYYY-MM-DD}/0X_topic.md`
6. `merge_newsletter()` produces `newsletter.md`
```

Add to the Running section:

```bash
# Research X and Y, pick 2 more from candidates interactively
uv run python run.py --topics "X, Y" --count 4 --hitl

# Ignore cached research candidates and re-collect
uv run python run.py --refresh
```

- [ ] **Step 4: Update the directory tree in CLAUDE.md**

```
src/
├── config.py              # Prompts, API keys, templates
├── main.py                # Orchestrator agent and streaming loop
├── agents/
│   ├── topic_researcher.py  # Single user-named topic -> TopicResearch
│   └── article_writer.py    # Research + draft + tone in one pass
├── tools/
│   ├── search_tools.py      # Tavily, HackerNews, PyTorch-KR forum
│   ├── content_tools.py     # Article fetching, official blog RSS
│   ├── research_collector.py # Weekly pipeline + run_weekly_research
│   ├── research_report.py   # Pure render/parse (stdlib only)
│   └── interrupt_tools.py   # request_topic_selection, auto_select_topics
└── utils/
    └── merge_articles.py

artifacts/research/{DATE}/   # candidates.json, raw_search_results.json (gitignored)
articles/{DATE}/             # research_results.md, 0X_*.md, newsletter.md
```

- [ ] **Step 5: Update README architecture section**

First locate the stale claims:

```bash
grep -n "research-agent\|topic-selector\|리서치 에이전트\|토픽 선택\|interrupt_on\|--topics\|--hitl" README.md
```

Read the surrounding sections, then replace only those factual claims with the Task 7 Step 1–3 content. Keep the README's existing tone, heading levels, and diagram style — this is a portfolio document, so do not restructure it. Two claims must change wherever they appear: the system has two subagents (`topic-researcher`, `article-writer`), and weekly research is a Python pipeline rather than an agent.

Verify nothing stale survives:

```bash
grep -c "research-agent\|topic-selector" README.md
```

Expected: `0`

- [ ] **Step 6: Verify and commit**

Run: `grep -rn "research-agent\|topic-selector\|topic_selection_agent\|RESEARCH_AGENT_PROMPT\|TOPIC_SELECTOR_PROMPT" --include="*.py" --include="*.md" . | grep -v "^./docs/"`
Expected: no output

Run: `uv run pytest -m "not integration" -v`
Expected: PASS

```bash
git add CLAUDE.md README.md
git commit -m "docs: correct agent architecture and HITL description"
```

---

## Verification

After Task 7, a live end-to-end check (spends API credits):

```bash
uv run python run.py --date 2026-08-05 --topics "Claude Agent SDK" --count 3 --hitl
```

Expect: one `topic-researcher` call and one `run_weekly_research` call in the same turn → `articles/2026-08-05/research_results.md` written → numbered list printed → after entering `3,7`, exactly those two candidates' titles appear in the subsequent `article-writer` calls → three article files plus `newsletter.md`.

The determinism check: open `research_results.md` and confirm entries 3 and 7 match the two articles written.
