# Implementation plan: fix ranking fairness + add relevance-scoring stage

Read `docs/research-signal-quality-findings.md` first for the full investigation
this plan is based on (archive/view-count evidence, query additions already
merged, the two-round Haiku-vs-Nano comparison). This file is the executable
spec — file-by-file changes, in order, with verification steps. It assumes
zero conversation context.

Both tasks touch `src/tools/research_collector.py`. Do Task A first — it's a
prerequisite for the 9 queries already in `RESEARCH_QUERY_PLAN` to have any
effect, and Task B is easiest to verify once ranking is already fair.

## Current state (already merged, nothing to do here)

- `src/tools/search_tools.py`: `search_ai_news()` no longer sets
  `include_domains` on the Tavily call (still sets `exclude_domains` for
  anthropic.com/openai.com/deepmind.google, to avoid duplicating
  `official_blogs`).
- `src/tools/research_collector.py`: `RESEARCH_QUERY_PLAN` has 19 entries
  (was 10) — see the file for the current list. These are the queries stuck
  behind Task A.

---

## Task A — fix query-level ranking fairness

### Problem

`_rank_and_truncate()` round-robins across **categories**, but within a
category it sorts by `candidate["score"]` and falls back to insertion order on
ties. Most scores are ties (flat `+0.3`/`+0.2`/`-0.2` boosts, or flat `0.0` for
github_search/blog/pytorch_kr items), and insertion order is just the order
queries appear in `RESEARCH_QUERY_PLAN`. Categories that now have multiple
queries (`agents_automation`: 6, `github_trending`: 5) always let the
first-declared query's items win — newer queries' items never surface in the
final `max_search_results`-sized list, even though they're present in the
pre-truncation pool. Confirmed via `raw_search_results.json` vs
`candidates.json` on a live run: 147 raw hits found, only 30 survive, zero
from any of the 9 newly added queries.

### Fix

Extract the round-robin already used across categories into a reusable
`_interleave()` helper, and apply it **twice** — once across queries within a
category, once across categories — instead of once.

**1. Tag each candidate with its originating query during normalization.**

In `_normalize_candidates()` (`src/tools/research_collector.py`), the loop
iterates `raw_results`, where each `result` has `category`, `tool`, `query`.
Add a synthetic key and attach it to every candidate built from that result:

```python
def _normalize_candidates(raw_results: list[dict]) -> list[dict]:
    candidates: list[dict] = []

    for result in raw_results:
        category = result["category"]
        tool = result["tool"]
        query_key = f"{tool}:{result['query']}"  # ADD THIS LINE
        topic_type = DEFAULT_TOPIC_TYPE

        for item in result["items"]:
            ...
            candidate = {
                "title": title,
                "url": url,
                ...
                "score": round(score, 3),
                "fetched": False,
                "_query_key": query_key,  # ADD THIS FIELD
            }
            ...
            candidates.append(candidate)

    return candidates
```

`_query_key` is transient — same treatment as the existing `prefetched_content`
field: strip it before persisting (see step 3).

**2. Replace `_rank_and_truncate()`'s single-level interleave with a
two-level one, via a shared helper:**

```python
def _interleave(groups: list[list[dict]]) -> list[dict]:
    """Round-robin merge groups, one item from each per pass (each group
    already sorted by priority), so no single group — category or query —
    can crowd out the others just by being larger or declared first.
    """
    result: list[dict] = []
    depth = 0
    while any(depth < len(g) for g in groups):
        for g in groups:
            if depth < len(g):
                result.append(g[depth])
        depth += 1
    return result


def _rank_and_truncate(candidates: list[dict], max_search_results: int) -> list[dict]:
    """Interleave fairly at two levels: queries within a category, then
    categories within the run. Prevents both a high-volume query and a
    high-volume category from crowding out quieter ones. Reduces to a plain
    score sort when every candidate shares one category and one query.
    """
    by_category: dict[object, dict[object, list[dict]]] = {}
    cat_order: list[object] = []
    for c in candidates:
        cat = c.get("category")
        query_key = c.get("_query_key")
        if cat not in by_category:
            by_category[cat] = {}
            cat_order.append(cat)
        by_category[cat].setdefault(query_key, []).append(c)

    category_lists: list[list[dict]] = []
    for cat in cat_order:
        query_groups = list(by_category[cat].values())
        for group in query_groups:
            group.sort(key=lambda c: c["score"], reverse=True)
        category_lists.append(_interleave(query_groups))

    return _interleave(category_lists)[:max_search_results]
```

