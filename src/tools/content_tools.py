"""Content extraction and analysis tools."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def fetch_article_content(url: str) -> str:
    """Fetch and extract the main content from a URL.

    Args:
        url: The URL of the article to fetch

    Returns:
        JSON string containing the extracted title, content, and metadata
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)

        # Extract main content
        # Try common article containers
        content = ""
        article_selectors = [
            "article",
            '[role="main"]',
            ".post-content",
            ".article-content",
            ".entry-content",
            "main",
            ".content",
        ]

        for selector in article_selectors:
            article = soup.select_one(selector)
            if article:
                content = article.get_text(separator="\n", strip=True)
                break

        if not content:
            # Fallback to body content
            body = soup.find("body")
            if body:
                content = body.get_text(separator="\n", strip=True)

        # Clean up content
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        content = "\n".join(lines)

        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "...[truncated]"

        # Extract metadata
        domain = urlparse(url).netloc
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content", "")

        return json.dumps(
            {
                "url": url,
                "domain": domain,
                "title": title,
                "description": description,
                "content": content,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_rss_date(text: str) -> datetime | None:
    """Parse RFC 2822 date from RSS feeds (e.g. 'Wed, 11 Feb 2026 09:00:00 GMT')."""
    try:
        return parsedate_to_datetime(text).replace(tzinfo=None)
    except Exception:
        return None


def _parse_html_date(text: str) -> datetime | None:
    """Parse date strings found in HTML (e.g. 'Feb 5, 2026')."""
    text = text.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _fetch_rss_posts(
    client: httpx.Client,
    rss_url: str,
    source: str,
    base_url: str,
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Fetch posts from an RSS feed filtered by date range.

    Works for both OpenAI (/news/rss.xml) and DeepMind (/blog/rss.xml).
    """
    resp = client.get(rss_url, headers=_HEADERS)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    posts = []

    for item in root.findall(".//item"):
        pub_date_text = item.findtext("pubDate", "")
        dt = _parse_rss_date(pub_date_text)
        if not dt or not (start <= dt <= end):
            continue

        link = item.findtext("link", "")
        if not link.startswith("http"):
            link = base_url + link

        posts.append({
            "source": source,
            "title": item.findtext("title", ""),
            "url": link,
            "date": dt.strftime("%Y-%m-%d"),
            "category": item.findtext("category", ""),
            "description": item.findtext("description", ""),
        })

    return posts


def _fetch_anthropic_posts(
    client: httpx.Client, start: datetime, end: datetime
) -> list[dict]:
    """Scrape Anthropic news page for posts in the date range.

    Anthropic has no RSS feed. The /news page contains an <article> with
    <a href="/news/..."> links, each with <time>Feb 5, 2026</time>, titles
    in h2/h4/span, and categories in span elements.
    """
    resp = client.get("https://www.anthropic.com/news", headers=_HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    seen_urls: set[str] = set()
    posts = []
    article = soup.find("article")
    if not article:
        return posts

    for link in article.find_all("a", href=True):
        href = link["href"]
        if not href.startswith("/news/") and href != "/mars":
            continue
        if href in seen_urls:
            continue

        time_el = link.find("time")
        if not time_el:
            continue
        dt = _parse_html_date(time_el.get_text(strip=True))
        if not dt or not (start <= dt <= end):
            continue

        seen_urls.add(href)

        # Title from h2, h4, or last span
        title_el = link.find("h2") or link.find("h4")
        spans = link.find_all("span")
        if title_el:
            title = title_el.get_text(strip=True)
        elif spans:
            title = spans[-1].get_text(strip=True)
        else:
            title = ""

        # Category from first span that isn't the title
        category = ""
        for s in spans:
            txt = s.get_text(strip=True)
            if txt != title and not s.find("time"):
                category = txt
                break

        description = ""
        p_el = link.find("p")
        if p_el:
            description = p_el.get_text(strip=True)

        posts.append({
            "source": "anthropic",
            "title": title,
            "url": "https://www.anthropic.com" + href,
            "date": dt.strftime("%Y-%m-%d"),
            "category": category,
            "description": description,
        })

    return posts


def fetch_official_blog_posts(publication_date: str) -> str:
    """Fetch recent blog posts from OpenAI, Anthropic, and Google DeepMind.

    Uses RSS feeds for OpenAI and DeepMind, and HTML scraping for Anthropic
    (which has no RSS feed). Returns posts published between 7 days before
    the publication date and the publication date itself.

    Args:
        publication_date: Newsletter publication date in YYYY-MM-DD format
            (e.g. "2026-02-12")

    Returns:
        JSON string containing blog posts grouped by source, with title, URL,
        date, and category for each post.
    """
    pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
    start = pub_date - timedelta(days=7)
    end = pub_date.replace(hour=23, minute=59, second=59)

    all_posts: dict[str, list[dict]] = {
        "openai": [],
        "anthropic": [],
        "deepmind": [],
    }
    errors: list[str] = []

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # OpenAI - RSS feed
        try:
            all_posts["openai"] = _fetch_rss_posts(
                client,
                "https://openai.com/news/rss.xml",
                "openai",
                "https://openai.com",
                start,
                end,
            )
        except Exception as e:
            errors.append(f"openai: {e}")

        # Anthropic - HTML scraping (no RSS available)
        try:
            all_posts["anthropic"] = _fetch_anthropic_posts(client, start, end)
        except Exception as e:
            errors.append(f"anthropic: {e}")

        # DeepMind - RSS feed
        try:
            all_posts["deepmind"] = _fetch_rss_posts(
                client,
                "https://deepmind.google/blog/rss.xml",
                "deepmind",
                "https://deepmind.google",
                start,
                end,
            )
        except Exception as e:
            errors.append(f"deepmind: {e}")

    result = {
        "publication_date": publication_date,
        "date_range": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        },
        "posts": all_posts,
        "total_count": sum(len(v) for v in all_posts.values()),
    }
    if errors:
        result["errors"] = errors

    return json.dumps(result, ensure_ascii=False, indent=2)

