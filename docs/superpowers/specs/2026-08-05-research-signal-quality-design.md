# Research Signal Quality — Design

**Date:** 2026-08-05
**Status:** Approved for planning
**Scope:** `src/tools/research_collector.py`, `src/tools/search_tools.py`, `src/tools/content_tools.py`, `src/tools/research_report.py` (category labels only). Does not touch the HITL selection flow, orchestrator, or article-writer — those consume `candidates.json` as-is regardless of how it's populated.

## Problem

`collect_weekly_research()` is deterministic and well-tested, but the content it surfaces is generic SEO listicle material — "Top 10 AI Tools," "The Definitive Guide to AI Agent Deployment," "I tried 70+ AI tools" — instead of eye-opening launches or novel use cases. A real run's output (2026-08-05, 20 candidates) had 16 of 20 items in this category. Root causes:

1. **`include_domains` is commented out** in `search_ai_news` (`search_tools.py:82-89`). Tavily searches the open web with no quality filter, and "advanced" search depth ranks by relevance/freshness-of-crawl rather than actual publish date — evergreen content-mill pages that get periodically re-crawled outrank genuine recent news.
2. **`published_at` is hardcoded to `None` for every Tavily result** (`research_collector.py:155`). This means every Tavily candidate shows "날짜 미상," eats the `-0.5` score penalty regardless of actual freshness, and — more importantly — never gets checked against `_date_filter`'s 14-day window, so old evergreen pages that should be excluded aren't.
3. **Query wording is generic** ("AI developer tools," "AI agent deployment guide," "AI 스타트업 산업 동향"). This is exactly the phrasing SEO listicles target, and four of the eight query categories (`tools_infra`, `industry_business`, `policy_society`, `study_resources`) exist almost entirely to produce this kind of roundup content.
4. **No structural defense against listicle titles.** Nothing rejects "Top N," "Best X for 2026," "Ultimate/Definitive Guide" patterns even as a safety net.
5. **No source is inherently novelty-biased.** HN and PyTorch-KR are naturally bottom-up, but they're a small fraction of the query plan (3 of 13 queries); the rest is Tavily hunting for content that, by construction, only content mills reliably produce.

## Goals

1. Surface novel tool/model launches and viral demos — content a reader hasn't already seen — over generic roundups and reports.
2. Every Tavily-touching query is either narrowly scoped to a specific, non-listicle-prone source class (official-ish tech press, arXiv) or removed in favor of a naturally bottom-up source (HN, GitHub).
3. Dates are real where available, and stale content is actually filtered rather than silently passed through as "date unknown."
4. Add GitHub as a source: both "just launched" (new repos gaining traction) and "genuinely viral this week" (established trending) signals.
5. Official lab blog posts that are customer/use-case stories get pulled into `real_world_usecases` instead of sitting undifferentiated in `official_blogs`.

## Non-goals

- Changing dedup, ranking-truncation, fetch, or summarization mechanics — those stay as-is.
- Changing the HITL selection flow, `research_report.py` rendering logic (beyond the category label table), or anything downstream of `candidates.json`.
- Adding a `GITHUB_TOKEN` / auth — unauthenticated GitHub Search API rate limit (10 req/min) comfortably covers the 2 calls/run this design adds (verified live, see Testing).
- Guaranteeing the `study_cafe` newsletter slot stays filled every week. Accepted regression — see Accepted tradeoffs.

## Architecture

### Query plan: 13 queries → 8

| Category | Before | After |
|---|---|---|
| `model_releases` | 2 Tavily queries | unchanged, + domain whitelist |
| `agents_automation` | 1 HN + 1 Tavily | HN only — Tavily leg dropped |
| `research_papers` | 1 Tavily (arXiv) | unchanged, + domain whitelist |
| `real_world_usecases` | 1 HN (Show HN) + 1 Tavily | HN only — Tavily leg dropped; gains candidates via blog-category routing (below) |
| `tools_infra` | 1 Tavily | **dropped** |
| `industry_business` | 1 Tavily | **dropped** |
| `policy_society` | 1 Tavily | **dropped** |
| `study_resources` | 1 Tavily | **dropped** (see Accepted tradeoffs) |
| `official_blogs` | 1 (RSS/scrape, no query) | unchanged mechanism; case-study posts re-routed to `real_world_usecases` |
| `pytorch_kr_community` | 1 (scrape, no query) | unchanged |
| `github_trending` (**new**) | — | 2 GitHub Search API queries + 1 trending-page scrape |

