# PyTorch-KR Forum Research Source — Design

**Date:** 2026-07-15  
**Status:** Approved for specification; awaiting user review before implementation

## Goal

Add the PyTorch Korean Users Group's **읽을거리&정보공유** forum (`https://discuss.pytorch.kr/c/news`) as a first-class source for the weekly newsletter research pipeline. The research agent must receive recent forum topics alongside Tavily, Hacker News, and official-blog results, then select interesting newsletter topics from the combined candidate pool.

For each forum post, retain both the Korean forum summary and the original/primary source URL that the forum post is based on.

## Scope

### In scope

- Collect forum topics published during the seven days ending on `publication_date`.
- Extract each topic's title, forum URL, publication date, tags, first two text paragraphs, and primary-source URL.
- Integrate the results into `collect_weekly_research` as a new category.
- Normalize, deduplicate, rank, truncate, summarize, persist, and report forum candidates through the existing research pipeline.
- Add deterministic unit tests and an opt-in live integration test.

### Out of scope

- Browser/UI automation or simulated infinite scrolling.
- Scraping replies beyond the original post.
- Changing the newsletter topic-selector policy or reserving a forum-specific quota.
- Fetching the original external source's full content as part of this feature.
- Authentication, posting, commenting, or other write operations on PyTorchKR.

## Approach Selection

### Recommended: Discourse JSON API

Use the forum's public Discourse endpoints:

- `GET /c/news/14/l/latest.json?page=N` for paginated topic listings.
- `GET /t/{topic_id}.json` for a topic's original post, rendered HTML, and outbound-link metadata.

The UI's scroll-driven loading is backed by this pagination. Direct JSON calls are therefore more reliable and testable than browser scrolling, avoid rendering/timing concerns, and expose the full original post needed for the requested two-paragraph excerpt and primary source URL.

### Alternatives considered

1. **Browser scroll + HTML scraping** — mirrors the visual page but is slower and more fragile because dynamic loading, selectors, and timing can change.
2. **Category RSS feed** — supplies title, date, link, and often a full description, but is blocked for generic bots in the site's `robots.txt` and is limited to 25 items/page. It also does not expose outbound-link metadata as reliably as topic JSON.
3. **Listing JSON only** — cheap, but insufficient because it lacks the forum post prose and primary-source link.

## Architecture

### New source adapter

Add `search_pytorch_kr_forum(publication_date: str) -> str` in `src/tools/search_tools.py`.

It returns a JSON string with the same error-as-data convention as the existing search tools. A successful item has this source-specific shape:

```json
{
  "title": "…",
  "forum_url": "https://discuss.pytorch.kr/t/{slug}/{id}",
  "original_url": "https://primary-source.example/…",
  "content": "first paragraph\n\nsecond paragraph",
  "published_at": "YYYY-MM-DD",
  "tags": ["…"]
}
```

`original_url` falls back to `forum_url` when no qualifying external source can be identified.

### Pipeline integration

Add a `pytorch_kr_community` item to `RESEARCH_QUERY_PLAN` with a new `pytorch_kr` tool type. Extend `_run_searches` to call the forum adapter and `_normalize_candidates` to map its source-specific records to the existing candidate schema.

Normalized forum candidates use:

- `source`: `"discuss.pytorch.kr"`
- `url`: the forum URL, preserving the Korean community context
- `original_url`: the extracted external/primary source
- `published_at`: the forum topic's `created_at` date
- `summary`: first two meaningful forum paragraphs
- `category`: `"pytorch_kr_community"`
- `topic_type`: `"main"` by default
- `prefetched_content`: the two-paragraph forum excerpt, retained internally for later batch enrichment
- `fetched`: initially `false`; it becomes `true` only when the candidate is selected for the existing shared enrichment budget

Forum candidates compete normally in the existing deduplication, shared ranking, and `max_search_results` truncation. They receive **no reserved quota** and do not bypass the shared `max_fetches`/summarization policy. When a forum candidate is among the shared top `max_fetches`, `_fetch_top_candidates` uses its `prefetched_content` instead of re-fetching the forum page and passes that excerpt to the existing batch summarizer. This keeps the requested per-topic content collection while preserving the current bounded LLM-enrichment budget.

