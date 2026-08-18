# Multiturn Editing + Persistent Taste Memory Design

## Problem

`run.py` is one-shot: generate, print, exit. Two gaps:

1. **No follow-up editing.** Once articles are drafted there's no way to say "add a paragraph to topic 2" or "shorten the intro" without re-running the whole pipeline from scratch. The existing `MemorySaver` checkpointer is in-memory and only attached when `--hitl` is set, so even within a single process there's no durable thread once the run function returns — and nothing survives process exit at all.
2. **No taste memory.** The agent has no way to learn "I prefer shorter intros" or "don't use that analogy style" and carry it into next week's run. Every run starts from the same static `ARTICLE_WRITER_PROMPT`.

These are two independent persistence problems (session-scoped conversation vs. cross-session preference) solved by two different mechanisms — bundled here because both were requested together as "multiturn."

## Goal

1. Let the user iterate on a generated newsletter via an interactive follow-up loop, in the same run and later in a fresh process.
2. Let `article-writer` accumulate durable writing-taste notes across every future run, with zero new infrastructure.

## Approach

### 1. Session-level editing: persistent checkpointer + REPL

Replace the in-memory, HITL-only checkpointer with a `SqliteSaver` (from `langgraph-checkpoint-sqlite`) attached on every run, one file per date: `articles/{date}/checkpoint.sqlite`. Thread id stays `newsletter-{date}` (already date-scoped).

Two new `run.py` flags:

- `--interactive` — opt-in. After normal generation finishes and prints results, drops into a REPL: prompt for an instruction, empty input exits, non-empty sends as a new human message on the same thread (reusing `_run_with_interrupts`), then `merge_newsletter(date)` runs after every turn so `newsletter.md` stays in sync.
- `--continue DATE` — skips generation entirely. Requires `articles/{date}/checkpoint.sqlite` to already exist; if missing, print a clear error ("먼저 뉴스레터를 생성하세요: `python run.py --date {date}`") and exit 1. Otherwise rebuilds the agent (the deepagents graph object itself is stateless per process — all history lives in the sqlite thread) and drops straight into the same REPL.

`ORCHESTRATOR_PROMPT` gets a short addendum for follow-up turns: locate the existing `articles/{date}/0X_*.md` file via the built-in `read_file`/`edit_file` tools (already available through `FilesystemBackend`) and edit it in place, rather than re-running the full research→draft→save pipeline.

Both flags are orthogonal to `--hitl`/`--topics`/`--count`, which only apply to the initial generation.

### 2. Cross-session taste memory: deepagents `MemoryMiddleware`

deepagents ships exactly this: `MemoryMiddleware` loads an `AGENTS.md`-style file into the system prompt on every run and lets the agent update it itself via `edit_file` when it learns something durable. No new dependency, no DB — reuses the `FilesystemBackend` already wired in `main.py`.

Scope: `article-writer` only (matches "writing taste" directly; topic-selection preferences are out of scope for this spec).

- New file `memory/writing_preferences.md`, committed to git, seeded with a short header (e.g. "이 파일은 article-writer가 스스로 갱신하는 문체 선호 메모입니다.").
- `SubAgent` dicts don't expose a `memory` key directly, so it's wired via the subagent's `middleware` list:

```python
article_writer_agent = {
    ...,
    "middleware": [
        MemoryMiddleware(
            backend=FilesystemBackend(root_dir=".", virtual_mode=True),
            sources=["memory/writing_preferences.md"],
        ),
    ],
}
```

- `ARTICLE_WRITER_PROMPT` gets one line pointing at the memory explicitly (deepagents' built-in memory-update instructions handle the *mechanism*, but naming it in-prompt makes the behavior more reliable than relying on implicit `<agent_memory>` discovery alone).

This mechanism is independent of the sqlite checkpointer — it works identically whether or not `--interactive`/`--continue` is used, since it's file-based and loaded fresh every run regardless of thread/date.

## Component Changes

### `pyproject.toml`
- Add `langgraph-checkpoint-sqlite` dependency.

### `src/main.py`
- `create_newsletter_agent`: always attach a `SqliteSaver` checkpointer pointed at `articles/{date}/checkpoint.sqlite` (drop the `use_hitl`-only condition).
- New REPL loop function (reused by both `--interactive` and `--continue`): prompt for instruction, empty exits, otherwise stream on the existing thread via `_run_with_interrupts`, then call `merge_newsletter(date)`.
- New `run_continue(target_date)` entry point: validate the checkpoint file exists, rebuild the agent, enter the REPL directly (no initial generation prompt).
- `run_newsletter_generation`: after normal flow completes, if `--interactive`, enter the REPL loop before returning.

### `src/agents/article_writer.py`
- Add `middleware=[MemoryMiddleware(backend=FilesystemBackend(root_dir=".", virtual_mode=True), sources=["memory/writing_preferences.md"])]`.

### `src/config.py`
- `ORCHESTRATOR_PROMPT`: add a short "후속 수정 요청 처리" section describing the edit-existing-file behavior for REPL turns.
- `ARTICLE_WRITER_PROMPT`: add one line pointing at `memory/writing_preferences.md`.

### `run.py`
- Add `--interactive` (store_true) and `--continue DATE_DIR` flags, wired to the new `src/main.py` entry points.

### `memory/writing_preferences.md`
- New file, seeded, committed.

### Unchanged
`src/tools/*`, `src/agents/topic_researcher.py`, `src/utils/merge_articles.py` (called as-is, not modified), newsletter templates, HITL topic-selection flow.

## Testing

- One small pytest alongside the existing `test_agents_wiring.py`/`test_interrupt_loop.py` patterns:
  - `create_newsletter_agent` always attaches a checkpointer (not conditional on `use_hitl`).
  - `--continue` on a date with no existing checkpoint file raises the documented error instead of silently creating an empty thread.
- Manual smoke test: `uv run python run.py --quick --interactive`, issue one follow-up edit instruction, confirm the target article file changes and `newsletter.md` re-merges.
