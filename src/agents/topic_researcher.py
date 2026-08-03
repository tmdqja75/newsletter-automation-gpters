"""Topic research subagent: one user-named topic to a validated structured result."""

from typing import Literal

from pydantic import BaseModel, Field

from ..config import TOPIC_RESEARCHER_PROMPT
from ..tools.content_tools import fetch_article_content
from ..tools.search_tools import search_ai_news


class TopicResearch(BaseModel):
    """사용자가 지정한 토픽 하나의 리서치 결과.

    Fields mirror a collect_weekly_research candidate so a researched topic and
    a picked candidate are interchangeable downstream.
    """

    title: str = Field(description="정확한 한국어 제목")
    url: str = Field(description="사실 검증에 사용한 1차 출처 URL")
    original_url: str | None = Field(default=None, description="다른 원문 출처가 있으면")
    published_at: str | None = Field(default=None, description="YYYY-MM-DD, 모르면 null")
    summary: str = Field(description="2-3문장 한국어 요약")
    key_facts: list[str] = Field(default_factory=list, description="원문에서 확인된 사실, 최대 5개")
    why_it_matters: str = Field(default="", description="왜 중요한지 1-2문장")
    topic_type: Literal["main", "study_cafe"] = "main"


topic_researcher_agent = {
    "name": "topic-researcher",
    "description": "사용자가 자연어로 지정한 단일 토픽을 리서치해 구조화된 결과를 반환합니다.",
    "system_prompt": TOPIC_RESEARCHER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
    "response_format": TopicResearch,
}
