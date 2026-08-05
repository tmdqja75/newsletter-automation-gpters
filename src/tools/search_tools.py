"""Search tools for gathering AI/LLM news and information."""

import json
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from tavily import TavilyClient


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
_PYTORCH_KR_BLOCKED_HOSTS = {
    "pytorch.kr",
    "t.me",
    "telegram.me",
    "telegram.org",
    "discuss-noti.pytorch.kr",
    "www.discourse.org",
}
_PYTORCH_KR_SIGNUP_PATHS = {
    "/signup",
    "/register",
    "/login",
    "/auth",
}
_PYTORCH_KR_MEDIA_EXTENSIONS = {
    ".avif", ".gif", ".jpeg", ".jpg", ".mov", ".mp3", ".mp4",
    ".pdf", ".png", ".svg", ".webm", ".webp",
}
_PYTORCH_KR_BOILERPLATE_PARAGRAPHS = {
    "powered by discourse",
    "pytorch korea users group",
}


def search_ai_news(query: str, max_results: int = 10, article_date: str | None = None) -> str:
    """Search for AI/LLM related news using Tavily API.

    Args:
        query: Search query for AI news (e.g., "new LLM model release 2026")
        max_results: Maximum number of results to return (default: 10)
        article_date: Newsletter publication date in YYYY-MM-DD format.

    Returns:
        JSON string containing search results with titles, URLs, and snippets
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})

    client = TavilyClient(api_key=api_key)

    # Calculate date from 2 weeks ago for filtering recent content
    if article_date:
        try:
            article_datetime = datetime.strptime(article_date, "%Y-%m-%d")
            two_weeks_ago = (article_datetime - timedelta(days=14)).strftime("%Y-%m-%d")
        except ValueError:
            return json.dumps({"error": "Invalid article_date format. Use YYYY-MM-DD."})
    else:
        two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=max_results,
            start_date=two_weeks_ago,  # Filter for content from last 2 weeks
            include_domains=[
                "anthropic.com",
                "openai.com",
                "ai.google",
                "blog.google",
                "huggingface.co",
                "arxiv.org",
                "techcrunch.com",
                "theverge.com",
                "venturebeat.com",
                "wired.com",
                "arstechnica.com",
            ],
            exclude_domains=[
                "openai.com",
                "anthropic.com",
                "deepmind.google",
            ],
        )

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


def search_hackernews(query: str, num_results: int = 10, publication_date: str | None = None) -> str:
    """Search Hacker News for AI-related posts and discussions.

    Args:
        query: Search query (e.g., "AI agent", "LLM framework")
        num_results: Number of results to return (default: 10)
        publication_date: Newsletter publication date in YYYY-MM-DD format.
            When provided, results are filtered to the 7 days before this date.
            Defaults to 7 days before today.

    Returns:
        JSON string containing HN posts with titles, URLs, points, and comments
    """
    try:
        if publication_date:
            pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
        else:
            pub_date = datetime.now()
        start = pub_date - timedelta(days=7)
        start_timestamp = int(start.timestamp())

        # Use HN Algolia API
        search_url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": num_results,
            "numericFilters": f"created_at_i>{start_timestamp}",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(search_url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for hit in data.get("hits", []):
            story_id = hit.get("objectID", "")
            results.append({
                "title": hit.get("title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                "points": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "created_at": hit.get("created_at", ""),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def search_github_repos(query: str, publication_date: str, max_results: int = 6) -> str:
    """Search GitHub repositories via the public Search API for repos created recently.

    Args:
        query: GitHub search qualifiers/keywords (e.g. "topic:ai-agents")
        publication_date: Newsletter publication date in YYYY-MM-DD format.
            Results are restricted to repos created in the 14 days before this date.
        max_results: Maximum number of results to return (default: 6)

    Returns:
        JSON string containing repo full_name, url, description, stars, created_at
    """
    try:
        pub_date = datetime.strptime(publication_date, "%Y-%m-%d")
    except ValueError:
        return json.dumps({"error": "Invalid publication_date format. Use YYYY-MM-DD."})

    window_start = (pub_date - timedelta(days=14)).strftime("%Y-%m-%d")
    full_query = f"{query} created:>{window_start}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                GITHUB_SEARCH_URL,
                params={
                    "q": full_query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": max_results,
                },
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "full_name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "description": item.get("description") or "",
                "stars": item.get("stargazers_count", 0),
                "created_at": item.get("created_at", ""),
            })

        return json.dumps(results, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


def _parse_pytorch_kr_created_at(value: object) -> datetime | None:
    """Parse the UTC timestamps emitted by Discourse topic listings."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (AttributeError, TypeError, ValueError):
        return None


