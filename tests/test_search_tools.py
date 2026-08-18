"""Tests for search_ai_news's Tavily call construction."""

import json
from unittest.mock import MagicMock

from src.tools.search_tools import search_ai_news


def test_search_ai_news_requests_news_topic_and_no_domain_whitelist(monkeypatch):
    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}
    monkeypatch.setattr("src.tools.search_tools.TavilyClient", lambda api_key: mock_client)
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    search_ai_news("test query", article_date="2026-08-05")

    _, kwargs = mock_client.search.call_args
    assert kwargs["topic"] == "news"
    assert "include_domains" not in kwargs
    # exclude_domains stays — these three are covered by official_blogs instead
    assert set(kwargs["exclude_domains"]) == {"openai.com", "anthropic.com", "deepmind.google"}


def test_search_ai_news_returns_valid_json_on_missing_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = json.loads(search_ai_news("test query"))
    assert "error" in result


import httpx


def _make_mock_github_search_client(payload: dict) -> httpx.Client:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


def test_search_github_repos_shapes_results_and_builds_query(monkeypatch):
    from src.tools.search_tools import search_github_repos

    payload = {
        "items": [
            {"full_name": "microsoft/skill-recorder",
             "html_url": "https://github.com/microsoft/skill-recorder",
             "description": "Records sessions", "stargazers_count": 1763,
             "created_at": "2026-07-29T00:00:00Z"},
        ]
    }
    mock_client = _make_mock_github_search_client(payload)
    monkeypatch.setattr("src.tools.search_tools.httpx.Client", lambda **kwargs: mock_client)

    result = json.loads(search_github_repos("topic:ai-agents", "2026-08-05"))

    assert result == [{
        "full_name": "microsoft/skill-recorder",
        "url": "https://github.com/microsoft/skill-recorder",
        "description": "Records sessions",
        "stars": 1763,
        "created_at": "2026-07-29T00:00:00Z",
    }]

    call_kwargs = mock_client.get.call_args.kwargs
    assert "created:>2026-07-22" in call_kwargs["params"]["q"]
    assert call_kwargs["params"]["sort"] == "stars"


def test_search_github_repos_handles_network_error(monkeypatch):
    from src.tools.search_tools import search_github_repos

    def boom(**kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr("src.tools.search_tools.httpx.Client", boom)

    result = json.loads(search_github_repos("topic:ai-agents", "2026-08-05"))
    assert "error" in result


def test_search_github_repos_rejects_bad_date():
    from src.tools.search_tools import search_github_repos

    result = json.loads(search_github_repos("topic:ai-agents", "not-a-date"))
    assert "error" in result
