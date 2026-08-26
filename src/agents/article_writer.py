"""Article writing subagent: researches, drafts, and tone-edits in one pass."""

from ..tools.search_tools import search_ai_news
from ..tools.content_tools import fetch_article_content
from ..tools.diagram_tools import create_svg_diagram
from ..config import ARTICLE_WRITER_PROMPT


def build_article_writer_agent(preferences: str = "") -> dict:
    """Build the article-writer subagent dict, with user preferences appended
    to its system prompt so tone/style choices honor them directly."""
    system_prompt = ARTICLE_WRITER_PROMPT
    if preferences:
        system_prompt += f"\n\n## 사용자 선호 (기억된 내용)\n{preferences.strip()}\n"

    return {
        "name": "article-writer",
        "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성합니다.",
        "system_prompt": system_prompt,
        "tools": [search_ai_news, fetch_article_content, create_svg_diagram],
    }
