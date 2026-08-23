# Multiturn Feedback + Preference Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the newsletter agent take feedback on a drafted newsletter (same run, or a later `--feedback` invocation) and remember explicit user style/taste preferences across all future runs.

**Architecture:** A `SqliteSaver` checkpointer (replacing the current in-memory-only `MemorySaver`) persists each date's LangGraph thread to `memory/threads.sqlite`, keyed by the existing deterministic `thread_id = f"newsletter-{date}"`. After the first draft, `run.py` loops on `input()`, streaming each feedback message as a new turn on that thread; the orchestrator edits already-saved article files and re-merges rather than regenerating. A flat file `memory/preferences.md` holds explicit "remember this" notes, read once per process and injected into both the orchestrator's initial prompt and the `article-writer` subagent's system prompt.

**Tech Stack:** Python, `uv`, LangGraph (`langgraph-checkpoint-sqlite` — new dependency), deepagents, pytest (stdlib `unittest`-style asserts, `monkeypatch`/`tmp_path` fixtures only, no new test frameworks).

**Spec:** `docs/superpowers/specs/2026-08-23-multiturn-feedback-memory-design.md`

## Global Constraints

- Memory capture is explicit-only — no auto-inference from feedback/edits.
- `memory/` is gitignored (personal data) — covers both `preferences.md` and `threads.sqlite`.
- `thread_id` stays exactly `f"newsletter-{date}"` — no new thread-id scheme.
- Resuming a thread later requires the explicit `--feedback DATE_DIR` flag — never auto-detected from file presence.
- No new persistence backend beyond `langgraph-checkpoint-sqlite` (the standard LangGraph sqlite checkpointer) — added via `uv add`, never `pip`.
- Tests: stdlib assertions + `pytest`'s `monkeypatch`/`tmp_path`/`capsys` only, following the existing style in `tests/test_interrupt_loop.py` — no fixtures files, no mocking libraries.

---

## Task 1: Persistent SQLite checkpointer

**Files:**
- Modify: `pyproject.toml` (via `uv add`, not by hand)
- Modify: `src/config.py:35-36` (paths section)
- Modify: `src/main.py:1-33` (imports, new `_build_checkpointer`), `src/main.py:176-203` (`create_newsletter_agent`)
- Modify: `tests/test_interrupt_loop.py`
- Modify: `tests/test_agents_wiring.py:17-29`
- Modify: `tests/test_phase1_cost_controls.py:10-37`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `THREADS_DB: str` (in `src.config`), `main._build_checkpointer() -> SqliteSaver` (no args), `create_newsletter_agent(target_date, open_slots=4, use_hitl=False)` now always includes `"checkpointer"` in the kwargs passed to `create_deep_agent`.

- [ ] **Step 1: Add the dependency**

Run: `uv add langgraph-checkpoint-sqlite`

Verify it's importable:
Run: `uv run python3 -c "from langgraph.checkpoint.sqlite import SqliteSaver; print(SqliteSaver)"`
Expected: prints the class, no `ImportError`.

- [ ] **Step 2: Add `THREADS_DB` and gitignore `memory/`**

In `src/config.py`, change:
```python
# Paths
ARTICLES_DIR = "articles"
```
to:
```python
# Paths
ARTICLES_DIR = "articles"
THREADS_DB = "memory/threads.sqlite"
```

In `.gitignore`, under the `# Project specific` section (alongside `articles/`, `artifacts/`), add:
```
memory/
```

- [ ] **Step 3: Write the failing tests**

In `tests/test_interrupt_loop.py`, add near the top (after the existing imports):
```python
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
```

Add these test functions (anywhere after the existing `_ScriptedAgent`-based tests):
```python
def test_build_checkpointer_creates_sqlite_file(tmp_path, monkeypatch):
    db_path = tmp_path / "sub" / "threads.sqlite"
    monkeypatch.setattr(main, "THREADS_DB", str(db_path))

    checkpointer = main._build_checkpointer()

    assert db_path.exists()
    assert isinstance(checkpointer, SqliteSaver)


def test_create_agent_always_attaches_checkpointer(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(main, "_build_checkpointer", lambda: SimpleNamespace(name="fake"))

    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=True)
    assert "checkpointer" in captured

    captured.clear()
    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=False)
    assert "checkpointer" in captured
```

