"""Tests for search_ai_news's Tavily call construction."""

import json
from unittest.mock import MagicMock

from src.tools.search_tools import search_ai_news


def test_search_ai_news_requests_news_topic_and_domain_whitelist(monkeypatch):
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}
    monkeypatch.setattr("src.tools.search_tools.TavilyClient", lambda api_key: mock_client)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    search_ai_news("test query", article_date="2026-08-05")

    _, kwargs = mock_client.search.call_args
    assert kwargs["topic"] == "news"
    assert set(kwargs["include_domains"]) == {
        "anthropic.com", "openai.com", "ai.google", "blog.google",
        "huggingface.co", "arxiv.org",
        "techcrunch.com", "theverge.com", "venturebeat.com", "wired.com", "arstechnica.com",
    }
    # exclude_domains stays — these three are covered by official_blogs instead
    assert set(kwargs["exclude_domains"]) == {"openai.com", "anthropic.com", "deepmind.google"}


def test_search_ai_news_returns_valid_json_on_missing_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = json.loads(search_ai_news("test query"))
    assert "error" in result
