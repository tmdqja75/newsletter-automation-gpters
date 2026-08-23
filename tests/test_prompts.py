"""Tests that config prompts contain required instructions."""

from src.config import (
    TOPIC_RESEARCHER_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
    SVG_DIAGRAM_PROMPT,
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


def test_article_writer_prompt_instructs_diagram_tool():
    """Must know when and how to call create_svg_diagram and splice the result in."""
    assert "create_svg_diagram" in ARTICLE_WRITER_PROMPT
    assert "focus" in ARTICLE_WRITER_PROMPT


def test_article_writer_preserves_citations():
    """Article writer must be told not to remove inline citations."""
    assert "제거" in ARTICLE_WRITER_PROMPT or "수정하지" in ARTICLE_WRITER_PROMPT


def test_orchestrator_forbids_inventing_topics():
    """Zero research results must stop the run, not trigger hallucinated topics."""
    assert "지어내지" in ORCHESTRATOR_PROMPT


def test_orchestrator_handles_feedback_by_editing_saved_files():
    """Revisions must patch existing article files, not regenerate everything."""
    assert "merge_newsletter" in ORCHESTRATOR_PROMPT
    assert "피드백" in ORCHESTRATOR_PROMPT


def test_orchestrator_prompt_handles_diagram_feedback():
    """SVG-shaped feedback must call create_svg_diagram with the existing path, not edit .md text."""
    assert "create_svg_diagram" in ORCHESTRATOR_PROMPT
    assert "existing_svg_path" in ORCHESTRATOR_PROMPT


def test_orchestrator_infers_preferences_without_explicit_trigger():
    """Taste signals in feedback must be saved without requiring a "remember" keyword."""
    assert "memory/preferences.md" in ORCHESTRATOR_PROMPT
    assert "덧붙여" in ORCHESTRATOR_PROMPT
    assert "취향" in ORCHESTRATOR_PROMPT


# --- SVG diagram prompt ---

def test_svg_diagram_prompt_scopes_to_one_diagram():
    """Must not write article prose, only draw one diagram."""
    assert "글은 쓰지 않습니다" in SVG_DIAGRAM_PROMPT or "다이어그램 1개" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_viewbox():
    assert "viewBox" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_forbids_host_dependent_styling():
    """Embedded via <img>, so no currentColor / external font links / script."""
    assert "currentColor" in SVG_DIAGRAM_PROMPT
    assert "<script>" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_cjk_font_fallback():
    assert "Gothic" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_requires_worth_it_output_field():
    assert "worth_it" in SVG_DIAGRAM_PROMPT
    assert "caption" in SVG_DIAGRAM_PROMPT


def test_svg_diagram_prompt_handles_revision_mode():
    assert "existing_svg" in SVG_DIAGRAM_PROMPT
