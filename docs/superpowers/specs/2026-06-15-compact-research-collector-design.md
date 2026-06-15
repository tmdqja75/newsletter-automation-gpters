# Compact Deterministic Research Collector — Design Spec

- **Date**: 2026-06-15
- **Status**: Approved (pre-implementation)
- **Scope**: Phase 2 of `docs/cost-time-optimization-strategy.md` — "Compact Deterministic Research Collector"
- **Related**: Phase 1 (model configurability + run metrics, already landed/in progress on this branch)

## Context

The current `research-agent` subagent (`src/agents/research.py`) is an open-ended
DeepAgents subagent: it is given `search_ai_news`, `search_hackernews`,
`fetch_article_content`, and `fetch_official_blog_posts`, plus a long prompt
(`RESEARCH_AGENT_PROMPT` in `src/config.py`) describing 8 research categories,
and is left to decide how much to search and fetch.

This produces large, variable-cost agent loops: many search/fetch tool calls,
large fetched-content payloads (`fetch_article_content` can return up to
~10,000 chars per URL), and unpredictable topic-selection input.

This spec replaces the open-ended search/fetch loop with a single
Python-controlled collection step (`collect_weekly_research`) that the
research-agent calls first. The research-agent keeps its current
responsibility of producing the final polished markdown research report
(`research_results.md`), but now derives it from compact, pre-ranked,
pre-summarized candidates instead of raw search/fetch output.

## Goals

- Lower input token cost and latency for the research stage.
- More predictable, reproducible topic-selection input.
- Persist raw + structured research artifacts for reuse/debugging and for
  HITL topic-reject retries.
- Preserve the existing `research_results.md` output format/contract that
  `topic-selector` and the orchestrator depend on.

## Non-Goals (deferred to later phases)

- Replacing the broad DeepAgents orchestration loop (Phase 3).
- Async/parallel fetching and article generation (Phase 4).
- Per-stage model tiering beyond the collector's own model (Phase 5, partially
  addressed here only for the collector itself).

## Architecture & Pipeline Flow

New module: `src/tools/research_collector.py`

- `_collect_weekly_research_core(publication_date, max_search_results=20, max_fetches=8, max_chars_per_source=1500, summarizer=None) -> list[dict]`
  Pure pipeline logic. `summarizer` is injectable (a callable taking the list
  of fetched candidates and returning enrichment dicts) so tests can supply a
  fake without hitting a real model.

- `collect_weekly_research(publication_date, max_search_results=20, max_fetches=8, max_chars_per_source=1500) -> str`
  `@tool`-decorated wrapper, returns a JSON string (same convention as
  `search_ai_news`/`fetch_official_blog_posts`). Never raises.

### Pipeline steps

1. **Build query plan** — `RESEARCH_QUERY_PLAN` (module-level constant,
   ~12 entries derived from the 8 `RESEARCH_AGENT_PROMPT` categories), with
   `{year}` / `{month}` / `{month_en}` placeholders filled from
   `publication_date`.
2. **Run searches** — call `search_ai_news`, `search_hackernews`, and
   `fetch_official_blog_posts` directly from Python (not via the agent),
   tagging each raw result with its `category` and `tool`.
3. **Normalize** — convert raw results into preliminary `ResearchCandidate`
   dicts (title, url, source, category, published_at if available, score,
   topic_type inferred from category). Initial `topic_type` inference:
   `study_resources` → `study_cafe`; all other categories → `main`. This is
   a provisional value — the batch summarizer (step 8) may override
   `topic_type` per candidate based on actual content.
4. **Deduplicate** — by canonical URL (strip tracking params) and normalized
   title; keep the higher-scored duplicate.
5. **Date filter** — drop candidates whose parseable `published_at` falls
   outside `[publication_date - 14 days, publication_date]`. Candidates with
   no parseable date are **kept** but score-penalized (see Ranking below) —
   search snippets often omit dates, while official blog posts always have
   dates from RSS/HTML scraping.
6. **Rank & truncate** — composite score (see Configuration section);
   truncate to `max_search_results`.
