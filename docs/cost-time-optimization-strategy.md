# Newsletter Cost & Time Optimization Strategy

## Context

Current newsletter generation is estimated at roughly **30 minutes** and **$2 per newsletter**. The project currently uses a DeepAgents/LangGraph orchestration flow to research weekly AI/LLM news, select topics, draft Korean articles, apply Automata tone editing, save markdown files, and merge them into a final newsletter.

This document captures the cost/time reduction strategy identified from inspecting the codebase. The goal is to preserve newsletter quality while making each run faster, cheaper, and easier to measure.

## Primary Optimization Goals

1. **Make model choice configurable** so the project can move off the most expensive model without code changes.
2. **Measure every run** so future changes are based on real duration, token, and tool-call data.
3. **Reduce agent-loop overhead** by moving deterministic workflow decisions into Python.
4. **Reduce research context size** before sending information to the LLM.
5. **Parallelize independent work** such as network fetching and article drafting/editing.
6. **Keep expensive models only where quality impact is highest**: final synthesis and article writing.

## Current Cost/Latency Drivers

### 1. Top-level model was hardcoded

`src/config.py` defines `MODEL_NAME`, but the main agent previously hardcoded the DeepAgents model in `src/main.py`. That meant changing `.env` did not actually change the primary model used during newsletter generation.

Impact:

- Prevented quick experimentation with cheaper/faster models.
- Made cost controls depend on source-code edits.

### 2. One broad agent loop controls the whole workflow

The full run starts with a broad prompt similar to:

```text
이번 주 오토마타 뉴스레터를 작성해주세요.
```

The agent then decides how to research, select topics, write, edit, save, and merge. This creates repeated model/tool cycles with growing context.

Impact:

- More model calls than a deterministic pipeline needs.
- Larger accumulated context over time.
- Harder to predict cost and duration.
- Harder to profile which step is expensive.

### 3. Research can return too much content

The research prompt encourages fetching full article content before presenting candidates. `fetch_article_content()` can return up to approximately 10,000 characters per URL, and search can return many URLs.

Impact:

- Large prompt payloads.
- Higher input token cost.
- Slower model calls.
- More chance of low-value duplicated context.

### 4. Network work is mostly serial

The content-fetching flow creates clients per request and official blog collection is performed sequentially.

Impact:

- Wall-clock time grows linearly with the number of sources.
- Slow or flaky sources delay the whole run.

### 5. No first-class telemetry

Before Phase 1, there was no saved run-level metrics file for:

- elapsed time,
- model used,
- stream/model/tool event counts,
- tool-call counts,
- token usage when available from provider metadata.

Impact:

- Difficult to confirm whether an optimization helped.
- Difficult to identify whether time is spent in model calls, tools, search, fetching, or file operations.

## Implemented Phase 1: Measurement & Configurability

Phase 1 is intentionally low-risk. It improves observability and makes the top-level model configurable without changing the overall agentic architecture.

### Implemented changes

- `src/main.py` now uses `MODEL_NAME` from `src/config.py` for the main DeepAgents model.
- Model names without a provider prefix are converted to Anthropic model specs, e.g. `claude-haiku-4-5` becomes `anthropic:claude-haiku-4-5`.
- Model names with a provider prefix are preserved, e.g. `openai:gpt-5-mini` remains unchanged.
- Each full or quick generation saves `articles/{date}/run_metrics.json`.
- `run_metrics.json` records:
  - target date,
  - run mode,
  - model,
  - start/completion time,
  - duration seconds,
  - stream/model/tool/interrupt event counts,
  - assistant output characters,
  - final content characters,
  - tool call counts,
  - tool result counts,
  - token usage when LangChain/provider messages expose metadata.
- `src/utils/merge_articles.py` excludes `research_results.md` from newsletter merge and preview so research notes do not accidentally become a newsletter article.

### Intentionally not included in Phase 1

Per-subagent model overrides were intentionally skipped per request. The current Phase 1 only changes the top-level model and adds telemetry.

