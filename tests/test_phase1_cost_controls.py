"""Tests for low-risk newsletter cost-control changes."""

import json
from types import SimpleNamespace

from src.main import NewsletterRunMetrics, create_newsletter_agent
from src.utils.merge_articles import merge_newsletter, preview_newsletter


def test_create_newsletter_agent_uses_configured_model(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.MODEL_NAME", "claude-haiku-4-5")
    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr("src.main._build_checkpointer", lambda: SimpleNamespace())

    create_newsletter_agent("2026-06-17")

    assert captured["model"] == "anthropic:claude-haiku-4-5"


def test_create_newsletter_agent_preserves_provider_model_prefix(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.MODEL_NAME", "openai:gpt-5-mini")
    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr("src.main._build_checkpointer", lambda: SimpleNamespace())

    create_newsletter_agent("2026-06-17")

    assert captured["model"] == "openai:gpt-5-mini"


def test_merge_newsletter_excludes_research_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    articles_dir = tmp_path / "articles" / "2026-06-17"
    articles_dir.mkdir(parents=True)
    (articles_dir / "01_main.md").write_text("# Main Article\n\nBody", encoding="utf-8")
    (articles_dir / "02_second.md").write_text("# Second Article\n\nBody", encoding="utf-8")
    (articles_dir / "research_results.md").write_text(
        "# Research Notes\n\nThis should not be merged.",
        encoding="utf-8",
    )

    output_path = merge_newsletter("2026-06-17", version="01")
    newsletter = (tmp_path / output_path).read_text(encoding="utf-8")
    preview = preview_newsletter("2026-06-17")

    assert "Main Article" in newsletter
    assert "Second Article" in newsletter
    assert "Research Notes" not in newsletter
    assert "research_results.md" not in preview


def test_run_metrics_saves_token_and_tool_counts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    metrics = NewsletterRunMetrics("2026-06-17", "quick", "anthropic:claude-test")

    message = SimpleNamespace(
        content="hello",
        usage_metadata={"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
        tool_calls=[{"name": "save_article"}],
    )
    metrics.record_stream_event({"model": {"messages": [message]}})
    metrics.record_model_message(message)
    metrics.record_tool_result("save_article")

    output_path = metrics.save("completed", final_content="hello")
    saved = json.loads((tmp_path / output_path).read_text(encoding="utf-8"))

    assert saved["status"] == "completed"
    assert saved["model"] == "anthropic:claude-test"
    assert saved["token_usage"] == {
        "input_tokens": 10,
        "output_tokens": 3,
        "total_tokens": 13,
    }
    assert saved["tool_calls"] == {"save_article": 1}
    assert saved["tool_results"] == {"save_article": 1}
    assert saved["final_content_chars"] == 5
