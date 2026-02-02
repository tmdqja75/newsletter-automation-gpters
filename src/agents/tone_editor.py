"""Tone and manner editing subagent for newsletter style consistency."""

from typing import Optional
from ..config import (
    TONE_EDITOR_PROMPT,
    DIFFICULTY_TONE,
    DURATION_TONE,
    normalize_difficulty,
    normalize_duration,
)


def build_personalized_tone_prompt(
    difficulty: Optional[str] = None,
    duration: Optional[str] = None,
    base_prompt: str = TONE_EDITOR_PROMPT,
) -> str:
    """
    Build personalized tone editor prompt based on user preferences.

    Args:
        difficulty: User's difficulty level (초급/중급/고급 or beginner/intermediate/advanced)
        duration: User's preferred duration (3분/5분/10분/15분+ or 3min/5min/10min/15min+)
        base_prompt: Base tone editor prompt

    Returns:
        Customized system prompt with personalization guidelines
    """
    additions = []

    if difficulty:
        normalized = normalize_difficulty(difficulty)
        tone_config = DIFFICULTY_TONE.get(normalized, DIFFICULTY_TONE["intermediate"])

        additions.append(f"\n## 난이도별 조정 (사용자 선택: {difficulty})")
        additions.append(f"- 용어 설명 수준: {tone_config['term_explanation']}")
        additions.append(f"- 비유 사용: {tone_config['analogy_usage']}")
        additions.append(f"- 기술적 깊이: {tone_config['technical_depth']}")

        # Add specific examples based on level
        if normalized == "beginner":
            additions.append(
                "\n모든 기술 용어를 상세히 설명하고, 일상적인 비유를 많이 사용하세요."
            )
            additions.append(
                "예: 'RAG(Retrieval-Augmented Generation, 검색 증강 생성)는 AI가 외부 지식을 검색해서 답변하는 방식이에요. 쉽게 말해, AI가 인터넷 검색하면서 답하는 것과 비슷해요.'"
            )
        elif normalized == "intermediate":
            additions.append(
                "\n핵심 용어만 간단히 설명하고, 실무 적용에 초점을 맞추세요."
            )
            additions.append(
                "예: 'RAG(검색 증강 생성)는 외부 지식베이스를 활용하는 기법이에요.'"
            )
        elif normalized == "advanced":
            additions.append(
                "\n기술 용어 설명을 최소화하고, 전문적인 내용에 집중하세요."
            )
            additions.append(
                "예: 'RAG 아키텍처에서 retriever와 generator의 결합 방식...'"
            )

    if duration:
        normalized = normalize_duration(duration)
        duration_config = DURATION_TONE.get(normalized, DURATION_TONE["5min"])

        additions.append(f"\n## 분량별 조정 (사용자 선택: {duration})")
        additions.append(f"- 섹션 상세도: {duration_config['section_detail']}")
        additions.append(f"- 예시 개수: {duration_config['examples']}")
        additions.append(
            f"- 코드 스니펫 포함: {'예' if duration_config['code_snippets'] else '아니오'}"
        )

        # Add specific guidance based on duration
        if normalized == "3min":
            additions.append(
                "\n핵심만 간결하게 전달하세요. 예시는 생략하고 주요 포인트만 나열하세요."
            )
        elif normalized == "5min":
            additions.append(
                "\n균형잡힌 분량으로 핵심을 설명하세요. 중요한 예시 1개 정도를 포함하세요."
            )
        elif normalized == "10min":
            additions.append(
                "\n상세한 설명을 제공하세요. 예시 2개와 코드 스니펫을 포함할 수 있습니다."
            )
        elif normalized == "15min+":
            additions.append(
                "\n깊이 있는 분석을 제공하세요. 다양한 예시와 코드 스니펫을 포함하여 종합적으로 설명하세요."
            )

    if additions:
        return base_prompt + "\n".join(additions)

    return base_prompt


def create_tone_editor_agent(
    difficulty: Optional[str] = None, duration: Optional[str] = None
):
    """
    Create tone editor agent with optional personalization.

    Args:
        difficulty: User's difficulty preference (초급/중급/고급 or beginner/intermediate/advanced)
        duration: User's duration preference (3분/5분/10분/15분+ or 3min/5min/10min/15min+)

    Returns:
        Tone editor agent configuration dict
    """
    system_prompt = build_personalized_tone_prompt(difficulty, duration)

    return {
        "name": "tone-editor",
        "description": "오토마타 뉴스레터 톤앤매너 교정. 친근하면서도 전문적인 해요체로 아티클을 교정합니다.",
        "system_prompt": system_prompt,
        "tools": [],  # No tools needed - uses text editing only
    }


# Default agent for backward compatibility
tone_agent = create_tone_editor_agent()
