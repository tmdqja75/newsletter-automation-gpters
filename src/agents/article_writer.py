"""Article writing subagent: researches, drafts, and tone-edits in one pass."""

from ..tools.search_tools import search_ai_news
from ..tools.content_tools import fetch_article_content
from ..config import ARTICLE_WRITER_PROMPT


article_writer_agent = {
    "name": "article-writer",
    "description": "토픽별 아티클 작성 전문가. 필요 시 Tavily로 추가 리서치를 하고, 오토마타 톤앤매너에 맞춰 최종 아티클을 작성합니다.",
    "system_prompt": ARTICLE_WRITER_PROMPT,
    "tools": [search_ai_news, fetch_article_content],
}