7. **Fetch top-N** — call `fetch_article_content` for the top `max_fetches`
   candidates by rank; truncate fetched content to `max_chars_per_source`.
   Per-item fetch failure sets `fetched: false` and the candidate proceeds
   with snippet-only content.
8. **Batch-summarize** — a single LLM call (via the injectable `summarizer`,
   default backed by `RESEARCH_COLLECTOR_MODEL`) over all successfully-fetched
   candidates, requesting a JSON array of
   `{url, summary, key_facts, why_it_matters, topic_type}`. Parse failures
   fall back to per-candidate snippet-based fields (see Error Handling).
   Candidates that were **not** fetched (`fetched: false`, i.e. outside the
   top `max_fetches` or whose fetch failed) are **not** sent to the
   summarizer; they keep `summary` = their original search-result snippet
   (e.g. Tavily `content` field or HN title), `key_facts = []`,
   `why_it_matters = ""`, and the provisional `topic_type` from step 3.
9. **Merge enrichment** back into the full candidate list by URL.
10. **Persist artifacts** under `artifacts/research/{publication_date}/`.
11. **Return** the full candidate list (Python list of dicts from the core
    function; JSON string from the tool wrapper).

## Data Model & Artifacts

### `ResearchCandidate` shape

```json
{
  "title": "...",
  "url": "...",
  "source": "...",
  "published_at": "... | null",
  "summary": "...",
  "key_facts": ["...", "..."],
  "why_it_matters": "...",
  "topic_type": "main | study_cafe | background",
  "category": "model_releases | agents_automation | research_papers | tools_infra | industry_business | policy_society | study_resources | real_world_usecases | official_blogs",
  "score": 0.0,
  "fetched": true
}
```

`category`, `score`, and `fetched` are additional internal/debugging fields
included on every candidate (in both the artifact files and the tool's JSON
output) — they are useful for debugging and incur negligible token cost.

### Artifacts (`artifacts/research/{publication_date}/`)

- `raw_search_results.json` — raw results from `search_ai_news`,
  `search_hackernews`, and `fetch_official_blog_posts`, tagged by
  category/query. For debugging search quality.
- `candidates.json` — the final enriched `ResearchCandidate` list (same
  content the tool returns as JSON).

Both written via `Path.mkdir(parents=True, exist_ok=True)` +
`write_text(json.dumps(..., ensure_ascii=False, indent=2))`, mirroring
`NewsletterRunMetrics.save()`. Artifact write failures are appended to the
`errors` list but never abort the pipeline.

### Top-level JSON envelope (tool return value)

```json
{
  "publication_date": "...",
  "candidates": [ /* ResearchCandidate list */ ],
  "total_found": 0,
  "total_fetched": 0,
  "errors": ["..."]
}
```

`errors` is omitted when empty (matches `fetch_official_blog_posts`
convention).

## Configuration

### New env var

```python
# src/config.py
RESEARCH_COLLECTOR_MODEL = os.getenv("RESEARCH_COLLECTOR_MODEL", "claude-haiku-4-5")
```

A shared helper `to_model_spec(name: str) -> str` is factored out (used by
both `MODEL_NAME`/`_agent_model_spec()` in `src/main.py` and
`RESEARCH_COLLECTOR_MODEL`): names without a `:` provider prefix become
`anthropic:{name}`; names with a prefix (e.g. `openai:gpt-5-mini`) pass
through unchanged. `tests/test_phase1_cost_controls.py` continues to pass via
this shared helper.

### `RESEARCH_QUERY_PLAN`

Module-level constant in `research_collector.py`, ~12 entries derived from the
8 categories in `RESEARCH_AGENT_PROMPT`:

| category | tool | query template |
|---|---|---|
| model_releases | tavily | `{year}년 {month}월 AI 모델 출시` |
| model_releases | tavily | `{month_en} {year} new LLM model release` |
| agents_automation | hn | `AI agent` |
| agents_automation | tavily | `{year}년 {month}월 AI 에이전트 자동화` |
| research_papers | tavily | `arXiv AI agent {month_en} {year}` |
| tools_infra | tavily | `{month_en} {year} AI developer tools` |
| industry_business | tavily | `{year}년 {month}월 AI 스타트업 산업 동향` |
| policy_society | tavily | `{month_en} {year} AI policy regulation` |
| study_resources | tavily | `{month_en} {year} AI agent tutorial course` |
| real_world_usecases | hn | `Show HN AI agent` |
| real_world_usecases | tavily | `"AI agent" deployed production results {year}` |
| official_blogs | blog | (n/a — single `fetch_official_blog_posts(publication_date)` call) |

