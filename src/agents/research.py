"""Research subagent for gathering AI/LLM news and trends."""

from typing import Optional
from ..tools.search_tools import search_ai_news, search_hackernews
from ..tools.content_tools import fetch_article_content
from ..config import RESEARCH_AGENT_PROMPT, build_research_agent_prompt


def create_research_subagent(user_context: Optional[dict] = None) -> dict:
    """Create research subagent with optional user context for personalization.

    Args:
        user_context: Optional dictionary containing:
            - topic: str - Main topic to research
            - topic_description: str (optional) - Detailed description
            - subtopics: list[str] (optional) - Specific areas of interest
            - preferred_sources: list[str] (optional) - Preferred source types
            - goal: str (optional) - User's purpose (work/learning/business/hobby)
            - difficulty: str (optional) - User's level (beginner/intermediate/advanced)

    Returns:
        Dictionary configuration for the research subagent

    Examples:
        # Default AI/LLM research
        >>> agent = create_research_subagent()

        # Personalized research
        >>> agent = create_research_subagent({
        ...     "topic": "의료 AI",
        ...     "subtopics": ["진단", "영상분석"],
        ...     "goal": "learning",
        ...     "difficulty": "intermediate"
        ... })
    """
    # Use personalized prompt if context provided, otherwise use default
    if user_context:
        system_prompt = build_research_agent_prompt(
            topic=user_context.get("topic", ""),
            topic_description=user_context.get("topic_description"),
            subtopics=user_context.get("subtopics"),
            preferred_sources=user_context.get("preferred_sources"),
            goal=user_context.get("goal"),
            difficulty=user_context.get("difficulty"),
        )
        description = f"{user_context.get('topic', '주제')} 관련 리서치 전문가. 최신 뉴스, 기술 블로그, 연구 자료를 검색하고 분석합니다."
    else:
        system_prompt = RESEARCH_AGENT_PROMPT
        description = "AI/LLM 뉴스 및 트렌드 리서치 전문가. 최신 모델 발표, HackerNews 논의, 기술 블로그를 검색하고 분석합니다."

    return {
        "name": "research-agent",
        "description": description,
        "system_prompt": system_prompt,
        "tools": [search_ai_news, search_hackernews, fetch_article_content],
    }


# Backward compatibility: Default research subagent for AI/LLM news
research_subagent = create_research_subagent()