def _is_pytorch_kr_primary_source(url: object) -> bool:
    """Return whether a post link is an external, non-media primary source."""
    if not isinstance(url, str) or not url.strip() or url.lstrip().startswith("#"):
        return False

    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return False
    if host == "discuss.pytorch.kr" or host.endswith(".pytorch.kr"):
        return False
    if host in _PYTORCH_KR_BLOCKED_HOSTS or host.endswith((".t.me", ".telegram.me", ".telegram.org")):
        return False
    if host == "discourse.org" or host.endswith(".discourse.org"):
        return False
    if any(segment in path for segment in ("/upload/", "/uploads/", "/image/", "/images/", "/media/")):
        return False
    if any(path.startswith(sp) for sp in _PYTORCH_KR_SIGNUP_PATHS):
        return False
    return not path.endswith(tuple(_PYTORCH_KR_MEDIA_EXTENSIONS))


def _extract_pytorch_kr_post_fields(cooked: str, forum_url: str) -> tuple[str, str]:
    """Extract a short forum excerpt and the best external source link."""
    soup = BeautifulSoup(cooked or "", "html.parser")

    paragraphs: list[str] = []
    for paragraph in soup.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        if not text or text.casefold() in _PYTORCH_KR_BOILERPLATE_PARAGRAPHS:
            continue
        paragraphs.append(text)
        if len(paragraphs) == 2:
            break

    for onebox in soup.find_all(attrs={"data-onebox-src": True}):
        if onebox.find_parent("footer") is not None:
            continue
        if onebox.find_parent(class_="footer") is not None:
            continue
        source_url = onebox.get("data-onebox-src")
        if _is_pytorch_kr_primary_source(source_url):
            return "\n\n".join(paragraphs), source_url.strip()

    for anchor in soup.find_all("a", href=True):
        if anchor.find_parent("footer") is not None:
            continue
        if anchor.find_parent(class_="footer") is not None:
            continue
        source_url = anchor.get("href")
        if _is_pytorch_kr_primary_source(source_url):
            return "\n\n".join(paragraphs), source_url.strip()

    return "\n\n".join(paragraphs), forum_url


