# Multiturn Feedback + Preference Memory

Status: approved
Branch: feature/multiturn-conversation

## Problem

`run.py` generates a newsletter once per process and exits. There is no way
to give feedback on the draft in the same run, and nothing persists across
runs — the agent has no memory of the user's taste or writing-style
preferences from prior sessions.

## Goals

1. After the first draft/merge completes, let the user give feedback in the
   same run and have the agent revise (files + `newsletter.md`) before
   exiting, in a loop until the user is done.
2. Let the agent remember explicit user preferences ("기억해줘 ...",
   "remember ...") across runs, and apply them to every future run's
   research/writing/tone.

## Non-goals

- No auto-inferred preferences from edits/feedback (explicit only).
- No separate `--revise` command for feedback given after the process has
  already exited (out of scope for this pass).
- No new persistence backend (SQLite, DB) — flat file only.

## Design

### 1. Feedback loop (same run)

- `create_newsletter_agent` always attaches a `MemorySaver` checkpointer
  (currently only attached when `use_hitl and open_slots > 0`). Needed so
  the LangGraph thread's message history survives across feedback rounds.
- `run_newsletter_generation`, after `_run_with_interrupts` returns the
  first `final_content`, enters a loop:
  1. Print the current result.
  2. `input()` for feedback. Blank line or `done`/`exit`/`끝` ends the loop.
  3. Otherwise, stream the feedback text as a new user message on the same
     `thread_id`, reusing `_run_with_interrupts` (interrupts, e.g. HITL
     topic selection, can't recur here in practice but the helper is
     reused as-is rather than duplicated).
  4. Update `final_content` from the round's result, loop back to 1.
- The orchestrator already has file read/write tools via
  `FilesystemBackend` — no new tools needed for it to edit an existing
  article file and re-call `merge_newsletter`.
- `ORCHESTRATOR_PROMPT` gets a new section describing: revisions arrive as
  follow-up user turns, referencing already-saved article files by their
  filenames; edit the specific file(s) the feedback concerns, then re-run
  `merge_newsletter`.

### 2. Preference memory

- New path constant `MEMORY_FILE = "memory/preferences.md"` in
  `src/config.py`. Directory `memory/`, file gitignored (personal data,
  matches existing `articles/`/`artifacts/` gitignore pattern).
- `run_newsletter_generation` reads `MEMORY_FILE` if present (empty string
  if missing) before creating the agent.
- `create_newsletter_agent` takes this text and:
  - includes it in the orchestrator's initial prompt (`_build_prompt`),
    under a clearly labeled "사용자 선호 (기억된 내용)" section — guarantees
    the model sees it without relying on it choosing to read the file.
  - passes it into `build_article_writer_agent(preferences)` (replaces the
    static `article_writer_agent` dict in `src/agents/article_writer.py`),
    appended to `ARTICLE_WRITER_PROMPT` so the subagent's tone/style output
    honors it directly, independent of whether the orchestrator relays it
    when delegating.
- `ORCHESTRATOR_PROMPT` gets an instruction: when a user feedback message
  explicitly asks to remember something (starts with or contains
  "기억해줘"/"remember"), **append** one line to `memory/preferences.md`
  via the file-write tool (never overwrite the file), then confirm to the
  user in its reply before continuing the normal feedback flow.

### Data flow

```
run.py → run_newsletter_generation
  → read memory/preferences.md → prefs_text (empty if absent)
  → create_newsletter_agent(..., preferences=prefs_text)
      orchestrator prompt includes prefs_text
      article-writer subagent prompt includes prefs_text
  → _run_with_interrupts(...) → final_content   # first draft + merge
  → loop:
      print final_content
      feedback = input()
      if blank/done/exit: break
      final_content = _run_with_interrupts(feedback message, same thread)
        # orchestrator may edit article files, re-merge,
        # and/or append memory/preferences.md if asked to remember
```

### Error handling

Unchanged pattern: exceptions in `run_newsletter_generation` are caught,
`metrics.save("failed", ...)` runs, traceback printed. A failure inside the
feedback loop breaks the loop (doesn't retry) — the already-saved draft on
disk from the last successful round is preserved either way, since every
round writes through `save_article`/`merge_newsletter` as it always did.

### Testing

One `test_*.py` (stdlib `unittest`/`assert`, no fixtures): builds the
orchestrator prompt and the article-writer subagent prompt with a fake
`memory/preferences.md` content and asserts the text appears in both. This
is the smallest check that fails if the injection wiring breaks — no test
for the interactive loop itself (not worth mocking `input()`/streaming for
a personal tool).

## Files touched

- `src/main.py` — always-on checkpointer, feedback loop, read memory file,
  pass preferences through to `create_newsletter_agent`.
- `src/agents/article_writer.py` — static dict → `build_article_writer_agent(preferences)`.
- `src/agents/__init__.py` — export the new builder instead of the dict.
- `src/config.py` — `MEMORY_FILE` constant, prompt additions.
- `.gitignore` — add `memory/`.
- `memory/` — new directory, created at runtime if missing.
- One new test file for the prompt-injection check.