### Suggested immediate `.env` experiments

Start by comparing current quality/cost using a cheaper top-level model:

```env
MODEL_NAME=claude-haiku-4-5
```

or, if using provider-prefixed model names:

```env
MODEL_NAME=anthropic:claude-haiku-4-5
```

Then run:

```bash
uv run python run.py --quick
uv run python run.py
```

Compare `articles/{date}/run_metrics.json` across runs.

## Phase 2: Compact Deterministic Research Collector

Replace open-ended research behavior with a Python-controlled collection step.

### Proposed shape

```python
collect_weekly_research(
    publication_date: str,
    max_search_results: int = 20,
    max_fetches: int = 8,
    max_chars_per_source: int = 1500,
) -> list[ResearchCandidate]
```

Each `ResearchCandidate` should contain compact structured fields:

```json
{
  "title": "...",
  "url": "...",
  "source": "...",
  "published_at": "...",
  "summary": "...",
  "key_facts": ["..."],
  "why_it_matters": "...",
  "topic_type": "main|study_cafe|background"
}
```

### Tactics

- Search broadly, but fetch only top-ranked candidates.
- Deduplicate by canonical URL and normalized title.
- Prefer official sources and high-signal technical posts.
- Date-filter before sending anything to the LLM.
- Truncate or summarize source text before model calls.
- Save raw/structured research as an artifact for reuse and debugging.

### Expected benefit

- Lower input token cost.
- Faster model calls.
- More predictable topic selection.
- Easier reuse when HITL rejects selected topics.

### Implemented changes (this PR)

- Added `collect_weekly_research()` in `src/tools/research_collector.py`: a
  deterministic pipeline covering 9 source-routing categories (the original
  8 `RESEARCH_AGENT_PROMPT` categories plus `official_blogs`), with
  dedup-by-URL/title, a 14-day date filter, score-based ranking/truncation,
  top-N fetching via `fetch_article_content`, and a single batch-summarizer
  LLM call (`RESEARCH_COLLECTOR_MODEL`, default `claude-haiku-4-5`).
- `research-agent`'s tools are now `[collect_weekly_research,
  fetch_article_content]` — `search_ai_news`, `search_hackernews`, and
  `fetch_official_blog_posts` are called internally by the collector instead
  of by the agent directly.
- `RESEARCH_AGENT_PROMPT` now describes a 3-step collect → optionally verify
  → write report flow, producing the same numbered
  제목/요약/출처/날짜/중요도/카테고리 format as before.
- Raw search results and structured candidates are persisted to
  `artifacts/research/{publication_date}/raw_search_results.json` and
  `candidates.json` for debugging and reuse.
- Added shared `to_model_spec()` helper in `src/config.py`, used by both
  `MODEL_NAME` (top-level model) and `RESEARCH_COLLECTOR_MODEL` (collector
  summarizer model).

## Phase 3: Python-Controlled Pipeline

Move orchestration from one broad agent loop into explicit Python steps.

### Target workflow

```text
collect_research()
→ select_topics()
→ draft_articles_in_parallel()
→ edit_tone_in_parallel()
→ save_articles()
→ merge_newsletter()
```

### Why this matters

The workflow itself is mostly deterministic. The LLM is needed for judgement and writing, not for deciding that the next step after writing article 1 is saving article 1.

### Proposed LLM call boundaries

1. **Topic selection**
   - Input: compact research candidates.
   - Output: structured list of selected topics.
   - Can use a cheaper/faster model.

2. **Article drafting**
   - Input: selected topic + supporting facts.
   - Output: article markdown.
   - This is quality-critical; use a strong model if needed.

3. **Tone editing**
   - Input: drafted article + style rules.
   - Output: edited article markdown.
   - Can often use a cheaper/faster model.

4. **Final validation**
   - Input: generated newsletter.
   - Output: checklist findings.
   - Can be a deterministic script plus optional LLM review.

### Expected benefit

- Fewer agent/tool round trips.
- Lower context growth.
- Easier step-by-step retries.
- Easier parallelism.
- Easier cost attribution per stage.

## Phase 4: Parallelization

Parallelize independent I/O and generation work.

### Network fetching

Use `httpx.AsyncClient` and `asyncio.gather` for:

- official blog fetching,
- selected article content fetching,
- Hacker News or API lookups.

Add timeouts and per-source error handling so one slow source does not block the full run.

### Article generation

Once topics are selected, draft independent articles concurrently, then tone-edit them concurrently.

Potential structure:

```python
articles = await asyncio.gather(*[
    draft_article(topic) for topic in selected_topics
])

