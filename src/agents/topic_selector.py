"""Topic selection subagent for newsletter content curation."""

from ..config import TOPIC_SELECTOR_PROMPT


topic_selection_agent = {
    "name": "topic-selector",
    "description": "뉴스레터 토픽 선정 및 우선순위 결정. 리서치 결과를 바탕으로 3개 메인 토픽과 1개 스터디 카페 토픽을 선정합니다.",
    "system_prompt": TOPIC_SELECTOR_PROMPT,
    "tools": [],  # No tools needed - uses reasoning only
}
