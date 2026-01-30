"""Search tools for gathering AI/LLM news and information."""

import os
import json
import httpx
from typing import Optional
from tavily import TavilyClient


def generate_search_queries(
    topic: str,
    subtopics: Optional[list[str]] = None,
    goal: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> list[str]:
    """Generate personalized search queries based on user context.

    Args:
        topic: Main topic to research (e.g., "의료 AI", "게임 개발", "블록체인")
        subtopics: Specific areas of interest within the topic
        goal: User's purpose - "work", "learning", "business", or "hobby"
        difficulty: User's level - "beginner", "intermediate", or "advanced"

    Returns:
        List of search query strings optimized for the user's context

    Examples:
        >>> generate_search_queries("의료 AI", ["진단", "영상분석"], "learning", "beginner")
        ["의료 AI", "의료 AI 진단", "의료 AI 영상분석", "의료 AI introduction tutorial"]
    """
    queries = [topic]

    # Add subtopic combinations
    if subtopics:
        for subtopic in subtopics:
            queries.append(f"{topic} {subtopic}")

    # Adjust queries based on user goal
    if goal:
        goal_modifiers = {
            "work": ["implementation", "case study", "best practices"],
            "learning": ["tutorial", "introduction", "guide"],
            "business": ["market analysis", "trends", "industry report"],
            "hobby": ["getting started", "examples", "projects"],
        }
        modifiers = goal_modifiers.get(goal, [])
        if modifiers:
            # Add goal-specific query
            queries.append(f"{topic} {modifiers[0]}")

    # Adjust queries based on difficulty level
    if difficulty:
        difficulty_modifiers = {
            "beginner": "introduction",
            "intermediate": "advanced techniques",
            "advanced": "research papers",
        }
        modifier = difficulty_modifiers.get(difficulty)
        if modifier and difficulty != "intermediate":  # Skip intermediate to avoid redundancy
            queries.append(f"{topic} {modifier}")

    return queries


def search_ai_news(
    query: str,
    max_results: int = 10,
    preferred_domains: Optional[list[str]] = None,
    blocked_domains: Optional[list[str]] = None,
) -> str:
    """Search for AI/LLM related news using Tavily API.

    Args:
        query: Search query for AI news (e.g., "new LLM model release 2026")
        max_results: Maximum number of results to return (default: 10)
        preferred_domains: List of domains to prioritize (uses include_domains)
        blocked_domains: List of domains to exclude (uses exclude_domains)

    Returns:
        JSON string containing search results with titles, URLs, and snippets

    Note:
        If neither preferred_domains nor blocked_domains is provided,
        defaults to the AI/LLM whitelist for backward compatibility.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return json.dumps({"error": "TAVILY_API_KEY not set"})

    client = TavilyClient(api_key=api_key)

    # Default AI/LLM whitelist for backward compatibility
    default_domains = [
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
    ]

    # Build search parameters
    search_params = {
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
    }

    # Apply domain filtering
    if preferred_domains:
        search_params["include_domains"] = preferred_domains
    elif not blocked_domains:
        # Use default whitelist only if no filtering specified
        search_params["include_domains"] = default_domains

    if blocked_domains:
        search_params["exclude_domains"] = blocked_domains

    try:
        response = client.search(**search_params)

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


def search_hackernews(query: str, num_results: int = 10) -> str:
    """Search Hacker News for AI-related posts and discussions.

    Args:
        query: Search query (e.g., "AI agent", "LLM framework")
        num_results: Number of results to return (default: 10)

    Returns:
        JSON string containing HN posts with titles, URLs, points, and comments
    """
    try:
        # Use HN Algolia API
        search_url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": num_results,
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
