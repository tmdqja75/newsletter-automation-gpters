"""Tests that config prompts contain required instructions."""

from src.config import (
    TOPIC_RESEARCHER_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
)


# --- Problem 1: Hallucination fixes ---

def test_topic_researcher_prompt_requires_fetch():
    """The researcher must be told to fetch primary sources, not just search."""
    assert "fetch_article_content" in TOPIC_RESEARCHER_PROMPT
    assert "반드시" in TOPIC_RESEARCHER_PROMPT or "필수" in TOPIC_RESEARCHER_PROMPT


def test_topic_researcher_prompt_scopes_to_one_topic():
    """It must not re-run weekly research; that is the collector's job."""
    assert "하나" in TOPIC_RESEARCHER_PROMPT


def test_orchestrator_calls_article_writer_in_parallel():
    """Orchestrator must fan out article-writer calls in parallel, not sequentially."""
    assert "article-writer" in ORCHESTRATOR_PROMPT
    assert "병렬" in ORCHESTRATOR_PROMPT


def test_article_writer_prompt_requires_citations():
    """Article writer must be instructed to cite sources inline and not invent facts."""
    assert "출처" in ARTICLE_WRITER_PROMPT
    # Must prohibit inventing facts
    assert "만들어내거나" in ARTICLE_WRITER_PROMPT or "추측" in ARTICLE_WRITER_PROMPT


def test_article_writer_preserves_citations():
    """Article writer must be told not to remove inline citations."""
    assert "제거" in ARTICLE_WRITER_PROMPT or "수정하지" in ARTICLE_WRITER_PROMPT


def test_orchestrator_forbids_inventing_topics():
    """Zero research results must stop the run, not trigger hallucinated topics."""
    assert "지어내지" in ORCHESTRATOR_PROMPT
