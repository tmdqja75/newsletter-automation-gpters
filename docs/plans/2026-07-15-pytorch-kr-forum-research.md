# PyTorch-KR Forum Research Source Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add recent PyTorch-KR 읽을거리&정보공유 posts to the deterministic weekly-research pipeline, preserving two Korean summary paragraphs and the post's primary external source URL.

**Architecture:** A source adapter in `src/tools/search_tools.py` uses the public Discourse JSON API to paginate category topics and retrieve each in-range topic's original post. It produces normalized source records containing forum metadata, a cleaned two-paragraph excerpt, and an external primary URL. `src/tools/research_collector.py` then routes the new source through its existing normalization, deduplication, ranking, bounded enrichment, artifact persistence, and research-agent reporting flow.

**Tech Stack:** Python 3.11+, `httpx`, Beautiful Soup 4, `pytest`, `unittest.mock`, existing `uv` project tooling.

**Branch:** `feature/pytorch-kr-forum-research`

**Design spec:** `docs/superpowers/specs/2026-07-15-pytorch-kr-forum-research-design.md`

**Known baseline:** `uv run pytest -m 'not integration'` currently reports **64 passed, 1 skipped, 8 errors**. The errors are pre-existing and unrelated: `tests/test_email_flow.py` patches nonexistent `src.api.newsletter_generator`. The target test suites (`tests/test_blog_scraping.py` and `tests/test_research_collector.py`) pass. Do not repair the email-flow suite in this feature.

---

## Task 1: Add deterministic parser and pagination tests for the forum adapter

**Objective:** Define the exact API, date-window, paragraph, URL-selection, and error-isolation behavior before implementing network code.

**Files:**
- Create: `tests/test_pytorch_kr_forum.py`
- Modify: `src/tools/search_tools.py` (implementation follows in Task 2)

**Step 1: Add reusable test fixtures**

Create small inline JSON/HTML fixtures in `tests/test_pytorch_kr_forum.py` rather than recording live responses:

- A listing page with an in-window topic, an exactly-seven-days-old topic, an older topic, and a pinned topic.
- A second page used to prove pagination and early stopping.
- Topic JSON whose `post_stream.posts[0].cooked` begins with an image-only paragraph, has two substantive Korean `<p>` elements, includes an external `data-onebox-src`, and ends with standard forum/footer links.
- A topic JSON with no onebox but an external plain hyperlink.
- A topic JSON with no qualifying external URL.

Use one `publication_date` (`"2026-07-15"`) throughout so the expected inclusive range is `2026-07-08` through `2026-07-15`.

**Step 2: Write failing pure-parser tests**

Import the planned helpers from `src.tools.search_tools`:

```python
from src.tools.search_tools import (
    _extract_pytorch_kr_post_fields,
    _fetch_pytorch_kr_forum_posts,
    search_pytorch_kr_forum,
)


def test_extracts_two_meaningful_paragraphs_and_onebox_source():
    content, original_url = _extract_pytorch_kr_post_fields(
        SAMPLE_TOPIC_HTML,
        "https://discuss.pytorch.kr/t/example/101",
    )

    assert content == "첫 번째 실제 본문입니다.\n\n두 번째 실제 본문입니다."
    assert original_url == "https://github.com/example/project"


def test_plain_external_link_is_used_when_no_onebox_exists():
    _, original_url = _extract_pytorch_kr_post_fields(
        SAMPLE_PLAIN_LINK_HTML,
        "https://discuss.pytorch.kr/t/example/102",
    )
    assert original_url == "https://arxiv.org/abs/2601.00001"


def test_forum_url_is_used_when_no_primary_source_exists():
    forum_url = "https://discuss.pytorch.kr/t/example/103"
    _, original_url = _extract_pytorch_kr_post_fields(SAMPLE_NO_SOURCE_HTML, forum_url)
    assert original_url == forum_url
```

Also write tests proving PyTorchKR-internal URLs, `/uploads/` media URLs, anchors, signup/home, Telegram, and footer/notification links are not chosen as primary sources.