Then update the existing `test_create_agent_registers_hitl_tool_only_with_hitl` test (already in this file) to stop asserting `checkpointer` is *absent* in the no-hitl case, and to avoid touching a real sqlite file. Replace it entirely with:
```python
def test_create_agent_registers_hitl_tool_only_with_hitl(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(main, "_build_checkpointer", lambda: SimpleNamespace())

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
    assert "checkpointer" in captured
```

And update `test_create_agent_omits_research_tools_when_no_open_slots` (same file) to add the checkpointer monkeypatch so it doesn't hit disk either:
```python
def test_create_agent_omits_research_tools_when_no_open_slots(monkeypatch):
    """Every topic named by the user means the run cannot reach Tavily."""
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(main, "_build_checkpointer", lambda: SimpleNamespace())

    main.create_newsletter_agent("2026-08-05", open_slots=0, use_hitl=True)

    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "run_weekly_research" not in names
    assert "request_topic_selection" not in names
    assert "save_article" in names
```

In `tests/test_agents_wiring.py`, update `test_create_newsletter_agent_uses_article_writer` to add the same monkeypatch:
```python
def test_create_newsletter_agent_uses_article_writer(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr("src.main._build_checkpointer", lambda: SimpleNamespace())

    create_newsletter_agent("2026-06-17")

    subagent_names = {sa["name"] for sa in captured["subagents"]}
    assert subagent_names == {"topic-researcher", "article-writer"}
```

In `tests/test_phase1_cost_controls.py`, add the same monkeypatch line to both `test_create_newsletter_agent_uses_configured_model` and `test_create_newsletter_agent_preserves_provider_model_prefix`, right after their existing `monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)` line:
```python
monkeypatch.setattr("src.main._build_checkpointer", lambda: SimpleNamespace())
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_interrupt_loop.py tests/test_agents_wiring.py tests/test_phase1_cost_controls.py -v`
Expected: `test_build_checkpointer_creates_sqlite_file` and `test_create_agent_always_attaches_checkpointer` FAIL (`AttributeError: module 'src.main' has no attribute '_build_checkpointer'`); the other updated tests FAIL on the `assert "checkpointer" in captured` lines (checkpointer currently absent in the no-hitl case).

- [ ] **Step 5: Implement**

In `src/main.py`, replace the import:
```python
from langgraph.checkpoint.memory import MemorySaver
```
with:
```python
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
```
(keep `import json`, `import sys`, `import time` etc. as-is; add `import sqlite3` alongside them near the top of the file).

Update the config import to include `THREADS_DB`:
```python
from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    THREADS_DB,
    to_model_spec,
)
```

Add a new function, near `create_newsletter_agent`:
```python
def _build_checkpointer() -> SqliteSaver:
    """Persistent checkpointer so a thread's message history survives process restarts."""
    Path(THREADS_DB).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(THREADS_DB, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer
```

In `create_newsletter_agent`, replace:
```python
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
with:
```python
    agent_config = {
        "model": _agent_model_spec(),
        "system_prompt": ORCHESTRATOR_PROMPT,
        "tools": tools,
        "subagents": [topic_researcher_agent, article_writer_agent],
        "backend": FilesystemBackend(root_dir=".", virtual_mode=True),
        "checkpointer": _build_checkpointer(),
    }

    return create_deep_agent(**agent_config)
```
(the `subagents` line changes again in Task 2 — leave `article_writer_agent` as-is here.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_interrupt_loop.py tests/test_agents_wiring.py tests/test_phase1_cost_controls.py -v`
Expected: all PASS.

- [ ] **Step 7: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS (no other test calls `create_newsletter_agent` without the monkeypatch).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/config.py src/main.py tests/test_interrupt_loop.py tests/test_agents_wiring.py tests/test_phase1_cost_controls.py .gitignore
git commit -m "feat: persist newsletter threads with a SQLite checkpointer"
```

---

## Task 2: Preference-aware article-writer subagent

**Files:**
- Modify: `src/agents/article_writer.py`
- Modify: `src/agents/__init__.py`
- Modify: `src/main.py` (import line, `subagents` list in `create_newsletter_agent`)
- Modify: `tests/test_agents_wiring.py:1-15`
- Modify: `tests/test_research_collector.py:812-817`

**Interfaces:**
- Consumes: `ARTICLE_WRITER_PROMPT` (from `src.config`, unchanged).
- Produces: `build_article_writer_agent(preferences: str = "") -> dict` (replaces the static `article_writer_agent` dict; same keys: `name`, `description`, `system_prompt`, `tools`).

- [ ] **Step 1: Write the failing tests**

Replace the top of `tests/test_agents_wiring.py` (the import and first test) with:
```python
"""Tests that the article-writer subagent is correctly configured and wired in."""

