"""Ported humanize-korean runtime sub-agents.

Ported from https://github.com/epoko77-ai/im-not-ai (agents/humanize-monolith.md,
agents/humanize-diagnostician.md, agents/humanize-finalizer.md). See
docs/superpowers/specs/2026-08-18-im-not-ai-skill-design.md for the full design.

Only the 3 runtime agents the vendored skills/humanize-korean/SKILL.md calls are
ported. "model" is intentionally omitted from each dict so they inherit
article-writer's own model instead of the upstream-hardcoded "opus".
"""

from ..config import (
    HUMANIZE_DIAGNOSTICIAN_PROMPT,
    HUMANIZE_FINALIZER_PROMPT,
    HUMANIZE_MONOLITH_PROMPT,
)

humanize_monolith_agent = {
    "name": "humanize-monolith",
    "description": "5,000자 이하 한글 텍스트의 AI 티를 한 콜(read+read+write, 3회)로 탐지·윤문·자체검증까지 끝내는 단일 호출 윤문 에이전트. light/standard 경로 공용.",
    "system_prompt": HUMANIZE_MONOLITH_PROMPT,
}

humanize_diagnostician_agent = {
    "name": "humanize-diagnostician",
    "description": "Standard 경로 1단계 진단 에이전트. 윤문하지 않고 글 전체를 보고 가장 지배적인 AI 티 패턴 3~6개를 taxonomy ID와 함께 진단한다(02_diagnosis.md).",
    "system_prompt": HUMANIZE_DIAGNOSTICIAN_PROMPT,
}

humanize_finalizer_agent = {
    "name": "humanize-finalizer",
    "description": "Standard 경로 승급 시 마무리 에이전트. 원문과 윤문본을 직접 대조해 의미 보존과 자연성을 한 번에 판정하고, 문제 구간만 국소 보정한다(final.md + 09_finalize.json).",
    "system_prompt": HUMANIZE_FINALIZER_PROMPT,
}