Each Tavily/HN call requests a small `max_results` (5-6) so the combined raw
pool comfortably exceeds `max_search_results` before ranking/truncation.

> **Note on `official_blogs`:** the original `RESEARCH_AGENT_PROMPT` lists
> `fetch_official_blog_posts` as a sub-bullet of category 8
> (`real_world_usecases`), but official OpenAI/Anthropic/DeepMind blog posts
> can be model releases, research, policy, etc. — not exclusively use-cases.
> This spec introduces `official_blogs` as a 9th **source-routing category**
> (distinct from the 8 content categories in the prompt) purely for
> collector bookkeeping/artifacts. Its initial `topic_type` is `main` (per
> the step-3 mapping above), and the summarizer may reclassify
> `topic_type`/`category`-relevant framing per candidate based on actual
> content.

### Ranking score

```text
score = tavily_score (0 for HN/blog results)
      + 0.3 if category == "real_world_usecases"
      + 0.2 if this is an HN result with points > 50
      - 0.5 if published_at is missing/unparseable
```

### Date filter

Candidates with a parseable `published_at` outside
`[publication_date - 14 days, publication_date]` are dropped. Candidates with
no parseable date are kept (penalized via score above, not dropped).

### Summarizer

One LangChain chat-model call (`init_chat_model(to_model_spec(RESEARCH_COLLECTOR_MODEL))`
or equivalent) over all successfully-fetched candidates. Prompt includes
`{title, url, source, content[:max_chars_per_source]}` per candidate and
requests a strict JSON array:
`[{url, summary, key_facts, why_it_matters, topic_type}, ...]`.

## Research-Agent Integration

### Tool wiring (`src/agents/research.py`)

```python
research_subagent = {
    "name": "research-agent",
    "description": "...",  # unchanged
    "system_prompt": RESEARCH_AGENT_PROMPT,  # rewritten, see below
    "tools": [collect_weekly_research, fetch_article_content],
}
```

`search_ai_news`, `search_hackernews`, and `fetch_official_blog_posts` are
removed from the subagent's tool list (the collector still uses them
internally via direct Python calls). `src/tools/__init__.py` continues to
export them unchanged — no breaking changes to those modules or their
existing tests.

### `RESEARCH_AGENT_PROMPT` rewrite (`src/config.py`)

New three-step structure:

1. **Collect** — call `collect_weekly_research(publication_date=...)` to get
   the compact candidate list. `publication_date` is passed through from the
   orchestrator's date-aware prompt, same as today.
2. **Verify (optional, selective)** — for high-value candidates with
   `fetched: false` or a thin `summary`, optionally call
   `fetch_article_content` to confirm details before writing them up. The
   existing "원문 확인 규칙" language is retained but scoped to this optional
   verification step rather than mandatory for every candidate.
3. **Produce final markdown report** — from the structured candidates
   (`summary`, `key_facts`, `why_it_matters`, `category`/`topic_type`,
   `published_at`, `url`), write the **same numbered markdown format** as
   today:

   ```text
   1. 제목
      - 요약 (2-3문장)
      - 출처 URL
      - 발표/게시 날짜
      - 중요도 (높음/중간/낮음)
      - 카테고리 (모델발표/에이전트/연구/도구/산업동향/정책/학습자료)
   ```

   This output is saved as `research_results.md` (per `src/main.py`'s
   workflow) and remains byte-format-compatible with what `topic-selector`
   and the orchestrator currently expect. Only the research-agent's internal
   process changes — deterministic collection + optional spot-check, instead
   of a fully open-ended search/fetch loop.

## Error Handling

Every stage degrades gracefully; `collect_weekly_research` never raises:

