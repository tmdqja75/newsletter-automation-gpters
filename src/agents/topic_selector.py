"""Topic selection subagent for newsletter content curation."""

from typing import Optional, Dict, Any
from ..config import TOPIC_SELECTOR_PROMPT, build_topic_selector_prompt, DURATION_CONFIG


def create_topic_selector_subagent(user_context: Optional[Dict[str, Any]] = None) -> dict:
    """Create a topic selector subagent with optional personalization.

    Args:
        user_context: Optional user preferences containing:
            - difficulty (str): "beginner", "intermediate", or "advanced"
            - duration (str): "short", "medium", or "long"
            - subtopics (list[str]): Specific areas of interest

    Returns:
        Dictionary configuration for the topic selector subagent
    """
    # Use personalized prompt if context is provided
    if user_context:
        difficulty = user_context.get("difficulty")
        duration = user_context.get("duration")
        subtopics = user_context.get("subtopics")

        system_prompt = build_topic_selector_prompt(
            difficulty=difficulty,
            duration=duration,
            subtopics=subtopics,
        )

        # Build dynamic description based on duration
        duration_key = duration or "medium"
        config = DURATION_CONFIG.get(duration_key, DURATION_CONFIG["medium"])
        num_topics = config["key_issues"]

        description = f"뉴스레터 토픽 선정 및 우선순위 결정. 리서치 결과를 바탕으로 {num_topics}개의 핵심 이슈를 선정합니다."
    else:
        # Use default prompt for backward compatibility
        system_prompt = TOPIC_SELECTOR_PROMPT
        description = "뉴스레터 토픽 선정 및 우선순위 결정. 리서치 결과를 바탕으로 3개 메인 토픽과 1개 스터디 카페 토픽을 선정합니다."

    return {
        "name": "topic-selector",
        "description": description,
        "system_prompt": system_prompt,
        "tools": [],  # No tools needed - uses reasoning only
    }


# Backward compatibility: default instance without personalization
topic_selection_agent = create_topic_selector_subagent()
