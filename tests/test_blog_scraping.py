"""Tests for fetch_official_blog_posts and its internal helpers."""

import json
from datetime import datetime
from unittest.mock import MagicMock

import httpx
import pytest

from src.tools.content_tools import (
    _fetch_anthropic_posts,
    _fetch_rss_posts,
    _parse_html_date,
    _parse_rss_date,
    fetch_official_blog_posts,
)


# ---------------------------------------------------------------------------
# Unit tests: date parsers
# ---------------------------------------------------------------------------


class TestParseRssDate:
    def test_standard_rfc2822(self):
        dt = _parse_rss_date("Wed, 11 Feb 2026 09:00:00 GMT")
        assert dt == datetime(2026, 2, 11, 9, 0, 0)

    def test_with_timezone_offset(self):
        dt = _parse_rss_date("Mon, 09 Feb 2026 16:12:06 +0000")
        assert dt == datetime(2026, 2, 9, 16, 12, 6)

    def test_strips_timezone_info(self):
        dt = _parse_rss_date("Thu, 05 Feb 2026 11:00:00 GMT")
        assert dt is not None
        assert dt.tzinfo is None

    def test_empty_string(self):
        assert _parse_rss_date("") is None

    def test_garbage(self):
        assert _parse_rss_date("not a date") is None


class TestParseHtmlDate:
    def test_short_month(self):
        dt = _parse_html_date("Feb 5, 2026")
        assert dt == datetime(2026, 2, 5)

    def test_full_month(self):
        dt = _parse_html_date("February 5, 2026")
        assert dt == datetime(2026, 2, 5)

    def test_iso_datetime(self):
        dt = _parse_html_date("2026-02-11T09:00")
        assert dt == datetime(2026, 2, 11, 9, 0)

    def test_iso_date(self):
        dt = _parse_html_date("2026-02-11")
        assert dt == datetime(2026, 2, 11)

    def test_whitespace(self):
        dt = _parse_html_date("  Feb 5, 2026  ")
        assert dt == datetime(2026, 2, 5)

    def test_empty(self):
        assert _parse_html_date("") is None

    def test_month_year_only_returns_none(self):
        # _parse_html_date does not handle month+year format
        assert _parse_html_date("February 2026") is None


# ---------------------------------------------------------------------------
# Unit tests: RSS parser with mock HTTP
# ---------------------------------------------------------------------------

SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Test Feed</title>
  <item>
    <title>Article In Range</title>
    <link>https://example.com/in-range</link>
    <pubDate>Tue, 10 Feb 2026 12:00:00 GMT</pubDate>
    <category>Research</category>
    <description>This is in range</description>
  </item>
  <item>
    <title>Article Before Range</title>
    <link>https://example.com/before-range</link>
    <pubDate>Sun, 01 Feb 2026 12:00:00 GMT</pubDate>
    <category>Product</category>
    <description>This is before range</description>
  </item>
  <item>
    <title>Article After Range</title>
    <link>https://example.com/after-range</link>
    <pubDate>Mon, 16 Feb 2026 12:00:00 GMT</pubDate>
    <category>News</category>
    <description>This is after range</description>
  </item>
  <item>
    <title>Article On Start Boundary</title>
    <link>/relative-path</link>
    <pubDate>Thu, 05 Feb 2026 00:00:00 GMT</pubDate>
    <category>Engineering</category>
    <description>Boundary start</description>
  </item>
  <item>
    <title>Article On End Boundary</title>
    <link>https://example.com/end-boundary</link>
    <pubDate>Thu, 12 Feb 2026 23:59:00 GMT</pubDate>
    <category>Safety</category>
    <description>Boundary end</description>
  </item>
</channel>
</rss>
"""


def _make_mock_client(response_text: str, status_code: int = 200) -> httpx.Client:
    """Create a mock httpx.Client that returns the given response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.text = response_text
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()

    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_response
    return client