- **Per-query search/blog fetch** — wrapped in try/except; failures appended
  to `errors`, that query's results are skipped (matches
  `fetch_official_blog_posts` pattern).
- **Date parsing** — unparseable/missing `published_at` → kept with score
  penalty, not dropped.
- **`fetch_article_content` per candidate** — failure sets `fetched: false`;
  candidate proceeds with snippet-only content.
- **Batch summarizer call** — failure (network/model error or non-JSON
  response) → all fetched candidates fall back to
  `summary = content[:200]`, `key_facts = []`, `why_it_matters = ""`,
  `topic_type = "background"`; error appended to `errors`.
- **Artifact persistence** — write failures appended to `errors`, never abort
  the pipeline.
- **Top-level wrapper** — any uncaught exception is caught and returned as
  `{"error": str(e), "publication_date": ..., "candidates": [], "errors": [...]}`
  so the agent always receives valid JSON.

## Testing Strategy

New `tests/test_research_collector.py`, following `tests/test_blog_scraping.py`
conventions (monkeypatch + `tmp_path`, no real network/model calls by
default):

1. **Query plan** — `RESEARCH_QUERY_PLAN` covers all 8 categories; date
   placeholders fill correctly for a given `publication_date`.
2. **Normalization & dedup** — duplicate URLs (with tracking params) and
   near-duplicate titles collapse to one candidate, keeping the higher-scored
   copy.
3. **Date filtering** — items outside `[pub_date-14d, pub_date]` dropped;
   items with no date kept but scored lower; verified via ranked order.
4. **Ranking & truncation** — `real_world_usecases` bonus and HN-points bonus
   affect ordering; result truncated to `max_search_results`.
5. **Fetch limiting & truncation** — only top `max_fetches` candidates get
   `fetch_article_content` called (mock call-count assertion); content
   truncated to `max_chars_per_source`.
6. **Fetch failure handling** — mocked `fetch_article_content`
   raising/erroring → `fetched: false`, pipeline continues.
7. **Summarizer success** — fake summarizer returns valid JSON array → fields
   merged into matching candidates by URL.
8. **Summarizer failure/malformed JSON** — fallback fields applied, `errors`
   populated, no exception.
9. **Artifact persistence** — `raw_search_results.json` and `candidates.json`
   written under `artifacts/research/{date}/` with expected structure (via
   `tmp_path` + `monkeypatch.chdir`).
10. **`collect_weekly_research` wrapper** — returns valid JSON string matching
    the envelope; total pipeline failure (e.g. all searches raise) still
    returns valid JSON with `candidates: []`.
11. **`to_model_spec` helper** — `claude-haiku-4-5` →
    `anthropic:claude-haiku-4-5`; `openai:gpt-5-mini` passes through; used by
    both `MODEL_NAME` and `RESEARCH_COLLECTOR_MODEL` paths (refactor
    `_agent_model_spec` in `src/main.py` to use the shared helper, update
    `tests/test_phase1_cost_controls.py` assertions if needed).
12. **`research_subagent` tool wiring** — assert
    `tools == [collect_weekly_research, fetch_article_content]`.

### Integration test

One `@pytest.mark.integration`-marked test (skipped by default, like
`test_blog_scraping.py`'s `TestIntegration`) performing a real
`collect_weekly_research` call with real search APIs and the real
`RESEARCH_COLLECTOR_MODEL` summarizer, asserting non-empty candidates and
valid artifact files. For manual verification, not CI.

## Acceptance Criteria

- `collect_weekly_research` returns valid JSON matching the documented
  envelope for both success and total-failure cases.
- `research_subagent` exposes exactly `[collect_weekly_research,
  fetch_article_content]`.
- `research_results.md` output format remains compatible with
  `topic-selector`'s expectations (numbered list with 제목/요약/출처
  URL/날짜/중요도/카테고리).
- `artifacts/research/{publication_date}/raw_search_results.json` and
  `candidates.json` are written on a successful run.
- All new/updated tests pass via `uv run pytest` (excluding
  `-m integration`).
- Existing Phase 1 tests (`tests/test_phase1_cost_controls.py`) continue to
  pass after the `to_model_spec` refactor.