Net query count: 13 → 8 (2 model_releases + 1 agents_automation + 1 research_papers + 1 real_world_usecases + 3 github_trending), plus the 2 no-query source-routing entries (official_blogs, pytorch_kr).

`CATEGORY_LABELS_KO` (`research_report.py`) drops the four removed categories and adds `"github_trending": "오픈소스"`.

### GitHub as a source — two distinct signals

Verified live against the real API/page before committing to this design (see chat transcript for raw output):

**1. Search API — "just launched."** `GET /search/repositories?q={query}+created:>{14d-ago}&sort=stars&order=desc`, two query variants:
   - `topic:ai-agents`
   - `agent AI in:name,description`

   Tested 2026-08-05: both returned genuinely novel, non-listicle repos (`microsoft/skill-recorder` 1.7k★, `perplexityai/numbat` 684★, `kvcache-ai/AgentENV` 2.9k★, etc.), created in the prior 14 days. Confirmed via `/rate_limit`: unauthenticated search quota is 10/min; 2 queries/run is well within it.

   Rejected variant: adding `stars:>10000` to a `created:>` query returns **0 results** — brand-new repos don't hit 10k★ in two weeks, this qualifier combo is a dead end. Also rejected: `stars:>10000` + `pushed:>14d-ago` (i.e., "big and recently active") — tested and it just resurfaces already-famous repos (`langchain`, `dify`, `browser-use`) that had *any* commit recently, which is true of nearly every popular active repo. Not a novelty signal.

**2. Trending-page scrape — "viral this week."** GitHub's own trending algorithm (stars gained *this week*, not total) is only exposed via `github.com/trending?since=weekly` HTML, not the API. Scraped with the same BeautifulSoup pattern the Anthropic blog fetcher already uses (`content_tools.py:165-232`, `article.Box-row` → repo link, description, "N stars this week" span). Confirmed live: clean structured extraction, e.g. `block/buzz` (7,372★/week), `microsoft/AI-For-Beginners` (7,554★/week).

   The trending page isn't AI-scoped — it's global. Results are keyword-filtered post-scrape (name+description contains one of `agent`, `ai`, `llm`, `gpt`, `claude`, `gemini`) to stay on-topic. This is a real, accepted false-negative risk (an on-topic repo using none of these words is missed) traded for simplicity — see Accepted tradeoffs.

### Listicle title filter (safety net, all sources)

Applied in `_normalize_candidates`, before a candidate is constructed, regardless of source tool:

```python
_LISTICLE_TITLE_PATTERNS = [
    re.compile(r"\btop\s*\d+\b", re.IGNORECASE),
    re.compile(r"\bbest\b.*\b(tools?|ai)\b", re.IGNORECASE),
    re.compile(r"\d+\+?\s*(best|top)\b", re.IGNORECASE),
    re.compile(r"\bguide to\b", re.IGNORECASE),
    re.compile(r"\b(definitive|ultimate) guide\b", re.IGNORECASE),
    re.compile(r"완벽\s*가이드"),
    re.compile(r"가이드$"),
]
```

A title matching any pattern is dropped outright (not score-penalized) — structurally, this content is never what the newsletter wants, regardless of what else it scores on.

### Official blog case-study routing

`_normalize_candidates`'s `"blog"` branch already receives a `category` field per post (OpenAI/DeepMind RSS `<category>`, Anthropic's scraped section label — `content_tools.py:211-216`). If that raw tag contains `customer`, `story`, or `case stud` (case-insensitive substring), the candidate's `category` is set to `"real_world_usecases"` instead of `"official_blogs"` — picking up the `+0.3` boost and the `real_world_usecases` "always 높음" importance rule. Posts with other tags (`Announcements`, `Product`, etc.) are unaffected.

### Published-date capture for Tavily

`_normalize_candidates`'s `"tavily"` branch currently discards Tavily's `published_date` field. Wire it through and parse to `YYYY-MM-DD`, falling back to `None` on parse failure (existing `-0.5` penalty path unchanged for genuinely undated results). **Implementation must verify the actual field name/format against a live Tavily response** — this design assumes `published_date` per Tavily's documented advanced-search schema, but field names have drifted before and no live key was available while writing this spec.

This has a real second-order effect: once dates are populated, `_date_filter`'s 14-day window actually applies to Tavily results for the first time. Expect the two remaining Tavily categories (`model_releases`, `research_papers`) to return fewer, more genuinely-recent candidates — this is the intended fix, not a regression.

### Domain whitelist

