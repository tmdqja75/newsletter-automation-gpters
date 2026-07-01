# Article Writer Agent Design

## Problem

Today the newsletter pipeline splits article production across two places:

1. The **main orchestrator** drafts each article itself (pure reasoning, no tools, no extra research beyond what `research-agent` already collected).
2. The **tone-editor** subagent (`src/agents/tone_editor.py`) then rewrites the draft into Automata's tone (해요체, term glossing, structure) — also pure reasoning, no tools.

This means article depth is capped by whatever `research-agent` gathered during the weekly sweep. There's no way to dig deeper into a single selected topic before writing, so articles can be shallow when the weekly research only surfaced a short snippet.

## Goal

Replace `tone-editor` with a single `article-writer` subagent that, per topic, does its own targeted research (via Tavily) and produces a tone-correct final article in one call — collapsing "draft" + "tone edit" into one step and adding topic-specific research depth.

## Workflow Change

**Before:**
1. research-agent → `research_results.md` (weekly sweep)
2. topic-selector → picks topics
3. Orchestrator drafts each article itself (reasoning only)
4. tone-editor subagent → polishes tone
5. Orchestrator saves + merges

**After:**
1. research-agent → `research_results.md` (weekly sweep, unchanged)
2. topic-selector → picks topics (unchanged)
3. Orchestrator calls `article-writer` once per selected topic, passing the topic's title/summary/source URL from `research_results.md`
4. `article-writer` does supplementary Tavily research on that specific topic (only as needed — `research_results.md` facts are the primary source), drafts a 400-600 word article with inline source citations, and applies Automata tone — all in one call
5. Orchestrator saves the returned article directly and merges (unchanged)

The orchestrator no longer drafts articles itself and no longer makes a separate tone-editing call.

## Component Changes

### `src/agents/article_writer.py` (replaces `src/agents/tone_editor.py`)

```python
article_writer_agent = {
    "name": "article-writer",
    "description": "...",
    "system_prompt": ARTICLE_WRITER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
}
```

Reuses the existing `search_ai_news` (Tavily) and `fetch_article_content` tools already used by `research-agent` — no new tool code.

### `src/config.py`

- Remove `TONE_EDITOR_PROMPT`.
- Add `ARTICLE_WRITER_PROMPT`, merging:
  - The fact-based citation rules currently living in `ORCHESTRATOR_PROMPT` (no fabrication, inline source URLs, no synthesizing new facts across sources) — moved here since this agent is now the one writing from sources.
  - The tone/style guide currently in `TONE_EDITOR_PROMPT` (해요체, "구독자님"/"여러분", Korean+English term glossing, 400-600 words, 1 emoji in title only, worked example article).
  - New instructions: primary source is the topic info passed in from `research_results.md`; use `search_ai_news`/`fetch_article_content` only to fill gaps or verify/deepen specific claims for the assigned topic, not to redo the weekly sweep.
- Update `ORCHESTRATOR_PROMPT` workflow section: replace the separate "draft article" + "call tone-editor" steps with a single "call article-writer per topic" step.

### `src/main.py`

- Import `article_writer_agent` instead of `tone_agent`.
- `agent_config["subagents"] = [research_subagent, article_writer_agent]`.
- Update the HITL inline system prompt (steps 5-6) to call `article-writer` once per selected topic instead of the current draft-then-tone-editor sequence.

### `src/agents/__init__.py`

- Update export from `tone_agent` to `article_writer_agent`.

### Unchanged

`research.py`, `topic_selector.py`, `search_tools.py`, `content_tools.py`, `merge_articles.py`, article file naming/save conventions, newsletter templates.

## Testing

- No existing test coverage for agent prompts/wiring (this is prompt/config plumbing, not independently unit-testable business logic).
- Verification is a `--quick` run (`uv run python run.py --quick`) to confirm `article-writer` is invoked, produces a saved article, and the run completes without errors.
