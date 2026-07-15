"""Tests that config prompts contain required instructions."""

from src.config import (
    RESEARCH_AGENT_PROMPT,
    ORCHESTRATOR_PROMPT,
    ARTICLE_WRITER_PROMPT,
    TOPIC_SELECTOR_PROMPT,
)


# --- Problem 1: Hallucination fixes ---

def test_research_prompt_requires_fetch():
    """Research agent must be instructed to fetch full article content."""
    assert "fetch_article_content" in RESEARCH_AGENT_PROMPT
    # Must explicitly say fetching is mandatory, not optional
    assert "반드시" in RESEARCH_AGENT_PROMPT or "필수" in RESEARCH_AGENT_PROMPT


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


# --- Problem 2: Real-world use case discovery ---

def test_research_prompt_has_usecase_category():
    """Research agent must have a category for real-world AI use cases."""
    assert "실제 AI" in RESEARCH_AGENT_PROMPT or "활용 사례" in RESEARCH_AGENT_PROMPT
    # Must include Show HN targeting
    assert "Show HN" in RESEARCH_AGENT_PROMPT


def test_research_prompt_explains_forum_and_primary_source_urls():
    """Forum candidates preserve community context while prioritizing distinct primary sources."""
    # The optional field and community context are explicit in the candidate contract.
    assert "선택적으로 original_url" in RESEARCH_AGENT_PROMPT
    assert "포럼 출처 URL" in RESEARCH_AGENT_PROMPT

    # The report keeps mandatory fields consecutively numbered even when a
    # distinct primary source is absent.
    assert "3. 출처 URL" in RESEARCH_AGENT_PROMPT
    assert "4. 발표/게시 날짜" in RESEARCH_AGENT_PROMPT
    assert "5. 중요도" in RESEARCH_AGENT_PROMPT
    assert "6. 카테고리" in RESEARCH_AGENT_PROMPT

    # A primary/original URL is separately reported only when it differs from
    # the forum URL, and it takes priority for factual verification.
    assert "- 원문/주요 출처 URL: <original_url>" in RESEARCH_AGENT_PROMPT
    assert "original_url이 포럼 URL과 다를 때만 표시" in RESEARCH_AGENT_PROMPT
    assert "사실 검증은 이 URL을 우선 사용" in RESEARCH_AGENT_PROMPT


def test_topic_selector_prioritizes_usecases():
    """Topic selector must be told to rank use-case stories highly."""
    assert "활용 사례" in TOPIC_SELECTOR_PROMPT or "실제" in TOPIC_SELECTOR_PROMPT
    # Must have weighting or priority guidance
    assert "우선" in TOPIC_SELECTOR_PROMPT or "높은" in TOPIC_SELECTOR_PROMPT
