"""Tests that the article-writer subagent is correctly configured and wired in."""

from types import SimpleNamespace

from src.agents import article_writer_agent
from src.main import create_newsletter_agent
from src.tools.content_tools import fetch_article_content
from src.tools.search_tools import search_ai_news


def test_article_writer_agent_has_research_tools():
    assert article_writer_agent["name"] == "article-writer"
    assert search_ai_news in article_writer_agent["tools"]
    assert fetch_article_content in article_writer_agent["tools"]


def test_create_newsletter_agent_uses_article_writer(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)

    create_newsletter_agent("2026-06-17")

    subagent_names = {sa["name"] for sa in captured["subagents"]}
    assert subagent_names == {"research-agent", "article-writer"}