class TestFetchRssPosts:
    def test_filters_by_date_range(self):
        client = _make_mock_client(SAMPLE_RSS)
        # RSS dates have time components (e.g. 12:00:00), so end must
        # cover the full day to include articles published during the day
        start = datetime(2026, 2, 5)
        end = datetime(2026, 2, 12, 23, 59, 59)

        posts = _fetch_rss_posts(
            client, "https://example.com/rss.xml", "test", "https://example.com", start, end
        )

        titles = [p["title"] for p in posts]
        assert "Article In Range" in titles
        assert "Article On Start Boundary" in titles
        assert "Article On End Boundary" in titles
        assert "Article Before Range" not in titles
        assert "Article After Range" not in titles

    def test_post_fields(self):
        client = _make_mock_client(SAMPLE_RSS)
        start = datetime(2026, 2, 10)
        end = datetime(2026, 2, 10, 23, 59, 59)

        posts = _fetch_rss_posts(
            client, "https://example.com/rss.xml", "mysource", "https://example.com", start, end
        )

        assert len(posts) == 1
        post = posts[0]
        assert post["source"] == "mysource"
        assert post["title"] == "Article In Range"
        assert post["url"] == "https://example.com/in-range"
        assert post["date"] == "2026-02-10"
        assert post["category"] == "Research"
        assert post["description"] == "This is in range"

    def test_relative_link_gets_base_url(self):
        client = _make_mock_client(SAMPLE_RSS)
        start = datetime(2026, 2, 5)
        end = datetime(2026, 2, 5)

        posts = _fetch_rss_posts(
            client, "https://example.com/rss.xml", "test", "https://example.com", start, end
        )

        assert len(posts) == 1
        assert posts[0]["url"] == "https://example.com/relative-path"

    def test_empty_feed(self):
        empty_rss = '<?xml version="1.0"?><rss><channel></channel></rss>'
        client = _make_mock_client(empty_rss)
        start = datetime(2026, 2, 5)
        end = datetime(2026, 2, 12)

        posts = _fetch_rss_posts(
            client, "https://example.com/rss.xml", "test", "https://example.com", start, end
        )
        assert posts == []


# ---------------------------------------------------------------------------
# Unit tests: Anthropic HTML parser with mock HTTP
# ---------------------------------------------------------------------------

SAMPLE_ANTHROPIC_HTML = """\
<html><body>
<article>
  <a href="/news/post-in-range">
    <time>Feb 10, 2026</time>
    <span>Announcements</span>
    <h2>Anthropic Post In Range</h2>
    <p>Description of in-range post</p>
  </a>
  <a href="/news/post-before-range">
    <time>Jan 30, 2026</time>
    <span>Research</span>
    <h4>Post Before Range</h4>
    <p>Too old</p>
  </a>
  <a href="/news/post-in-range">
    <time>Feb 10, 2026</time>
    <span>Announcements</span>
    <span>Anthropic Post In Range</span>
  </a>
  <a href="/news/another-post">
    <time>Feb 8, 2026</time>
    <span>Product</span>
    <span>Another Post Title</span>
  </a>
  <a href="/about">
    <span>Not a news link</span>
  </a>
</article>
</body></html>
"""


class TestFetchAnthropicPosts:
    def test_filters_and_deduplicates(self):
        client = _make_mock_client(SAMPLE_ANTHROPIC_HTML)
        start = datetime(2026, 2, 5)
        end = datetime(2026, 2, 12)

        posts = _fetch_anthropic_posts(client, start, end)

        titles = [p["title"] for p in posts]
        assert "Anthropic Post In Range" in titles
        assert "Another Post Title" in titles
        assert "Post Before Range" not in titles
        # Deduplication: only 2 unique posts, not 3
        assert len(posts) == 2

    def test_post_fields_with_h2(self):
        client = _make_mock_client(SAMPLE_ANTHROPIC_HTML)
        start = datetime(2026, 2, 10)
        end = datetime(2026, 2, 10)

        posts = _fetch_anthropic_posts(client, start, end)

        assert len(posts) == 1
        post = posts[0]
        assert post["source"] == "anthropic"
        assert post["title"] == "Anthropic Post In Range"
        assert post["url"] == "https://www.anthropic.com/news/post-in-range"
        assert post["date"] == "2026-02-10"
        assert post["category"] == "Announcements"
        assert post["description"] == "Description of in-range post"

    def test_title_fallback_to_span(self):
        client = _make_mock_client(SAMPLE_ANTHROPIC_HTML)
        start = datetime(2026, 2, 8)
        end = datetime(2026, 2, 8)

        posts = _fetch_anthropic_posts(client, start, end)

        assert len(posts) == 1
        assert posts[0]["title"] == "Another Post Title"

    def test_ignores_non_news_links(self):
        client = _make_mock_client(SAMPLE_ANTHROPIC_HTML)
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)

        posts = _fetch_anthropic_posts(client, start, end)

        urls = [p["url"] for p in posts]
        assert all("/news/" in u for u in urls)

    def test_no_article_tag(self):
        client = _make_mock_client("<html><body><div>No article</div></body></html>")
        posts = _fetch_anthropic_posts(client, datetime(2026, 1, 1), datetime(2026, 12, 31))
        assert posts == []


