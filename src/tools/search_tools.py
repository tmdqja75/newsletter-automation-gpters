"""Search tools for gathering AI/LLM news and information."""

import os
import json
import httpx
from datetime import datetime, timedelta
from tavily import TavilyClient

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
    two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            start_date= article_date or two_weeks_ago,  # Filter for content from last 2 weeks
            # include_domains=[
            #     "arxiv.org",
            #     "techcrunch.com",
            #     "theverge.com",
            #     "venturebeat.com",
            #     "wired.com",
            #     "arstechnica.com",
            # ],
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
