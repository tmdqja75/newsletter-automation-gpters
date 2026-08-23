"""SVG diagram generation and revision for newsletter articles."""

import json
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import config


def _default_llm_call(system_prompt: str, user_content: str) -> str:
    """Make one isolated LLM call and return its raw text content."""
    from langchain.chat_models import init_chat_model

    model = init_chat_model(config.to_model_spec(config.MODEL_NAME))
    response = model.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ])
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


def create_svg_diagram(
    topic_slug: str,
    date_dir: str,
    article_text: str = "",
    focus: str = "",
    existing_svg_path: str | None = None,
    feedback: str | None = None,
    llm_call=None,
) -> str:
    """Generate or revise one SVG diagram for an article topic.

    Creation: pass article_text + focus.
    Revision: pass existing_svg_path + feedback (article_text/focus omitted
    — the existing markup + feedback fully determine the edit).

    Returns a markdown snippet ready to paste into the article
    ("![caption](topic_slug.svg)\\n\\ncaption"), "다이어그램 생략: ..." if the
    LLM judged it not worth drawing, or "오류: ..." on failure.
    """
    if llm_call is None:
        llm_call = _default_llm_call

    user_parts = []
    if article_text:
        user_parts.append(f"article_text:\n{article_text}")
    if focus:
        user_parts.append(f"focus:\n{focus}")
    if existing_svg_path:
        existing_svg = Path(existing_svg_path).read_text(encoding="utf-8")
        user_parts.append(f"existing_svg:\n{existing_svg}")
    if feedback:
        user_parts.append(f"feedback:\n{feedback}")
    user_content = "\n\n".join(user_parts)

    try:
        raw = llm_call(config.SVG_DIAGRAM_PROMPT, user_content)
        data = json.loads(raw)
    except Exception as exc:
        return f"오류: SVG 생성 실패 - {exc}"

    if not data.get("worth_it"):
        return "다이어그램 생략: 이 토픽엔 다이어그램이 필요 없다고 판단했어요."

    svg = data.get("svg", "")
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        return f"오류: SVG 생성 실패 - 잘못된 SVG 마크업 ({exc})"

    if existing_svg_path:
        svg_path = Path(existing_svg_path)
    else:
        svg_path = Path(config.ARTICLES_DIR) / date_dir / f"{topic_slug}.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")

    try:
        webbrowser.open(f"file://{svg_path.resolve()}")
    except Exception:
        pass

    caption = data.get("caption", "")
    return f"![{caption}]({svg_path.name})\n\n{caption}"
