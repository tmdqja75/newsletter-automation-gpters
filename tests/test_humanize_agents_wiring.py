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
