"""Tests that config prompts contain required instructions."""

from src.config import (
    RESEARCH_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT,
    TONE_EDITOR_PROMPT,
    TOPIC_SELECTOR_PROMPT,
)


# --- Problem 1: Hallucination fixes ---

def test_research_prompt_requires_fetch():
    """Research agent must be instructed to fetch full article content."""
    assert "fetch_article_content" in RESEARCH_AGENT_PROMPT
    # Must explicitly say fetching is mandatory, not optional
    assert "반드시" in RESEARCH_AGENT_PROMPT or "필수" in RESEARCH_AGENT_PROMPT


def test_orchestrator_prompt_requires_citations():
    """Orchestrator must be instructed to cite sources inline."""
    assert "출처" in ORCHESTRATOR_PROMPT
    # Must prohibit inventing facts
    assert "만들어내거나" in ORCHESTRATOR_PROMPT or "추측" in ORCHESTRATOR_PROMPT


def test_tone_editor_preserves_citations():
    """Tone editor must be told not to remove inline citations."""
    assert "출처" in TONE_EDITOR_PROMPT
    assert "제거" in TONE_EDITOR_PROMPT or "수정하지" in TONE_EDITOR_PROMPT


# --- Problem 2: Real-world use case discovery ---

def test_research_prompt_has_usecase_category():
    """Research agent must have a category for real-world AI use cases."""
    assert "실제 AI" in RESEARCH_AGENT_PROMPT or "활용 사례" in RESEARCH_AGENT_PROMPT
    # Must include Show HN targeting
    assert "Show HN" in RESEARCH_AGENT_PROMPT


def test_topic_selector_prioritizes_usecases():
    """Topic selector must be told to rank use-case stories highly."""
    assert "활용 사례" in TOPIC_SELECTOR_PROMPT or "실제" in TOPIC_SELECTOR_PROMPT
    # Must have weighting or priority guidance
    assert "우선" in TOPIC_SELECTOR_PROMPT or "높은" in TOPIC_SELECTOR_PROMPT