**3. Strip `_query_key` before persisting.** In `_collect_weekly_research_core()`,
there's already a loop that pops `prefetched_content` before
`_persist_artifacts()` is called — extend it:

```python
    for candidate in candidates:
        candidate.pop("prefetched_content", None)
        candidate.pop("_query_key", None)  # ADD THIS LINE
```

(Do this pop *after* `_rank_and_truncate` has run, same as today — the field
is needed during ranking, not after.)

### Tests to update

`tests/test_research_collector.py` already has:
- `test_rank_and_truncate_sorts_by_score_and_limits`
- `test_rank_and_truncate_interleaves_categories_so_none_dominates`
- `test_rank_and_truncate_preserves_score_order_within_category`

Check each still passes — they construct candidate dicts by hand, so add
`"_query_key": "tool:query"` (any placeholder string, same for all items in
a test) to their fixtures so `_rank_and_truncate` doesn't crash on a missing
key (use `.get("_query_key")` defensively either way). **Add one new test**
asserting the actual bug fix: build a category with 2 query groups (5 items
each, tied scores), call `_rank_and_truncate` with a `max_search_results` that
only fits ~6 of the 10, and assert the result contains items from **both**
query groups, not just the first-declared one.

### Manual verification

```bash
# From the project root:
rm -f artifacts/research/<TEST_DATE>/candidates.json
uv run python -c "
import json
from src.tools.research_collector import collect_weekly_research
from src.tools.research_report import render_selection_list
result = json.loads(collect_weekly_research('<TEST_DATE>'))
print(render_selection_list(result['candidates']))
"
```

Confirm the printed list includes at least one item whose title matches
something from the newly-added queries (e.g. a GitHub repo about token/context
compression or agent harnesses, an HN "Claude Code" thread, or a Tavily
harness-comparison article) — check `artifacts/research/<TEST_DATE>/candidates.json`
for a `_query_key`-free but otherwise-recognizable entry if the top-30 still
doesn't show one (there just may not be a great one that week).

---

## Task B — LLM relevance-scoring stage before ranking

### Problem

`_dedupe_candidates()` + `_date_filter()` remove almost nothing (measured: 147
raw → 142 survive both). The only thing that decides which candidates a user
sees is `_rank_and_truncate()`'s fixed-size cutoff — a blind budget cut, not a
quality judgment. This is how a literal job-posting URL reached the top-30
with high importance. There is currently no genuine "is this worth including"
signal anywhere in the pipeline.

### Model decision (already tested — do not re-litigate)

Use **`gpt-5.4-nano`** via the OpenAI API, not Claude Haiku 4.5. Two
independent test rounds (different weeks, 142 and 143 candidates, same
rubric) showed Nano scores more critically in a way that matches the
newsletter's proven-performer themes (see `docs/research-signal-quality-findings.md`
§5), and — on two different repos, across both rounds — caught real
abuse-risk content that Haiku scored favorably as "offbeat." Nano is also
~6x cheaper per run. Use the **regular (non-batch) OpenAI API**, not the
async Batch API — the score must be available synchronously before the HITL
screen renders in the same `run.py` invocation, and Batch API turnaround
(minutes to 24h) doesn't fit that.

### 1. Add the dependency

```bash
uv add openai
```

This adds `openai` to `pyproject.toml`'s `dependencies` list (currently does
not include it or any OpenAI package — verify after running).

### 2. Add config