from types import SimpleNamespace

from src.agents import build_article_writer_agent
from src.main import create_newsletter_agent
from src.tools.content_tools import fetch_article_content
from src.tools.search_tools import search_ai_news


def test_article_writer_agent_has_research_tools():
    agent = build_article_writer_agent()
    assert agent["name"] == "article-writer"
    assert search_ai_news in agent["tools"]
    assert fetch_article_content in agent["tools"]


def test_article_writer_agent_includes_preferences_in_prompt():
    agent = build_article_writer_agent("이모지 쓰지 마세요")
    assert "이모지 쓰지 마세요" in agent["system_prompt"]


def test_article_writer_agent_omits_preferences_section_when_empty():
    agent = build_article_writer_agent("")
    assert "사용자 선호" not in agent["system_prompt"]
```
(leave the rest of the file — `test_create_newsletter_agent_uses_article_writer` and the topic-researcher tests below it — unchanged.)

In `tests/test_research_collector.py`, replace:
```python
def test_collect_weekly_research_is_not_an_agent_tool():
    """Research is Python-driven now; no subagent should hold the collector."""
    from src.agents import article_writer_agent, topic_researcher_agent

    for agent in (article_writer_agent, topic_researcher_agent):
        assert collect_weekly_research not in agent["tools"]