# ---------------------------------------------------------------------------
# Unit tests: GitHub trending scrape
# ---------------------------------------------------------------------------

SAMPLE_TRENDING_HTML = """\
<html><body>
<article class="Box-row">
  <h2><a href="/microsoft/AI-For-Beginners">microsoft / AI-For-Beginners</a></h2>
  <p>12 Weeks, 24 Lessons, AI for All!</p>
  <span class="d-inline-block float-sm-right">7,554 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/some-org/unrelated-project">some-org / unrelated-project</a></h2>
  <p>A CLI for managing dotfiles</p>
  <span class="d-inline-block float-sm-right">500 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/block/buzz">block / buzz</a></h2>
  <p>A hive mind communication platform for agents</p>
  <span class="d-inline-block float-sm-right">7,372 stars this week</span>
</article>
</body></html>
"""


class TestFetchGithubTrendingPosts:
    def test_filters_by_ai_keyword(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client(SAMPLE_TRENDING_HTML)
        posts = _fetch_github_trending_posts(client)

        names = [p["full_name"] for p in posts]
        assert "microsoft/AI-For-Beginners" in names
        assert "block/buzz" in names
        assert "some-org/unrelated-project" not in names

    def test_post_fields(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client(SAMPLE_TRENDING_HTML)
        posts = _fetch_github_trending_posts(client)

        post = next(p for p in posts if p["full_name"] == "microsoft/AI-For-Beginners")
        assert post["url"] == "https://github.com/microsoft/AI-For-Beginners"
        assert post["description"] == "12 Weeks, 24 Lessons, AI for All!"
        assert post["stars_this_week"] == "7,554 stars this week"

    def test_no_matching_articles(self):
        from src.tools.content_tools import _fetch_github_trending_posts

        client = _make_mock_client("<html><body>no repos here</body></html>")
        assert _fetch_github_trending_posts(client) == []


class TestFetchGithubTrending:
    def test_output_structure(self, monkeypatch):
        from src.tools.content_tools import fetch_github_trending

        monkeypatch.setattr(
            "src.tools.content_tools._fetch_github_trending_posts",
            lambda client: [{"full_name": "a/b", "url": "https://github.com/a/b",
                              "description": "d", "stars_this_week": "1 stars this week"}],
        )
        result = json.loads(fetch_github_trending("2026-08-05"))
        assert result["publication_date"] == "2026-08-05"
        assert len(result["posts"]) == 1
        assert "errors" not in result

    def test_errors_captured_not_raised(self, monkeypatch):
        from src.tools.content_tools import fetch_github_trending

        def fail(client):
            raise ConnectionError("network down")

        monkeypatch.setattr("src.tools.content_tools._fetch_github_trending_posts", fail)

        result = json.loads(fetch_github_trending("2026-08-05"))
        assert result["posts"] == []
        assert "network down" in result["errors"][0]


# ---------------------------------------------------------------------------
# Unit tests: fetch_official_blog_posts output structure
# ---------------------------------------------------------------------------


class TestFetchOfficialBlogPostsStructure:
    def test_output_json_structure(self, monkeypatch):
        """Test the output JSON has the expected top-level keys."""
        # Mock all three fetchers to return known data
        monkeypatch.setattr(
            "src.tools.content_tools._fetch_rss_posts",
            lambda client, url, source, base, start, end: [
                {"source": source, "title": f"{source} post", "url": "https://example.com",
                 "date": "2026-02-10", "category": "Test", "description": "desc"}
            ],
        )
        monkeypatch.setattr(
            "src.tools.content_tools._fetch_anthropic_posts",
            lambda client, start, end: [
                {"source": "anthropic", "title": "anthropic post", "url": "https://anthropic.com",
                 "date": "2026-02-10", "category": "Test", "description": "desc"}
            ],
        )

        result = json.loads(fetch_official_blog_posts("2026-02-12"))

        assert result["publication_date"] == "2026-02-12"
        assert result["date_range"]["start"] == "2026-02-05"
        assert result["date_range"]["end"] == "2026-02-12"
        assert "openai" in result["posts"]
        assert "anthropic" in result["posts"]
        assert "deepmind" in result["posts"]
        # 2 RSS calls (openai + deepmind) + 1 anthropic = 3 sources
        assert result["total_count"] == 3
        assert "errors" not in result

    def test_errors_captured_not_raised(self, monkeypatch):
        """Test that individual source failures are captured, not propagated."""
        def fail(*args, **kwargs):
            raise ConnectionError("network down")

        monkeypatch.setattr("src.tools.content_tools._fetch_rss_posts", fail)
        monkeypatch.setattr("src.tools.content_tools._fetch_anthropic_posts", fail)

        result = json.loads(fetch_official_blog_posts("2026-02-12"))

        assert result["total_count"] == 0
        assert len(result["errors"]) == 3
        assert all("network down" in e for e in result["errors"])

    def test_date_range_is_7_days(self, monkeypatch):
        monkeypatch.setattr(
            "src.tools.content_tools._fetch_rss_posts", lambda *a, **kw: []
        )
        monkeypatch.setattr(
            "src.tools.content_tools._fetch_anthropic_posts", lambda *a, **kw: []
        )

        result = json.loads(fetch_official_blog_posts("2026-03-01"))

        assert result["date_range"]["start"] == "2026-02-22"
        # end includes the full publication day (23:59:59)
        assert result["date_range"]["end"] == "2026-03-01"


# ---------------------------------------------------------------------------
# Integration tests: hit real endpoints (skipped in CI)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegration:
    """Tests that hit real APIs. Run with: pytest -m integration"""

    def test_openai_rss_returns_posts(self):
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            posts = _fetch_rss_posts(
                client,
                "https://openai.com/news/rss.xml",
                "openai",
                "https://openai.com",
                datetime(2026, 2, 1),
                datetime(2026, 2, 28),
            )
        assert len(posts) > 0
        post = posts[0]
        assert post["source"] == "openai"
        assert post["title"]
        assert post["url"].startswith("https://")
        assert post["date"].startswith("2026-02")

    def test_anthropic_html_returns_posts(self):
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            posts = _fetch_anthropic_posts(
                client, datetime(2026, 1, 1), datetime(2026, 2, 28)
            )
        assert len(posts) > 0
        post = posts[0]
        assert post["source"] == "anthropic"
        assert post["title"]
        assert "anthropic.com" in post["url"]

    def test_deepmind_rss_returns_posts(self):
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            posts = _fetch_rss_posts(
                client,
                "https://deepmind.google/blog/rss.xml",
                "deepmind",
                "https://deepmind.google",
                datetime(2026, 1, 1),
                datetime(2026, 2, 28),
            )
        assert len(posts) > 0
        post = posts[0]
        assert post["source"] == "deepmind"
        assert post["title"]

    def test_full_function_returns_all_sources(self):
        result = json.loads(fetch_official_blog_posts("2026-02-12"))
        with open("result.json", "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        assert "errors" not in result, f"Errors: {result.get('errors')}"
        assert result["total_count"] > 0
        # At least one source should have posts
        non_empty = [s for s, posts in result["posts"].items() if posts]
        assert len(non_empty) >= 1, "Expected at least one source with posts"