In `src/config.py`, alongside the existing `TAVILY_API_KEY` /
`RESEARCH_COLLECTOR_MODEL` pattern:

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model used for the pre-ranking relevance/junk-filter pass in research_collector.
RESEARCH_RELEVANCE_MODEL = os.getenv("RESEARCH_RELEVANCE_MODEL", "gpt-5.4-nano")
```

Add `OPENAI_API_KEY=...` to `.env` (and to `.env.example` / the README's
required-keys list if one exists — check for it, this project documents
required env vars in `CLAUDE.md` under "Environment Setup").

### 3. Add the relevance-scoring function to `research_collector.py`

Insert after `_default_summarizer` (same file). This mirrors that function's
shape (batch call, JSON in/out, `[]`/exception on failure so the caller can
fall back) but calls OpenAI directly since `RESEARCH_RELEVANCE_MODEL` is
`gpt-5.4-nano`, not an Anthropic model — `init_chat_model` isn't the right fit
here without adding `langchain-openai` too, so use the `openai` SDK directly,
same as it was tested with.

```python
RELEVANCE_RUBRIC = """You score AI-agent-news candidates for a Korean newsletter ("Automata") read by AI agent enthusiasts and builders.

Score each candidate 0-10 on how likely it is to make a genuinely engaging newsletter item, plus whether it's junk.

HIGH value (7-10) — the newsletter's proven winning themes:
- Practical Claude Code / coding-agent tips, workflow hacks, token-saving techniques
- Agent harness or framework comparisons (e.g. two competing open-source agent projects)
- Offbeat or whimsical real-world agent applications with genuine substance (not just a press release)
- Industry drama or controversy involving an AI platform and its developer ecosystem
- Coding/agent benchmark head-to-head comparisons
- Open-source tools solving one concrete, specific developer pain point (not generic model releases)

MEDIUM value (4-6):
- Generic new model release announcements
- Official company blog posts
- Research papers with practical deployment relevance
- General AI industry news

LOW value / JUNK (0-3) — set is_junk=true for these:
- Job postings / recruiting pages
- Bare homepage stubs or link-redirect wrapper pages with no real article content
- Generic benchmark table dumps with no narrative
- Marketing/conference promo pages
- Near-duplicate of a bigger story already covered elsewhere in this same list

Return a JSON object of the form {"results": [...]}, where "results" is an array with one object per input item, in the SAME ORDER as the input, each with exactly these keys:
- "url": string, copied exactly from input
- "score": integer 0-10
- "is_junk": boolean
- "reason": string, one short phrase (<=15 words)

Return ONLY the JSON object. No other text.
"""

_JUNK_SCORE_THRESHOLD = 3  # drop candidates scored <= this, matching the rubric's JUNK band (0-3)


