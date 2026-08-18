# Research Signal Quality — Findings & Recommendations

## Context

`run_weekly_research()` (`src/tools/research_collector.py`) searches a fixed set of
categories via Tavily, HN, GitHub, and a PyTorch-KR forum scraper, then ranks and
truncates the results to a `max_search_results`-sized candidate list shown to the
user at the HITL topic-selection step. This document captures what we learned
investigating and improving that pipeline's signal quality, and what's still open.

## What changed in code (this session)

1. **Dropped `include_domains` from `search_ai_news()`** (`src/tools/search_tools.py`).
   The previous 11-domain Tavily allowlist was silently suppressing exactly the
   content that performs best for this newsletter — tips/how-to articles and
   independent commentary from sites like xda-developers.com, Axios, and Brookings
   were structurally invisible. `exclude_domains` (blocking anthropic.com/openai.com/
   deepmind.google, already covered by the `official_blogs` fetcher) was kept.

2. **Added 9 new query-plan entries** to `RESEARCH_QUERY_PLAN`
   (`src/tools/research_collector.py`):
   - `agents_automation`: HN `"Claude Code"`, HN `"coding agent"`, Tavily
     `"AI coding agent harness comparison"`, Tavily `"AI agent framework launch
     {month_en} {year}"`, Tavily `"AI agent startup funding {month_en} {year}"`
   - `research_papers`: Tavily `"multi-agent orchestration production lessons
     learned"`
   - `real_world_usecases`: Tavily `"how teams integrate AI agents into workflow"`
   - `github_trending`: `"token compression OR context compression LLM"`,
     `"agent harness"`

## Key findings

### 1. The newsletter's own archive is the ground truth for "what works"

Reading maily.so/automata's 28-issue archive and its 조회 (view count) history
replaced guessing with evidence. Ranked by what actually drove engagement:

| Issue | Views | Theme |
|---|---|---|
| V.17 | 6.03K (huge outlier) | Claude Code token/usage-saving tips |
| V.18 | 915 | Agent harness comparison (OpenClaw vs Hermes) |
| V.08 | 628 | Offbeat real agent usecase (Claude growing tomatoes) |
| V.16 | 553 | Autonomous-agent capability + platform drama |
| V.06 | 551 | Agent commerce/shopping protocol |
| V.10 | 496 | Coding benchmark head-to-head |

Every query and source change below was validated against these themes, not
against generic "AI news" intuition.

### 2. Tool choice matters more than query phrasing

- **HN rewards short, exact phrases** (`"Claude Code"` → 281pts/305 comments);
  padding the same idea (`"Claude Code usage"`) collapsed to near-zero. Tavily
  rewards fuller descriptive phrases — the opposite tuning.
- **GitHub search was the missing tool for the top two themes.** Reading the
  actual content of V.17 and V.18 revealed they're tool roundups and repo
  comparisons, not news articles — `search_github_repos("token compression OR
  context compression LLM")` and `search_github_repos("agent harness")` surfaced
  directly on-theme repos (Supercompress 42★, phone-harness 1383★,
  boundary-bench) that neither Tavily nor HN could reach.
- **Some themes are structurally unreachable by any current tool** (V.08's
  offbeat story was sourced from a single X/Twitter post; nothing in the
  pipeline searches X). Flagged as a real gap, not solved.

### 3. Ranking bug: new queries return good content but never surface

`_rank_and_truncate()` interleaves categories round-robin, but *within* a
category it falls back to declaration order on score ties — and most scores
are ties (flat category boosts, boolean HN>50pts threshold, flat github_search
scores). After adding queries, `github_trending` went from 3 sources to 5 and
`agents_automation` from 1 to 6, but the newly added queries' items were
confirmed present in `raw_search_results.json` (147 total_found) and still
**zero of them reached the final 30-item list** shown at the HITL step — older
queries always won ties. Fix proposed but not yet implemented: extract the
existing category-round-robin into a reusable `_interleave()` helper and apply
it one level deeper, across queries within each category, not just across
categories. A secondary fix (bumping `max_search_results`) was also discussed
as a smaller, complementary tuning knob.

