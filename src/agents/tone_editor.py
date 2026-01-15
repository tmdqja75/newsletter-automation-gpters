"""Tone and manner editing subagent for newsletter style consistency."""

from ..config import TONE_EDITOR_PROMPT


tone_agent = {
    "name": "tone-editor",
    "description": "오토마타 뉴스레터 톤앤매너 교정. 친근하면서도 전문적인 해요체로 아티클을 교정합니다.",
    "system_prompt": TONE_EDITOR_PROMPT,
    "tools": [],  # No tools needed - uses text editing only
}
