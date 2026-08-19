"""Article writing subagent: researches, drafts, tone-edits, and humanizes in one pass."""

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from ..config import ARTICLE_WRITER_PROMPT, MODEL_NAME, to_model_spec
from ..tools.content_tools import fetch_article_content
from ..tools.search_tools import search_ai_news
from .humanize_agents import (
    humanize_diagnostician_agent,
    humanize_finalizer_agent,
    humanize_monolith_agent,
)

article_writer_agent = {
    "name": "article-writer",
    "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성한 뒤 humanize-korean 스킬로 AI 티를 제거합니다.",
    "runnable": create_deep_agent(
        model=to_model_spec(MODEL_NAME),
        system_prompt=ARTICLE_WRITER_PROMPT,
        tools=[search_ai_news, fetch_article_content],
        subagents=[humanize_monolith_agent, humanize_diagnostician_agent, humanize_finalizer_agent],
        skills=["skills/"],
        backend=LocalShellBackend(root_dir=".", virtual_mode=True),
    ),
}