Re-enable `include_domains` in `search_ai_news` (`search_tools.py`), using the list already documented (but not enforced) in `CLAUDE.md`:

```python
include_domains=[
    "anthropic.com", "openai.com", "ai.google", "blog.google",
    "huggingface.co", "arxiv.org",
    "techcrunch.com", "theverge.com", "venturebeat.com", "wired.com", "arstechnica.com",
],
```

`exclude_domains` (currently `openai.com`, `anthropic.com`, `deepmind.google` — deduped against `official_blogs`) stays as-is; a URL blocked by both lists is still blocked, and `_dedupe_candidates` handles any residual overlap by canonical URL regardless.

### Missing-date penalty reduced: -0.5 → -0.2

The current `-0.5` penalty for missing/unparseable `published_at` (`research_collector.py:192-193`) is larger than any single novelty boost (`+0.3`), so one undated item can flip a `real_world_usecases`/`github_trending` candidate negative even when it's otherwise exactly the kind of content this design is trying to surface. Reduced to `-0.2` — still a real penalty (dated items rank ahead of undated ones, all else equal), but no longer able to override the novelty boost on its own.

This interacts with the Tavily date-capture fix above: once Tavily results carry real dates, the penalty applies almost exclusively to `github_trending`'s weekly-trending leg (which has no per-repo date, only a fetch-time approximation — see Accepted tradeoffs) and any source where date parsing genuinely fails. It stops being the blanket penalty it effectively was before.

### Candidate cutoff raised: top 20 → top 30

`max_search_results` (`collect_weekly_research`/`_collect_weekly_research_core` default, `research_collector.py:437,485`) goes from 20 to 30. With four categories now producing flat, closely-clustered scores (`0`, `0.3`, `0.2`, `0.5` combinations from the boost/penalty system above) instead of Tavily's more spread-out relevance floats, more candidates tie or cluster near the truncation boundary — raising the cutoff reduces the chance a legitimate novel item gets silently dropped at exactly the point this design is trying to surface more of them. `max_fetches` (full-content fetch + summarization budget, still 8 by default) is unchanged — this only widens what survives into `candidates.json` for the user to see and pick from, not what gets the expensive fetch/summarize treatment.

### Score boost extended to `github_trending`

The existing `if category == "real_world_usecases": score += 0.3` becomes a set membership check:

```python
_NOVELTY_BOOST_CATEGORIES = {"real_world_usecases", "github_trending"}
...
if category in _NOVELTY_BOOST_CATEGORIES:
    score += 0.3
```

`research_report.py`'s `_importance()` gets the same set applied to its "always 높음" rule, so GitHub candidates are surfaced with the same visual priority as real-world use cases.

## Components

| Module | Change |
|---|---|
| `src/tools/search_tools.py` | Re-enable `include_domains` in `search_ai_news`; add `search_github_repos(query, publication_date, max_results=6)` — GitHub Search API, `created:>` window, sort by stars |
| `src/tools/content_tools.py` | Add `fetch_github_trending(publication_date)` — scrape `github.com/trending?since=weekly`, keyword-filter, return `{full_name, url, description, stars_this_week}` list |
| `src/tools/research_collector.py` | `RESEARCH_QUERY_PLAN`: drop 4 categories' entries, drop 2 Tavily legs, add 3 `github_trending` entries. `_run_searches`: dispatch `github_search`/`github_trending_scrape` tool types. `_normalize_candidates`: capture Tavily `published_date`; add listicle title filter; add blog category→`real_world_usecases` routing; add github normalize branches; extend score-boost set; missing-date penalty `-0.5` → `-0.2`. `max_search_results` default `20` → `30` |
| `src/tools/research_report.py` | `CATEGORY_LABELS_KO`: drop 4 entries, add `github_trending`; `_importance()`: extend "always 높음" set |

No new files, no new dependencies (`httpx`, `bs4` already used for the existing PyTorch-KR/Anthropic scrapers).

## Data contract

Unchanged. GitHub-sourced candidates populate the same shape every other candidate does:

```python
{
    "title": str,        # repo full_name, e.g. "microsoft/skill-recorder"
    "url": str,           # html_url (search) or constructed https://github.com/{full_name} (trending)
    "source": "github.com",
    "published_at": str | None,   # repo created_at date (search); publication_date as fetch-time approximation (trending, since the page has no per-repo creation date)
    "summary": str,        # repo description; trending items append stars-this-week for context
    "key_facts": [],
    "why_it_matters": "",
    "topic_type": "main",
    "category": "github_trending",
    "score": 0.3,           # baseline 0 (no Tavily-equivalent relevance score) + novelty boost
    "fetched": False,
}
```