def _default_relevance_scorer(items: list[dict]) -> list[dict]:
    """Score candidates for newsletter relevance in a single batch LLM call.

    Args:
        items: list of {"url", "title", "source", "category", "snippet"} dicts.

    Returns:
        List of {"url", "score", "is_junk", "reason"} dicts. Returns [] on
        any error (caller keeps existing heuristic scores unchanged).
    """
    from openai import OpenAI
    from .. import config

    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=config.RESEARCH_RELEVANCE_MODEL,
            messages=[
                {"role": "system", "content": RELEVANCE_RUBRIC},
                {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        return parsed["results"]
    except Exception:
        return []


def _score_relevance(candidates: list[dict], scorer) -> list[str]:
    """Score every candidate's newsletter relevance in place via `scorer`,
    then drop candidates scored at or below `_JUNK_SCORE_THRESHOLD`.

    Uses the model's numeric score against a fixed threshold to decide what
    counts as junk, NOT the model's own is_junk boolean — testing showed the
    boolean cutoff disagreed with the score-based judgment more often than
    the underlying reasoning actually differed (boundary noise, not a real
    quality signal). is_junk is still stored on the candidate for visibility.

    Returns a list of error messages (empty on full success). Never raises;
    on any failure, candidates keep score=None and nothing is dropped, so
    the pipeline falls back to the existing heuristic-score ranking.
    """
    if not candidates:
        return []

    items = [
        {
            "url": c["url"],
            "title": c["title"],
            "source": c["source"],
            "category": c["category"],
            "snippet": (c.get("summary") or "")[:300],
        }
        for c in candidates
    ]

    errors: list[str] = []
    try:
        results = scorer(items)
    except Exception as exc:
        results = []
        errors.append(f"relevance_scorer: {exc}")

    by_url = {r["url"]: r for r in results if isinstance(r, dict) and "url" in r}
    if not by_url:
        errors.append("relevance_scorer: no valid scores returned, skipping relevance filter")
        for c in candidates:
            c["relevance_score"] = None
            c["is_junk"] = False
        return errors

    for c in candidates:
        r = by_url.get(c["url"])
        c["relevance_score"] = r.get("score") if r else None
        c["is_junk"] = bool(r.get("is_junk")) if r else False

    return errors
```

### 4. Wire it into the pipeline

In `_collect_weekly_research_core()`:

```python
    candidates = _normalize_candidates(raw_results)
    total_found = len(candidates)

    candidates = _dedupe_candidates(candidates)
    candidates = _date_filter(candidates, publication_date)

    # ADD THESE THREE LINES — score relevance on the full deduped/date-filtered
    # pool, before truncation, so the LLM judgment actually drives what survives.
    if relevance_scorer is None:
        relevance_scorer = _default_relevance_scorer
    errors.extend(_score_relevance(candidates, relevance_scorer))
    candidates = [
        c for c in candidates
        if not (c.get("relevance_score") is not None and c["relevance_score"] <= _JUNK_SCORE_THRESHOLD)
    ]

    candidates = _rank_and_truncate(candidates, max_search_results)
```

Add `relevance_scorer=None` as a parameter to `_collect_weekly_research_core()`
(same DI pattern as the existing `summarizer=None` param — see its signature),
so tests can inject a fake scorer instead of hitting the real API.

**Also update `_rank_and_truncate()`'s sort key** to prefer the relevance
score when present, falling back to the existing heuristic score when it
isn't (API failure, or a candidate that somehow skipped scoring):

```python
        for group in query_groups:
            group.sort(
                key=lambda c: c["relevance_score"] if c.get("relevance_score") is not None else c["score"],
                reverse=True,
            )
```

This makes the LLM relevance score the primary ranking signal within each
query group once Task A's two-level interleave is in place, while staying
safe if the relevance call fails for a run.

### 5. Cost/latency note for whoever reviews this

Measured (not estimated) on a 142-candidate run: ~20-26K input tokens,
~7-10K output tokens per relevance-scoring call, i.e. **a few cents per
weekly run** on `gpt-5.4-nano`. See `docs/research-signal-quality-findings.md`
§5 for the exact table. Runs once per `collect_weekly_research()` call
(cached via `load_candidates()` the same way summarization already is — no
extra caching needed).

### Tests to add

New test file section or additions to `tests/test_research_collector.py`,
following existing conventions (see `_default_summarizer`'s tests for the
pattern — search for `summarizer=` in that file):

- `_score_relevance` with a fake scorer returning known scores → candidates
  below `_JUNK_SCORE_THRESHOLD` are dropped, `relevance_score`/`is_junk` set
  correctly on survivors.
- `_score_relevance` with a scorer that raises → returns an error message,
  no candidates dropped, `relevance_score` is `None` on all (pipeline falls
  back to heuristic ranking).
- `_score_relevance` with a scorer returning a malformed/missing-`results`
  response → same fallback behavior as above.
- `_collect_weekly_research_core` with a fake `relevance_scorer` injected
  (mirrors existing tests that inject a fake `summarizer`) → confirms the
  wiring end-to-end without hitting the real OpenAI API.

### Manual verification (do this after Task A's manual verification passes)

Re-run the same before/after methodology used to validate Task A, but also
confirm:
1. `artifacts/research/<TEST_DATE>/candidates.json` entries have
   `relevance_score` and `is_junk` populated.
2. No obviously-junk items (job postings, bare homepage stubs) survive into
   the printed `render_selection_list()` output.
3. `errors` in the `collect_weekly_research()` return value is empty (or, if
   `OPENAI_API_KEY` isn't set in the test environment, contains exactly the
   `relevance_scorer:` fallback message — confirm the run still completes
   and produces the same result as before this change, i.e. graceful
   degradation actually works).

---

## Order of operations for this session

1. Task A code changes → run existing `tests/test_research_collector.py` →
   add the new interleave-fairness test → manual verification.
2. Task B code changes → `uv add openai` → config → manual verification with
   a real `OPENAI_API_KEY` (ask the user for one if `.env` doesn't have it —
   see `docs/research-signal-quality-findings.md` for the fallback options
   discussed if they'd rather not add a key).
3. Full pipeline smoke test: `uv run python run.py --refresh --hitl` for a
   real or test date, confirm the HITL topic-selection screen shows a
   qualitatively better list than what's documented as "before" in
   `docs/research-signal-quality-findings.md`.