### 4. Filtering is nearly a no-op today; the real gatekeeper is a blind budget cutoff

Traced the full funnel for one live run: 147 raw hits → 142 after
dedup/date-filter (only 5 removed by quality gates) → 30 shown to the user.
**112 of 142 candidates that passed every quality check were discarded purely
for lack of space**, not because they were judged uninteresting — there is
currently no genuine relevance/quality signal, only category-boost heuristics
and a fixed-size cutoff. This is why a literal job posting reached the final
list with 중요도 높음 (high importance).

### 5. LLM relevance-scoring: GPT-5.4 Nano outperformed Claude Haiku 4.5 in a two-round test

Proposed adding an LLM relevance/junk-filter pass before ranking, using a
rubric built from the finding-1 themes (see `RUBRIC` prompt below). Tested
head-to-head against 142 candidates (2026-08-12 window) and again against 143
fresh candidates (2026-08-05 window, an independent week):

| | Claude Haiku 4.5 | GPT-5.4 Nano |
|---|---|---|
| Round 1 avg score / junk flagged | 6.02 / 5 | 4.43 / 7 |
| Round 2 avg score / junk flagged | 5.96 / 11 | 4.75 / 12 |
| Junk-flag agreement (R1 / R2) | 99% / 92%* | |
| Cost this run (standard API, not batch) | ~$0.078 | ~$0.013 |

\* The 92% figure is boundary noise, not real disagreement — every
junk-flag mismatch in round 2 had near-identical reasoning text from both
models; they just drew the binary cutoff at a slightly different score
threshold.

**Nano was more critical of shallow/marketing content** (roundups, "launch
week" press posts) in a way that matches what section 1 established actually
performs. More importantly, **Nano caught a real abuse-risk item Haiku missed,
twice, independently**: `sv-number/mcp-server` (an MCP tool for buying phone
numbers and reading SMS verification codes) was scored 7/"offbeat real-world
application" by Haiku and 0/"security-ethics risk" by Nano in round 1;
`zhaoxuya520/reverse-skill` (a "penetration/reverse-engineering skill router")
showed the same pattern in round 2. Nano is also ~6x cheaper per run.

Rubric used for both models (system prompt, byte-identical rubric text; only
the OpenAI call needed a `{"results": [...]}` wrapper due to `json_object`
response-format constraints):

```
You score AI-agent-news candidates for a Korean newsletter ("Automata") read by AI agent enthusiasts and builders.

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

Return a JSON array, one object per input item, in the SAME ORDER as the input, each with exactly these keys:
- "url": string, copied exactly from input
- "score": integer 0-10
- "is_junk": boolean
- "reason": string, one short phrase (<=15 words)

Return ONLY the JSON array. No other text.
```

Async Batch API pricing (50% discount) doesn't fit this pipeline well — the
score needs to be available synchronously within the same `run.py` invocation,
before the HITL screen renders, and Batch API turnaround can take up to 24h.
Recommendation is the regular (non-batch) API in one consolidated call, same
pattern as the existing `_default_summarizer`.

## Open items / next steps

1. **Fix the ranking bug (finding 3)** — reusable `_interleave()` helper applied
   at both the query-within-category and category-within-run levels — before
   any of the new queries added in this session can actually reach users.
2. **Implement the relevance-scoring stage (finding 5)** using GPT-5.4 Nano,
   with `is_junk` derived from a fixed score threshold rather than trusting
   each model's own boolean (round-2 data showed the boolean cutoff is noisier
   than the underlying score).
3. **Re-verify the final HITL candidate list** end-to-end once both fixes land,
   using the same before/after methodology as the ranking-bug investigation.
4. **Known unaddressed gap**: offbeat/whimsical usecase content (V.08-style)
   is sourced from X/Twitter in the newsletter's own history; no current tool
   searches it. Not solved this session.