`fetched` content for GitHub items goes through the existing generic path: `_fetch_top_candidates` → `fetch_article_content(url)`. No GitHub-specific README fetcher is added — GitHub repo pages render the README inside an `<article>` tag, which `fetch_article_content`'s existing selector list already targets. Building a dedicated contents-API fetcher (mirroring PyTorch-KR's `prefetched_content` mechanism) was considered and rejected as unneeded complexity until the generic path is observed to produce bad results.

## Error handling

| Failure | Behavior |
|---|---|
| GitHub Search API rate-limited or errors | Caught in `_run_searches`'s existing per-query try/except (same pattern as every other tool branch); that query's items become `[]`, error appended, run continues |
| `github.com/trending` scrape fails (layout change, network) | Caught inside `fetch_github_trending`, returns `{"posts": [], "errors": [...]}"`; `_run_searches` surfaces the error, run continues |
| Tavily `published_date` field missing/unparseable | Falls back to `None`, existing `-0.5` penalty path, unchanged |
| Listicle-filter false positive (rejects a legitimate title) | Accepted risk — title-pattern matching is inherently heuristic. No override mechanism; if this proves too aggressive in practice, narrow the regexes |
| Blog category-routing false negative (a case-study post's category tag doesn't match keywords) | Post stays in `official_blogs` instead of `real_world_usecases` — degrades to today's behavior for that post, not a new failure mode |

## Testing

Existing pattern in this codebase is inline `assert`-based checks alongside the pytest suite (`test_research_collector.py`, 476 lines, explicitly called out as untouched in the prior design doc). This change adds:

- `_is_listicle_title`: table of known-bad titles from the real 2026-08-05 output (all 16 junk titles) must all match; a handful of legitimate titles (e.g. "Anthropic ships Claude Code skill for X") must not.
- Blog category routing: a post with `category="Customer story"` → `category` becomes `real_world_usecases`; a post with `category="Announcements"` → unchanged.
- `_normalize_candidates` github branches: one search-API-shaped item and one trending-shaped item each produce a correctly-shaped candidate dict with the `github_trending` category and `+0.3` score.
- `search_github_repos` / `fetch_github_trending`: mocked-response unit tests (no live network in the test suite), consistent with how `search_hackernews`/`fetch_official_blog_posts` are already tested.

No new tests hit live APIs — the existing `integration` marker convention holds. (The live verification in this design doc's Architecture section was exploratory, run manually during design, not part of the committed test suite.)

## Accepted tradeoffs

- **`study_resources` category is dropped.** It fed the newsletter's dedicated `study_cafe` article slot (`config.py:48`, `study_cafe.md`). The batch summarizer can still opportunistically tag any fetched candidate as `study_cafe` based on content (`config.py:70`), but there's no longer a dedicated query hunting for tutorials — some weeks the slot may go unfilled. Explicitly chosen: tutorials are out of scope for "eye-opening/novel" content, and a dedicated-but-listicle-prone query isn't worth keeping just to guarantee slot coverage.
- **Trending-page keyword filter has false negatives.** An on-topic repo whose name/description uses none of `agent/ai/llm/gpt/claude/gemini` (e.g., a paper-implementation repo just called "reverse-skill") is silently dropped from the trending leg. Accepted for simplicity; the Search API leg's `topic:`/keyword-scoped queries don't have this gap.
- **GitHub trending "published_at" is an approximation.** The weekly trending page shows momentum, not a creation or event date; items get `publication_date` (today) rather than a real date. This is consistent with how the category is used (rank by novelty/score, not by chronological placement) but means `_date_filter`'s window check is a no-op for this leg specifically.
- **Tavily field-name assumption is unverified.** `published_date` capture is designed against Tavily's documented schema but not confirmed against a live call (no API key available while writing this spec). First implementation step should be a live sanity check before wiring the parse logic in.

## Net effect

13 search-plan entries → 8, 4 SEO-listicle-prone categories removed outright, a structural listicle-title filter added as a backstop, Tavily's date blindness fixed (both fixing false "날짜 미상" spam and enabling real staleness filtering), and two new bottom-up signals added (GitHub Search API for brand-new projects, GitHub trending scrape for real viral momentum) — both verified against live data during design rather than assumed to work. Scoring rebalanced (missing-date penalty `-0.5` → `-0.2`, so it can no longer override a novelty boost on its own) and the candidate pool widened (top 20 → top 30) to match the new boost/penalty system's flatter score distribution.