```
with:
```python
def test_collect_weekly_research_is_not_an_agent_tool():
    """Research is Python-driven now; no subagent should hold the collector."""
    from src.agents import build_article_writer_agent, topic_researcher_agent

    for agent in (build_article_writer_agent(), topic_researcher_agent):
        assert collect_weekly_research not in agent["tools"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_research_collector.py::test_collect_weekly_research_is_not_an_agent_tool -v`
Expected: FAIL with `ImportError: cannot import name 'build_article_writer_agent'`.

- [ ] **Step 3: Implement**

Replace `src/agents/article_writer.py` entirely with:
```python
"""Article writing subagent: researches, drafts, and tone-edits in one pass."""

from ..tools.search_tools import search_ai_news
from ..tools.content_tools import fetch_article_content
from ..config import ARTICLE_WRITER_PROMPT


def build_article_writer_agent(preferences: str = "") -> dict:
    """Build the article-writer subagent dict, with user preferences appended
    to its system prompt so tone/style choices honor them directly."""
    system_prompt = ARTICLE_WRITER_PROMPT
    if preferences:
        system_prompt += f"\n\n## 사용자 선호 (기억된 내용)\n{preferences.strip()}\n"

    return {
        "name": "article-writer",
        "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성합니다.",
        "system_prompt": system_prompt,
        "tools": [search_ai_news, fetch_article_content],
    }
```

Replace `src/agents/__init__.py` with:
```python
"""Agent definitions for newsletter automation."""

from .topic_researcher import topic_researcher_agent
from .article_writer import build_article_writer_agent

__all__ = ["topic_researcher_agent", "build_article_writer_agent"]
```

In `src/main.py`, change the import:
```python
from .agents import topic_researcher_agent, article_writer_agent
```
to:
```python
from .agents import topic_researcher_agent, build_article_writer_agent
```

In `create_newsletter_agent`, change:
```python
        "subagents": [topic_researcher_agent, article_writer_agent],
```
to:
```python
        "subagents": [topic_researcher_agent, build_article_writer_agent(preferences)],
```
This introduces a new `preferences` parameter — add it to the function signature:
```python
def create_newsletter_agent(target_date: str, open_slots: int = 4, use_hitl: bool = False, preferences: str = ""):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agents_wiring.py tests/test_research_collector.py::test_collect_weekly_research_is_not_an_agent_tool -v`
Expected: all PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/agents/article_writer.py src/agents/__init__.py src/main.py tests/test_agents_wiring.py tests/test_research_collector.py
git commit -m "refactor: build article-writer subagent per-run with preferences"
```

---

## Task 3: Preference memory — read, inject into prompts

**Files:**
- Modify: `src/config.py:35-58` (paths + `ORCHESTRATOR_PROMPT`)
- Modify: `src/main.py` (import, new `_read_memory`, `_build_prompt` signature, `run_newsletter_generation` wiring)
- New: `tests/test_feedback_memory.py`
- Modify: `tests/test_prompts.py`

**Interfaces:**
- Consumes: `create_newsletter_agent(..., preferences: str = "")` (Task 2), `build_article_writer_agent(preferences)` (Task 2).
- Produces: `MEMORY_FILE: str` (in `src.config`), `main._read_memory() -> str`, `main._build_prompt(target_date, topics, open_slots, preferences) -> str` (adds a 4th required positional param).

- [ ] **Step 1: Write the failing tests**

In `src/config.py`, this step's tests reference `MEMORY_FILE` and new `ORCHESTRATOR_PROMPT` text — write the tests first, they'll fail until Step 3.

Create `tests/test_feedback_memory.py`:
```python
"""Tests for preference-memory reading and prompt injection."""

from pathlib import Path

import src.main as main


def test_read_memory_returns_empty_string_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")

    assert main._read_memory() == ""


def test_read_memory_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "preferences.md").write_text("이모지 쓰지 마세요", encoding="utf-8")

    assert main._read_memory() == "이모지 쓰지 마세요"


def test_build_prompt_includes_preferences_when_present():
    prompt = main._build_prompt("2026-08-05", [], 4, "이모지 쓰지 마세요")
    assert "이모지 쓰지 마세요" in prompt
    assert "사용자 선호" in prompt


def test_build_prompt_omits_preferences_section_when_empty():
    prompt = main._build_prompt("2026-08-05", [], 4, "")
    assert "사용자 선호" not in prompt
```

In `tests/test_prompts.py`, add:
```python
def test_orchestrator_handles_feedback_by_editing_saved_files():
    """Revisions must patch existing article files, not regenerate everything."""
    assert "merge_newsletter" in ORCHESTRATOR_PROMPT
    assert "피드백" in ORCHESTRATOR_PROMPT


def test_orchestrator_infers_preferences_without_explicit_trigger():
    """Taste signals in feedback must be saved without requiring a "remember" keyword."""
    assert "memory/preferences.md" in ORCHESTRATOR_PROMPT
    assert "덧붙여" in ORCHESTRATOR_PROMPT
    assert "취향" in ORCHESTRATOR_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_feedback_memory.py tests/test_prompts.py -v`
Expected: `test_read_memory_*` FAIL with `AttributeError` (no `_read_memory`/`MEMORY_FILE` yet); `test_build_prompt_*` FAIL with `TypeError` (missing positional arg); the two new `test_prompts.py` tests FAIL on missing substrings.

- [ ] **Step 3: Implement**

In `src/config.py`, change:
```python
# Paths
ARTICLES_DIR = "articles"
THREADS_DB = "memory/threads.sqlite"
```
to:
```python
# Paths
ARTICLES_DIR = "articles"
THREADS_DB = "memory/threads.sqlite"
MEMORY_FILE = "memory/preferences.md"
```

In `ORCHESTRATOR_PROMPT`, replace the ending:
```python
## 금지
- 리서치 결과가 없거나 도구가 "오류:"를 반환하면 토픽을 **지어내지** 말고
  그대로 보고하고 중단하세요.
"""
```
with:
```python
## 금지
- 리서치 결과가 없거나 도구가 "오류:"를 반환하면 토픽을 **지어내지** 말고
  그대로 보고하고 중단하세요.

## 피드백 반영 (후속 대화)
초안 완성 후 사용자가 피드백을 보내면, 전체를 다시 쓰지 말고 이미 저장된
아티클 파일(articles/{date}/*.md)을 직접 읽고 피드백이 가리키는 파일만
수정한 뒤 merge_newsletter를 다시 호출해 뉴스레터를 갱신하세요.

## 선호 기억하기
사용자의 피드백에서 취향이나 문체 선호가 드러나면(예: "이모지 빼줘",
"더 짧게 써줘" 같은 명시적 요청이든, 수정 지시에 취향이 묻어나는
암묵적인 경우든) "기억해줘" 같은 명시적인 말이 없어도 그 내용을 한 줄로
요약해 memory/preferences.md 파일에 **즉시 덧붙여 추가**하세요(기존 내용을
지우거나 덮어쓰지 말고, 저장 여부를 먼저 묻지도 마세요). 저장한 뒤 무엇을
기억했는지 답변에서 간단히 알려주세요. 단순 오탈자나 사실 정정처럼 취향과
무관한 피드백은 저장하지 마세요.
"""
```

In `src/main.py`, update the config import to add `MEMORY_FILE`:
```python
from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    THREADS_DB,
    MEMORY_FILE,
    to_model_spec,
)
```

Add `_read_memory`, near `_read_memory`'s natural home (next to `validate_api_keys`):
```python
def _read_memory() -> str:
    """Read saved user preferences, if any. Empty string when the file doesn't exist yet."""
    path = Path(MEMORY_FILE)
    return path.read_text(encoding="utf-8") if path.exists() else ""
```

Replace `_build_prompt`:
```python
def _build_prompt(target_date: str, topics: list[str], open_slots: int) -> str:
    lines = [f"{target_date} 발행 오토마타 뉴스레터를 작성해주세요.", ""]
    if topics:
        lines.append("사용자 지정 토픽 (각각 topic-researcher로 조사하세요):")
        lines += [f"- {topic}" for topic in topics]
        lines.append("")
    lines.append(f"후보에서 추가로 선택할 토픽 수: {open_slots}")
    lines.append(f"아티클 저장 디렉토리: articles/{target_date}/")
    return "\n".join(lines)
```
with:
```python
def _build_prompt(target_date: str, topics: list[str], open_slots: int, preferences: str) -> str:
    lines = [f"{target_date} 발행 오토마타 뉴스레터를 작성해주세요.", ""]
    if preferences:
        lines.append("## 사용자 선호 (기억된 내용)")
        lines.append(preferences.strip())
        lines.append("")
    if topics:
        lines.append("사용자 지정 토픽 (각각 topic-researcher로 조사하세요):")
        lines += [f"- {topic}" for topic in topics]
        lines.append("")
    lines.append(f"후보에서 추가로 선택할 토픽 수: {open_slots}")
    lines.append(f"아티클 저장 디렉토리: articles/{target_date}/")
    return "\n".join(lines)
```

In `run_newsletter_generation`, replace:
```python
    print("🔧 에이전트 초기화 중...")
    if use_hitl and open_slots > 0:
        print("👤 Human-in-the-Loop 모드 활성화")

    agent = create_newsletter_agent(target_date, open_slots=open_slots, use_hitl=use_hitl)
    prompt = _build_prompt(target_date, topics, open_slots)
```
with:
```python
    print("🔧 에이전트 초기화 중...")
    if use_hitl and open_slots > 0:
        print("👤 Human-in-the-Loop 모드 활성화")

    preferences = _read_memory()
    agent = create_newsletter_agent(target_date, open_slots=open_slots, use_hitl=use_hitl, preferences=preferences)
    prompt = _build_prompt(target_date, topics, open_slots, preferences)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_feedback_memory.py tests/test_prompts.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/config.py src/main.py tests/test_feedback_memory.py tests/test_prompts.py
git commit -m "feat: read and inject saved preferences into agent prompts"
```

---

## Task 4: Feedback loop within the same run

**Files:**
- Modify: `src/main.py` (new `_run_feedback_loop`, wire into `run_newsletter_generation`)
- Modify: `tests/test_feedback_memory.py`

**Interfaces:**
- Consumes: `main._run_with_interrupts(agent, initial, config, metrics)` (existing, unchanged signature).
- Produces: `main._run_feedback_loop(agent, config, metrics, final_content: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_feedback_memory.py`:
```python
from types import SimpleNamespace


class _Metrics:
    def record_stream_event(self, event):
        pass

    def record_model_message(self, msg):
        pass

    def record_tool_result(self, name):
        pass


class _ScriptedFeedbackAgent:
    """Returns one fixed reply per stream() call, no interrupts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.received = []

    def stream(self, stream_input, config=None):
        self.received.append(stream_input)
        reply = self.replies.pop(0)
        yield {"model": {"messages": [SimpleNamespace(content=reply, tool_calls=[])]}}


def test_feedback_loop_streams_feedback_and_stops_on_blank_input(monkeypatch):
    inputs = iter(["짧게 줄여줘", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    agent = _ScriptedFeedbackAgent(["수정된 초안"])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "수정된 초안"
    assert agent.received[0]["messages"][0]["content"] == "짧게 줄여줘"


def test_feedback_loop_returns_immediately_when_first_input_blank(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "원래 초안"
    assert agent.received == []


def test_feedback_loop_stops_on_done_keyword(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "done")
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")
    assert final == "원래 초안"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_feedback_memory.py -v`
Expected: the three new tests FAIL with `AttributeError: module 'src.main' has no attribute '_run_feedback_loop'`.

- [ ] **Step 3: Implement**

In `src/main.py`, add `_run_feedback_loop`, right after `_run_with_interrupts`:
```python
def _run_feedback_loop(agent, config, metrics, final_content):
    """Prompt for feedback after a draft; stream each round on the same thread
    until the user signals they're done."""
    while True:
        print("\n" + "=" * 40)
        print("📋 현재 결과:")
        print("=" * 40)
        print(final_content or "(응답 없음)")

        feedback = input("\n💬 피드백을 입력하세요 (완료: 빈 줄/done/exit/끝): ").strip()
        if not feedback or feedback.lower() in {"done", "exit"} or feedback == "끝":
            return final_content

        stream_input = {"messages": [{"role": "user", "content": feedback}]}
        final_content = _run_with_interrupts(agent, stream_input, config, metrics)
```

In `run_newsletter_generation`, replace:
```python
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}
        final_content = _run_with_interrupts(
            agent, {"messages": [{"role": "user", "content": prompt}]}, config, metrics
        )

        print("\n" + "=" * 40)
        print("📋 최종 결과:")
        print("=" * 40)
        print(final_content or "(응답 없음)")
```
with:
```python
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}
        final_content = _run_with_interrupts(
            agent, {"messages": [{"role": "user", "content": prompt}]}, config, metrics
        )
        final_content = _run_feedback_loop(agent, config, metrics, final_content)

        print("\n" + "=" * 40)
        print("📋 최종 결과:")
        print("=" * 40)
        print(final_content or "(응답 없음)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_feedback_memory.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_feedback_memory.py
git commit -m "feat: loop for feedback on the drafted newsletter before exiting"
```

---

## Task 5: Resume feedback across sessions

**Files:**
- Modify: `src/main.py` (new `resume_feedback`)
- Modify: `tests/test_feedback_memory.py`

**Interfaces:**
- Consumes: `create_newsletter_agent(date_dir, open_slots=0, use_hitl=False, preferences=...)` (Task 2/3), `_read_memory()` (Task 3), `_run_feedback_loop(agent, config, metrics, final_content)` (Task 4).
- Produces: `main.resume_feedback(date_dir: str) -> dict | None` (returns `{"final_content": str, "metrics_path": str}` or `None` on failure — same shape as `run_newsletter_generation`'s return).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_feedback_memory.py`:
```python
def test_resume_feedback_returns_none_when_newsletter_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "validate_api_keys", lambda: True)

    assert main.resume_feedback("2026-08-05") is None


def test_resume_feedback_reads_existing_newsletter_and_runs_loop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "validate_api_keys", lambda: True)
    monkeypatch.setattr(main, "_read_memory", lambda: "")
    monkeypatch.setattr(main, "_build_checkpointer", lambda: SimpleNamespace())
    monkeypatch.setattr(main, "create_deep_agent", lambda **kwargs: SimpleNamespace())

    articles_dir = tmp_path / "articles" / "2026-08-05"
    articles_dir.mkdir(parents=True)
    (articles_dir / "newsletter.md").write_text("기존 뉴스레터", encoding="utf-8")

    monkeypatch.setattr("builtins.input", lambda _: "")  # end loop immediately

    result = main.resume_feedback("2026-08-05")

    assert result["final_content"] == "기존 뉴스레터"
    assert Path(result["metrics_path"]).exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_feedback_memory.py -v`
Expected: both new tests FAIL with `AttributeError: module 'src.main' has no attribute 'resume_feedback'`.

- [ ] **Step 3: Implement**

In `src/main.py`, add `resume_feedback`, after `run_newsletter_generation`:
```python
def resume_feedback(date_dir: str) -> dict | None:
    """Reattach to an already-generated newsletter's thread and continue the
    feedback loop, without regenerating anything.

    Args:
        date_dir: Date directory of an existing newsletter (e.g. "2026-01-15").

    Returns:
        {"final_content": ..., "metrics_path": ...} or None on failure.
    """
    if not validate_api_keys():
        return None

    newsletter_path = Path(ARTICLES_DIR) / date_dir / "newsletter.md"
    if not newsletter_path.exists():
        print(f"❌ 뉴스레터를 찾을 수 없습니다: {newsletter_path}", file=sys.stderr)
        return None

    print(f"🔧 기존 스레드 재연결 중... ({date_dir})")
    preferences = _read_memory()
    agent = create_newsletter_agent(date_dir, open_slots=0, use_hitl=False, preferences=preferences)
    config = {"configurable": {"thread_id": f"newsletter-{date_dir}"}}
    metrics = NewsletterRunMetrics(date_dir, "feedback", _agent_model_spec())
    final_content = newsletter_path.read_text(encoding="utf-8")

    try:
        final_content = _run_feedback_loop(agent, config, metrics, final_content)
        metrics_path = metrics.save("completed", final_content=final_content)
        print(f"📊 실행 메트릭 저장: {metrics_path}")
        return {"final_content": final_content, "metrics_path": metrics_path}
    except Exception as e:
        metrics_path = metrics.save("failed", final_content=final_content, error=str(e))
        print(f"\n❌ 피드백 처리 중 오류: {e}", file=sys.stderr)
        print(f"📊 실행 메트릭 저장: {metrics_path}", file=sys.stderr)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_feedback_memory.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_feedback_memory.py
git commit -m "feat: resume feedback on an existing newsletter thread later"
```

---

## Task 6: CLI wiring — `--feedback` flag

**Files:**
- Modify: `run.py`
- Modify: `tests/test_interrupt_loop.py` (bottom CLI section)

**Interfaces:**
- Consumes: `src.main.resume_feedback(date_dir: str) -> dict | None` (Task 5).
- Produces: `run.py`'s `main()` returns `0` on success, `1` on failure, when invoked with `--feedback DATE_DIR`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_interrupt_loop.py` (in the CLI section at the bottom, alongside `test_validate_topic_count_returns_open_slots` etc.):
```python
def test_main_feedback_flag_calls_resume_feedback(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run.py", "--feedback", "2026-06-17"])
    monkeypatch.setattr(
        "src.main.resume_feedback",
        lambda date_dir: {"final_content": "ok", "metrics_path": "p"} if date_dir == "2026-06-17" else None,
    )

    assert cli.main() == 0


def test_main_feedback_flag_reports_failure(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run.py", "--feedback", "missing-date"])
    monkeypatch.setattr("src.main.resume_feedback", lambda date_dir: None)

    assert cli.main() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_interrupt_loop.py::test_main_feedback_flag_calls_resume_feedback tests/test_interrupt_loop.py::test_main_feedback_flag_reports_failure -v`
Expected: FAIL — `argparse` errors with `unrecognized arguments: --feedback` (exits via `SystemExit`, not the assert).

- [ ] **Step 3: Implement**

In `run.py`, add the argument (after the `--merge`/`--version` block, before `--hitl`):
```python
    parser.add_argument(
        "--feedback", "-f",
        type=str,
        metavar="DATE_DIR",
        help="기존 뉴스레터 스레드에 피드백 반영 (날짜 디렉토리 지정, 재생성 없이 이어서 진행)",
    )
```

Add the branch (after the `# Merge only mode` block, before `# Full generation mode`):
```python
    # Feedback mode: resume an existing thread without regenerating
    if args.feedback:
        from src.main import resume_feedback
        result = resume_feedback(args.feedback)
        if result is None:
            print("❌ 피드백 처리 실패")
            return 1
        print("✅ 피드백 반영 완료!")
        print(f"📁 결과 위치: articles/{args.feedback}/")
        return 0
```

Add an example to the epilog string (in the `epilog="""..."""` block):
```
  python run.py --feedback 2026-01-15             # 기존 뉴스레터에 피드백 이어서 반영
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_interrupt_loop.py::test_main_feedback_flag_calls_resume_feedback tests/test_interrupt_loop.py::test_main_feedback_flag_reports_failure -v`
Expected: all PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `uv run pytest tests/ -v -m "not integration"`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add run.py tests/test_interrupt_loop.py
git commit -m "feat: add --feedback CLI flag to resume an existing newsletter thread"
```