**Step 3: Run parser tests to verify failure**

Run:

```bash
uv run pytest tests/test_pytorch_kr_forum.py -q
```

Expected: collection/import failure because the adapter helpers do not exist yet.

**Step 4: Write failing pagination and error-isolation tests**

Use a fake `httpx.Client` (or a `MockTransport`) with deterministic URL responses. Call `_fetch_pytorch_kr_forum_posts` with `request_delay_seconds=0` and assert:

- only non-pinned topics dated `2026-07-08` through `2026-07-15` are returned;
- an old topic is not fetched for detail;
- the second page is reached when needed;
- pagination stops once a non-pinned page is entirely older than the lower boundary;
- a failed `/t/{id}.json` detail call is recorded in errors while other posts are returned;
- returned source records include `title`, `forum_url`, `original_url`, `content`, `published_at`, and `tags`;
- the public `search_pytorch_kr_forum` serializes the envelope as JSON rather than raising on source failure.

**Step 5: Commit the red tests**

```bash
git add tests/test_pytorch_kr_forum.py
git commit -m "test: define PyTorch-KR forum source behavior"
```

---

## Task 2: Implement the bounded, courteous Discourse source adapter

**Objective:** Make the tests from Task 1 pass without browser automation or additional dependencies.

**Files:**
- Modify: `src/tools/search_tools.py:1-123`
- Test: `tests/test_pytorch_kr_forum.py`

**Step 1: Add constants and imports**

Add only the imports needed by the adapter:

```python
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
```

Define configuration close to the imports:

```python
PYTORCH_KR_BASE_URL = "https://discuss.pytorch.kr"
PYTORCH_KR_NEWS_CATEGORY_ID = 14
PYTORCH_KR_MAX_PAGES = 5
PYTORCH_KR_REQUEST_DELAY_SECONDS = 0.2
PYTORCH_KR_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
```

Do not add Playwright, Selenium, or a browser dependency.

**Step 2: Implement pure content and URL helpers**

Add helpers with narrow responsibilities:

```python
def _parse_pytorch_kr_created_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (AttributeError, TypeError, ValueError):
        return None


def _is_pytorch_kr_primary_source(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    if host == "discuss.pytorch.kr" or host.endswith(".discuss.pytorch.kr"):
        return False
    return host not in {"pytorch.kr", "t.me", "discuss-noti.pytorch.kr"}
```

Make the final implementation additionally reject image/media URLs by path/extension and rely on the DOM position to avoid footer links. `_extract_pytorch_kr_post_fields(cooked, forum_url)` must:

1. parse `cooked` with Beautiful Soup;
2. collect the first two non-empty `<p>` texts after HTML stripping, ignoring image-only nodes and known community/footer boilerplate;
3. choose the first qualifying external `data-onebox-src` in document order;
4. otherwise choose the first qualifying external `<a href>` in document order;
5. fall back to `forum_url`.

Return `(content, original_url)`, with paragraph text joined by `"\n\n"`.

**Step 3: Implement pagination/detail collection**

Add an internal, dependency-injected helper:

```python
def _fetch_pytorch_kr_forum_posts(
    client: httpx.Client,
    publication_date: str,
    *,
    max_pages: int = PYTORCH_KR_MAX_PAGES,
    request_delay_seconds: float = PYTORCH_KR_REQUEST_DELAY_SECONDS,
) -> tuple[list[dict], list[str]]:
    """Return source records and recoverable errors for the requested week."""
```

Implementation requirements:

- Parse `publication_date` using `%Y-%m-%d`; set `start = publication_date - timedelta(days=7)` and `end` to `23:59:59` on the publication day.
- Fetch `/c/news/14/l/latest.json?page={page}` in page order, using the constants above.
- Ignore pinned topics and duplicate topic ids.
- Build a forum permalink as `f"{PYTORCH_KR_BASE_URL}/t/{slug}/{id}"`.
- Only call `/t/{id}.json` for a topic whose parseable `created_at` is inside the inclusive range.
- Stop on an empty listing, no `more_topics_url`, the configured maximum, or after processing a page whose non-pinned, parseable topics are all older than `start`.
- Fetch topic details sequentially. Delay only between detail requests and only if another eligible topic remains.
- For every successful detail request, create exactly this source record:

```python
{
    "title": topic["title"],
    "forum_url": forum_url,
    "original_url": original_url,
    "content": content,
    "published_at": created_at.strftime("%Y-%m-%d"),
    "tags": [tag["slug"] if isinstance(tag, dict) else tag for tag in topic.get("tags", [])],
}
```

- Treat listing failures as a source error and return no further data; treat individual detail failures as per-topic errors and continue.

**Step 4: Add the public tool function**

Implement the public wrapper, preserving the existing tools' error-as-data behavior:

```python
def search_pytorch_kr_forum(publication_date: str) -> str:
    """Collect seven days of PyTorchKR 읽을거리&정보공유 forum topics.

    Returns a JSON envelope with publication_date, date_range, posts, and
    optional errors. Each post preserves two forum paragraphs and its primary
    external source URL.
    """
```

Use `httpx.Client(timeout=30.0, follow_redirects=True)`, call the internal helper, and serialize with `ensure_ascii=False, indent=2`. Invalid dates and top-level HTTP/JSON failures must return a valid JSON envelope containing an `errors` list.

**Step 5: Run focused tests to verify pass**

Run:

```bash
uv run pytest tests/test_pytorch_kr_forum.py -q
```

Expected: all new adapter tests pass.

**Step 6: Run the live source check (optional integration test)**

After adding the integration test in Task 4, run:

```bash
uv run pytest tests/test_pytorch_kr_forum.py -m integration -q
```

Expected: the live forum test passes for the current date window, or produces a clear external-network failure without affecting ordinary test runs.

**Step 7: Commit adapter implementation**

```bash
git add src/tools/search_tools.py tests/test_pytorch_kr_forum.py
git commit -m "feat: collect recent PyTorch-KR forum posts"
```

---

## Task 3: Route forum records through the deterministic collector

**Objective:** Integrate the source with existing candidate normalization and bounded enrichment without giving it a quota or refetching its forum pages.

**Files:**
- Modify: `src/tools/research_collector.py:15-18, 35-48, 69-112, 123-188, 261-286`
- Modify: `tests/test_research_collector.py:5-37, 66-168, 250-293, 381-458`

**Step 1: Write failing collector tests**

First update the test import list and `EXPECTED_CATEGORIES` to include `"pytorch_kr_community"`. Add a fake forum adapter envelope:

```python
def fake_search_pytorch_kr_forum(publication_date):
    return json.dumps({
        "publication_date": publication_date,
        "date_range": {"start": "2026-06-10", "end": "2026-06-17"},
        "posts": [{
            "title": "Forum Item",
            "forum_url": "https://discuss.pytorch.kr/t/forum-item/1",
            "original_url": "https://github.com/example/project",
            "content": "첫 문단\n\n둘째 문단",
            "published_at": "2026-06-12",
            "tags": ["llm", "agent"],
        }],
    })
```

Use it in all `_run_searches` and `_collect_weekly_research_core` tests so the expanded plan never calls the live forum.

Add assertions that the `pytorch_kr` raw result is labeled `pytorch_kr_community` and that normalization creates:

```python
{
    "url": "https://discuss.pytorch.kr/t/forum-item/1",
    "original_url": "https://github.com/example/project",
    "source": "discuss.pytorch.kr",
    "published_at": "2026-06-12",
    "summary": "첫 문단\n\n둘째 문단",
    "prefetched_content": "첫 문단\n\n둘째 문단",
    "category": "pytorch_kr_community",
    "topic_type": "main",
    "fetched": False,
    "score": 0.0,
}
```

