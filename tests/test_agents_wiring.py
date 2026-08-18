"""Tests that the article-writer subagent is correctly configured and wired in."""

from types import SimpleNamespace

from src.agents import article_writer_agent
from src.main import create_newsletter_agent
from src.tools.content_tools import fetch_article_content
from src.tools.search_tools import search_ai_news


def test_article_writer_agent_is_compiled_subagent():
    assert article_writer_agent["name"] == "article-writer"
    assert "runnable" in article_writer_agent
    assert "tools" not in article_writer_agent  # tools now live inside the nested runnable


def test_create_newsletter_agent_uses_article_writer(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)

    create_newsletter_agent("2026-06-17")

    subagent_names = {sa["name"] for sa in captured["subagents"]}
    assert subagent_names == {"topic-researcher", "article-writer"}


from src.agents import topic_researcher_agent
from src.agents.topic_researcher import TopicResearch


def test_topic_researcher_returns_structured_output():
    assert topic_researcher_agent["name"] == "topic-researcher"
    assert topic_researcher_agent["response_format"] is TopicResearch
    assert search_ai_news in topic_researcher_agent["tools"]
    assert fetch_article_content in topic_researcher_agent["tools"]


def test_topic_research_schema_mirrors_candidate_shape():
    """A researched topic and a picked candidate must be the same shape downstream."""
    fields = set(TopicResearch.model_fields)
    assert fields == {
        "title", "url", "original_url", "published_at",
        "summary", "key_facts", "why_it_matters", "topic_type",
    }