`original_url` remains an optional additive candidate field; existing consumers that do not use it remain compatible. The research-agent report will be updated to show both the forum URL and the primary source URL when they differ, so the article writer can use the original source for fact verification.

## Data Flow

1. `collect_weekly_research(publication_date)` builds the usual query plan, now including `pytorch_kr_community`.
2. `search_pytorch_kr_forum` computes the inclusive interval `[publication_date - 7 days, publication_date]`.
3. It fetches category-list JSON pages in descending recency order, skipping pinned topics and stopping when a page is older than the interval. A fixed page limit protects against unexpected pagination behavior.
4. For each in-range topic, it requests `/t/{id}.json` sequentially using the existing browser-like headers and a modest inter-request delay.
5. It parses the original post's `cooked` HTML:
   - select the first two non-empty, meaningful `<p>` elements;
   - discard image-only, empty, and boilerplate-only paragraphs;
   - convert them to clean plain text;
   - locate primary URLs by preferring `data-onebox-src` external URLs, then external `<a href>` links;
   - exclude internal forum, image/upload, anchor, signup, social-notification, and footer/community-promotion links.
6. The adapter returns source records, with per-topic failures captured rather than failing the entire source.
7. `research_collector` normalizes results, deduplicates equivalent titles/URLs, applies the existing date filter and shared ranking, then enriches surviving fetched candidates with the existing batch summarizer.
8. Raw results and final candidates continue to be persisted under `artifacts/research/{publication_date}/`.

## Primary Source Extraction Rules

The field represents the external resource that most directly supports the forum post:

1. Prefer the first external `data-onebox-src` URL in document order.
2. If none exists, use the first external non-image hyperlink in the original post body.
3. Reject links to `discuss.pytorch.kr`, uploads/media, anchors, the PyTorchKR home page, signup pages, Telegram/notification pages, and the standard forum footer.
4. If no qualifying URL exists, set `original_url` to the topic's own forum URL.

The original source is preserved for citation and deeper article verification; it is not automatically fetched by this new adapter.

## Error Handling and Courtesy

- Use the established `httpx.Client`, existing `_HEADERS`, a 30-second timeout, and redirect following.
- Handle category-level network/invalid-JSON failures as structured source errors.
- Handle topic-detail failures individually: skip only the failed post and record a descriptive error.
- Stop pagination on an empty page, a page whose non-pinned topics are all older than the cutoff, or the bounded maximum page count.
- Request details sequentially with a short delay to avoid burst traffic to the community forum.
- Never create, edit, or authenticate against forum content.

## Testing

Add tests following the project's existing `tests/test_blog_scraping.py` and `tests/test_research_collector.py` conventions.

### Unit tests

- Date-window boundaries, including publication-day inclusion and exclusion of topics older than seven days.
- Multi-page pagination and early stopping.
- Pinned-topic exclusion.
- First-two-meaningful-paragraph extraction, including leading image-only paragraphs.
- Primary-source selection precedence: onebox URL, plain external link fallback, and forum-URL fallback.
- Rejection of internal/footer/media URLs.
- Per-topic failure isolation and source-level error reporting.
- Query-plan coverage, search dispatch, and normalized candidate fields for the new category.

### Integration test

Add an `@pytest.mark.integration` test that calls the live public forum for a known date window and asserts that returned entries have a title, forum URL, date, two-paragraph content when available, and a populated primary-source field. The default test suite remains offline.

## Acceptance Criteria

1. `collect_weekly_research` includes a `pytorch_kr_community` source entry and can run when this source is available or unavailable without breaking the other sources.
2. Only non-pinned topics published within the inclusive seven-day period ending on `publication_date` are returned.
3. Each eligible topic carries its title, forum URL, `published_at`, tags, cleaned first two meaningful paragraphs, and `original_url` (falling back to the forum URL).
4. Original-source selection prioritizes an external onebox source and excludes PyTorchKR/internal, media, anchor, and footer links.
5. Forum candidates compete equally in existing deduplication, ranking, and truncation; no reserved quota is introduced.
6. The research agent's report shows the forum source and primary-source URL where distinct.
7. Unit tests cover parsing, pagination, date boundaries, error isolation, and collector integration; the non-integration suite passes.
8. A live integration test is marked `integration` and is not required for ordinary offline test runs.