Write a failing `_fetch_top_candidates` test proving a prefetched forum candidate:

- consumes one slot in the existing `max_fetches` slice,
- adds `prefetched_content[:max_chars_per_source]` under the candidate's forum `url`,
- sets `fetched=True`, and
- never calls `fetch_article_content` for that candidate.

**Step 2: Run collector tests to verify failure**

Run:

```bash
uv run pytest tests/test_research_collector.py -q
```

Expected: failures for the missing category/tool branch and prefetched-content behavior.

**Step 3: Add query-plan and search dispatch support**

Import `search_pytorch_kr_forum` alongside the existing search functions. Add this entry to `RESEARCH_QUERY_PLAN`:

```python
{"category": "pytorch_kr_community", "tool": "pytorch_kr", "query": None},
```

In `_run_searches`, add a `pytorch_kr` branch that parses the public adapter's envelope, appends source errors with a `pytorch_kr_community/pytorch_kr:` prefix, and assigns `items = result.get("posts", [])`. Keep failures isolated, exactly like the existing blog source handling.

**Step 4: Add candidate normalization support**

In `_normalize_candidates`, add a `pytorch_kr` branch before the final missing-title/URL guard:

```python
elif tool == "pytorch_kr":
    url = item.get("forum_url", "")
    title = item.get("title", "")
    published_at = item.get("published_at")
    score = 0.0
    summary = item.get("content", "")
    source = "discuss.pytorch.kr"
    original_url = item.get("original_url", url)
    prefetched_content = summary
```

Extend the candidate construction only for this branch to include `original_url` and `prefetched_content`. Do not alter the fields or scores of Tavily, HN, and official-blog candidates.

**Step 5: Reuse prefetched excerpts inside the shared enrichment budget**

Adjust `_fetch_top_candidates` so its existing `candidates[:max_fetches]` loop checks `candidate.get("prefetched_content")` before calling `fetch_article_content`:

```python
prefetched_content = candidate.get("prefetched_content")
if prefetched_content:
    fetched_content[candidate["url"]] = prefetched_content[:max_chars_per_source]
    candidate["fetched"] = True
    continue
```

This preserves the existing shared `max_fetches` cap. Do not pre-enrich every scraped forum post and do not make extra generic fetches of selected forum pages.

**Step 6: Run the collector suite to verify pass**

Run:

```bash
uv run pytest tests/test_research_collector.py -q
```

Expected: all collector tests pass, including the new forum category and prefetched-content test.

**Step 7: Commit collector integration**

```bash
git add src/tools/research_collector.py tests/test_research_collector.py
git commit -m "feat: integrate PyTorch-KR candidates into research"
```

---

## Task 4: Expose the primary source to the research agent and add a live regression check

**Objective:** Ensure the research report makes both the forum context and original-source citation available to downstream article writing.

**Files:**
- Modify: `src/config.py:69-102`
- Modify: `tests/test_prompts.py`
- Modify: `tests/test_pytorch_kr_forum.py`

**Step 1: Write a failing prompt-contract test**

Add a focused test in `tests/test_prompts.py` that asserts `RESEARCH_AGENT_PROMPT` instructs the agent to:

- recognize optional `original_url` on candidates;
- list the forum URL as the community source;
- list the primary/original URL separately whenever it differs from the forum URL.

Keep the test textual and narrow; do not construct an LLM or call external APIs.

**Step 2: Run the prompt test to verify failure**

Run:

```bash
uv run pytest tests/test_prompts.py -q
```

Expected: the new assertion fails because the existing prompt only documents `url`.

**Step 3: Update the report contract in `RESEARCH_AGENT_PROMPT`**

Revise the candidate-field text and final-report format so the report contains, for each PyTorchKR candidate:

```text
3. 포럼 출처 URL: <forum_url>
4. 원문/주요 출처 URL: <original_url>   # only when different
5. 발표/게시 날짜: <published_at>
```

