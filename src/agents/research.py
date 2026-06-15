"""Research subagent for gathering AI/LLM news and trends."""

from ..tools.content_tools import fetch_article_content
from ..tools.research_collector import collect_weekly_research
from ..config import RESEARCH_AGENT_PROMPT

research_subagent = {
    "name": "research-agent",
    "description": "AI/LLM 뉴스 및 트렌드 리서치 전문가. 최신 모델 발표, HackerNews 논의, 기술 블로그를 검색하고 분석합니다.",
    "system_prompt": RESEARCH_AGENT_PROMPT,
    "tools": [collect_weekly_research, fetch_article_content],
}
