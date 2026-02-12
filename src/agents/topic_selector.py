"""Topic selection subagent for newsletter content curation."""

from ..config import TOPIC_SELECTOR_PROMPT


topic_selection_agent = {
    "name": "topic-selector",
    "description": "뉴스레터 토픽 후보 선정. 리서치 결과를 바탕으로 10개 토픽 후보(메인 8-9개 + 스터디 카페 1-2개)를 제시합니다.",
    "system_prompt": TOPIC_SELECTOR_PROMPT,
    "tools": [],  # No tools needed - uses reasoning only
}