Renumber the subsequent fields consistently. State that article writers should use `original_url` for fact verification when present, while retaining the forum URL as the Korean-community context. Do not modify unrelated orchestrator, topic-selector, or article-writer style requirements.

**Step 4: Add a marked live integration test**

Add an `@pytest.mark.integration` test in `tests/test_pytorch_kr_forum.py` that uses the current date window:

```python
from datetime import datetime, timedelta


@pytest.mark.integration
def test_live_pytorch_kr_forum_returns_structured_posts():
    publication_date = datetime.now().strftime("%Y-%m-%d")
    earliest_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    payload = json.loads(search_pytorch_kr_forum(publication_date))
    assert payload["publication_date"] == publication_date
    assert payload["posts"]
    post = payload["posts"][0]
    assert post["title"]
    assert post["forum_url"].startswith("https://discuss.pytorch.kr/t/")
    assert earliest_date <= post["published_at"] <= publication_date
    assert post["content"]
    assert post["original_url"].startswith("http")
```

The current date is deliberate: the source adapter itself is date-relative, and the marked live test should continue to exercise the currently available category pages. It remains excluded from the default suite.

**Step 5: Run target verification**

Run:

```bash
uv run pytest tests/test_pytorch_kr_forum.py tests/test_research_collector.py tests/test_prompts.py -q
uv run pytest -m integration tests/test_pytorch_kr_forum.py -q
```

Expected: all offline target tests pass; the marked live test passes when the forum is reachable.

**Step 6: Record the known full-suite baseline separately**

Run:

```bash
uv run pytest -m 'not integration'
```

Expected: feature-target tests remain green; the known `tests/test_email_flow.py` errors may persist unchanged. Report these separately and do not claim full-suite green unless that unrelated baseline is corrected in another scope.

**Step 7: Commit prompt/report integration**

```bash
git add src/config.py tests/test_prompts.py tests/test_pytorch_kr_forum.py
git commit -m "feat: surface PyTorch-KR primary sources in research"
```

---

## Task 5: Final feature verification and Kanban handoff

**Objective:** Verify the branch contains the design, plan, and implementation with only intended changes, then make the existing Kanban card executable.

**Files:**
- Verify: `docs/superpowers/specs/2026-07-15-pytorch-kr-forum-research-design.md`
- Verify: `docs/plans/2026-07-15-pytorch-kr-forum-research.md`
- Verify: `src/tools/search_tools.py`
- Verify: `src/tools/research_collector.py`
- Verify: `src/config.py`
- Verify: `tests/test_pytorch_kr_forum.py`
- Verify: `tests/test_research_collector.py`
- Verify: `tests/test_prompts.py`

**Step 1: Inspect the feature diff**

Run:

```bash
git diff --check personal...HEAD
git diff --stat personal...HEAD
git status --short
```

Expected: no whitespace errors and only the planned implementation, test, design, and plan files changed.

**Step 2: Run the final target suites**

Run:

```bash
uv run pytest tests/test_pytorch_kr_forum.py tests/test_research_collector.py tests/test_prompts.py -q
```

Expected: all selected tests pass.

**Step 3: Run the live source check**

Run:

```bash
uv run pytest -m integration tests/test_pytorch_kr_forum.py -q
```

Expected: the public endpoint works and returns structured data. If external availability blocks it, capture the exact error but do not treat it as an offline-unit-test regression.

**Step 4: Unblock and update the Kanban card only after plan approval**

Run:

```bash
hermes kanban --board newsletter-automation-gpters unblock t_ac24560b
hermes kanban --board newsletter-automation-gpters comment t_ac24560b \
  'Implementation plan approved and committed on feature/pytorch-kr-forum-research; execution may begin.'
```

Expected: `t_ac24560b` becomes ready with the implementation-plan status recorded.

**Step 5: Commit the implementation plan (this planning phase)**

```bash
git add docs/plans/2026-07-15-pytorch-kr-forum-research.md
git commit -m "docs: add PyTorch-KR forum implementation plan"
```