def _fetch_pytorch_kr_forum_posts(
    client: httpx.Client,
    publication_date: str,
    *,
    max_pages: int = PYTORCH_KR_MAX_PAGES,
    request_delay_seconds: float = PYTORCH_KR_REQUEST_DELAY_SECONDS,
) -> tuple[list[dict], list[str]]:
    """Collect recent non-pinned PyTorch-KR news topics through Discourse JSON."""
    try:
        end = datetime.strptime(publication_date, "%Y-%m-%d").replace(
            hour=23,
            minute=59,
            second=59,
        )
    except (TypeError, ValueError) as error:
        return [], [f"Invalid publication_date {publication_date!r}: {error}"]

    start = end.replace(hour=0, minute=0, second=0) - timedelta(days=7)
    listing_url = (
        f"{PYTORCH_KR_BASE_URL}/c/news/{PYTORCH_KR_NEWS_CATEGORY_ID}/l/latest.json"
    )
    seen_topic_ids: set[str] = set()
    eligible_topics: list[tuple[dict, datetime]] = []

    for page in range(max_pages):
        try:
            response = client.get(listing_url, params={"page": page})
            response.raise_for_status()
            listing = response.json()
            topic_list = listing.get("topic_list", {})
            topics = topic_list.get("topics", [])
            if not isinstance(topics, list):
                raise ValueError("listing topic_list.topics is not a list")
        except Exception as error:
            return [], [f"PyTorch-KR listing page {page} failed: {error}"]

        if not topics:
            break

        parseable_non_pinned_dates: list[datetime] = []
        for topic in topics:
            if not isinstance(topic, dict):
                continue

            created_at = _parse_pytorch_kr_created_at(topic.get("created_at"))
            if not topic.get("pinned") and created_at is not None:
                parseable_non_pinned_dates.append(created_at)

            topic_id = topic.get("id")
            if topic_id is None:
                continue
            topic_id_key = str(topic_id)
            if topic_id_key in seen_topic_ids:
                continue
            seen_topic_ids.add(topic_id_key)

            if topic.get("pinned") or created_at is None:
                continue
            if start <= created_at <= end:
                eligible_topics.append((topic, created_at))

        if (
            parseable_non_pinned_dates
            and all(created_at < start for created_at in parseable_non_pinned_dates)
        ):
            break
        if not topic_list.get("more_topics_url"):
            break

    posts: list[dict] = []
    errors: list[str] = []
    for index, (topic, created_at) in enumerate(eligible_topics):
        topic_id = topic["id"]
        slug = topic.get("slug", "")
        forum_url = f"{PYTORCH_KR_BASE_URL}/t/{slug}/{topic_id}"
        try:
            response = client.get(f"{PYTORCH_KR_BASE_URL}/t/{topic_id}.json")
            response.raise_for_status()
            detail = response.json()
            cooked = detail["post_stream"]["posts"][0]["cooked"]
            if not isinstance(cooked, str):
                raise ValueError("topic detail first post has no cooked HTML")
            content, original_url = _extract_pytorch_kr_post_fields(cooked, forum_url)
            tags = []
            for tag in topic.get("tags", []):
                if isinstance(tag, dict) and isinstance(tag.get("slug"), str):
                    tags.append(tag["slug"])
                elif isinstance(tag, str):
                    tags.append(tag)
            posts.append(
                {
                    "title": topic.get("title", ""),
                    "forum_url": forum_url,
                    "original_url": original_url,
                    "content": content,
                    "published_at": created_at.strftime("%Y-%m-%d"),
                    "tags": tags,
                }
            )
        except Exception as error:
            errors.append(f"PyTorch-KR topic {topic_id} detail failed: {error}")

        if request_delay_seconds > 0 and index < len(eligible_topics) - 1:
            time.sleep(request_delay_seconds)

    return posts, errors


def search_pytorch_kr_forum(publication_date: str) -> str:
    """Collect the inclusive seven-day PyTorch-KR news window as JSON data."""
    try:
        end = datetime.strptime(publication_date, "%Y-%m-%d")
    except (TypeError, ValueError) as error:
        return json.dumps(
            {
                "publication_date": publication_date,
                "date_range": {"start": None, "end": None},
                "posts": [],
                "errors": [f"Invalid publication_date {publication_date!r}: {error}"],
            },
            ensure_ascii=False,
            indent=2,
        )

    start = end - timedelta(days=7)
    envelope = {
        "publication_date": publication_date,
        "date_range": {
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
        },
        "posts": [],
        "errors": [],
    }
    try:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=PYTORCH_KR_HEADERS,
        ) as client:
            envelope["posts"], envelope["errors"] = _fetch_pytorch_kr_forum_posts(
                client,
                publication_date,
            )
    except Exception as error:
        envelope["errors"] = [f"PyTorch-KR forum collection failed: {error}"]

    return json.dumps(envelope, ensure_ascii=False, indent=2)