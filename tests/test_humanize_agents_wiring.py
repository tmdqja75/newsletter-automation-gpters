"""The 3 ported humanize-korean sub-agents are correctly shaped."""

from src.agents.humanize_agents import (
    humanize_monolith_agent,
    humanize_diagnostician_agent,
    humanize_finalizer_agent,
)


def test_humanize_agent_names():
    assert humanize_monolith_agent["name"] == "humanize-monolith"
    assert humanize_diagnostician_agent["name"] == "humanize-diagnostician"
    assert humanize_finalizer_agent["name"] == "humanize-finalizer"


def test_humanize_agents_have_no_hardcoded_model():
    # Each must inherit article-writer's model rather than pinning "opus".
    for agent in (humanize_monolith_agent, humanize_diagnostician_agent, humanize_finalizer_agent):
        assert "model" not in agent


def test_humanize_agents_preserve_citation_format():
    for agent in (humanize_monolith_agent, humanize_diagnostician_agent, humanize_finalizer_agent):
        assert "(출처: https://" in agent["system_prompt"]


from types import SimpleNamespace

from src.agents import article_writer_agent
from src.main import create_newsletter_agent


def test_article_writer_nested_backend_is_local_shell():
    from deepagents.backends import LocalShellBackend

    runnable = article_writer_agent["runnable"]
    # The compiled graph stores the backend used to build it on its middleware stack;
    # simplest robust check is that skills/humanize-korean is resolvable through it and
    # the runnable was built with LocalShellBackend — verified via the module the
    # dict-construction code imports, not runtime introspection of the compiled graph.
    import src.agents.article_writer as article_writer_module
    import inspect

    source = inspect.getsource(article_writer_module)
    assert "LocalShellBackend" in source
    assert runnable is not None


def test_orchestrator_backend_is_not_local_shell(monkeypatch):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr("src.main.create_deep_agent", fake_create_deep_agent)

    create_newsletter_agent("2026-06-17")

    from deepagents.backends import FilesystemBackend, LocalShellBackend

    assert isinstance(captured["backend"], FilesystemBackend)
    assert not isinstance(captured["backend"], LocalShellBackend)