edited_articles = await asyncio.gather(*[
    edit_tone(article) for article in articles
])
```

### Expected benefit

- Significant wall-clock reduction, especially when model/API calls can run concurrently.
- Better isolation of slow or failed topics.

## Phase 5: Model Tiering

Use model tiers by task complexity.

| Stage | Recommended model tier | Reason |
|---|---:|---|
| Research filtering | cheap/fast | Mostly extraction/ranking |
| Topic selection | cheap/medium | Structured judgement, short output |
| Article drafting | medium/strong | Highest quality impact |
| Tone editing | cheap/medium | Style transformation |
| Final QA | cheap/medium | Checklist-based review |

Per-subagent model overrides were not implemented in Phase 1, but they remain a high-leverage future optimization once the user wants to pursue them.

## Measurement Plan

Use `run_metrics.json` as the baseline artifact for comparing runs.

### Compare these fields

- `duration_seconds`
- `model`
- `stream_events`
- `model_events`
- `tool_events`
- `interrupt_events`
- `model_messages`
- `model_messages_with_usage`
- `assistant_output_chars`
- `final_content_chars`
- `tool_calls`
- `tool_results`
- `token_usage.input_tokens`
- `token_usage.output_tokens`
- `token_usage.total_tokens`

### Suggested experiment matrix

Run the same date/topic input through:

1. current default model,
2. cheaper top-level model,
3. cheaper model + compact research,
4. deterministic pipeline,
5. deterministic pipeline + parallel drafting/editing.

Record cost, duration, and qualitative newsletter quality for each run.

## Acceptance Criteria for Future Optimization Work

An optimization should be considered successful only if it satisfies all of the following:

- Produces a complete `newsletter.md`.
- Preserves Automata Korean tone and style.
- Includes citations/source links where appropriate.
- Does not merge research notes into the final newsletter.
- Saves metrics for the run.
- Reduces either cost, elapsed time, or variance without unacceptable quality loss.

## Recommended Next PRs

### PR 1: Research compaction

- Add a deterministic research collector.
- Limit fetched URLs and returned characters.
- Save compact structured research.
- Add tests for deduplication, filtering, and truncation.

### PR 2: Deterministic orchestration

- Add an explicit pipeline function.
- Keep the current agentic path as a fallback while validating quality.
- Add per-stage metrics.

### PR 3: Async fetch and parallel article generation

- Add async batch fetch tools.
- Generate/edit independent articles concurrently.
- Add timeout and partial-failure handling.

### PR 4: Optional model tiering

- Add task-specific model env vars.
- Use cheaper models for low-risk steps.
- Keep stronger model for final writing if quality requires it.

## Risks and Tradeoffs

- Cheaper models may reduce writing quality unless prompts and QA are tightened.
- Aggressive truncation may omit important technical details.
- Parallel model calls can hit rate limits if concurrency is not bounded.
- Deterministic orchestration reduces flexibility but improves predictability and cost control.
- Live source scraping can remain brittle; tests should avoid depending on fixed future date ranges or external page structure.

## Bottom Line

The highest-leverage path is:

1. measure every run,
2. make model choice configurable,
3. compact research before model calls,
4. replace broad agent orchestration with a deterministic pipeline,
5. parallelize independent network/model work,
6. introduce model tiering after the pipeline is easier to profile.

Phase 1 now provides the measurement/configuration foundation needed to validate the remaining phases with real data.
