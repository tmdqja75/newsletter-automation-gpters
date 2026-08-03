"""Render research candidates to text and parse selections back to candidates.

Pure: stdlib only, no filesystem, no network, no model. render_research_results
and render_selection_list both enumerate the same list, and parse_selection
indexes back into it, so the numbering the user sees is the numbering they get.
"""

import re

CATEGORY_LABELS_KO = {
    "model_releases": "모델발표",
    "agents_automation": "에이전트",
    "research_papers": "연구",
    "tools_infra": "도구",
    "industry_business": "산업동향",
    "policy_society": "정책",
    "study_resources": "학습자료",
    "real_world_usecases": "활용사례",
    "official_blogs": "공식블로그",
    "pytorch_kr_community": "커뮤니티",
}


def _importance(candidate: dict) -> str:
    """Apply the rule the old research prompt asked a model to eyeball.

    The score formula in research_collector already encodes it:
    real_world_usecases +0.3, HN >50 points +0.2, missing date -0.5.
    """
    score = candidate.get("score") or 0
    if candidate.get("category") == "real_world_usecases" or score >= 0.8:
        return "높음"
    return "중간" if score >= 0.4 else "낮음"


def _label(candidate: dict) -> str:
    category = candidate.get("category", "")
    return CATEGORY_LABELS_KO.get(category, category or "기타")


def render_research_results(result: dict) -> str:
    """Render the full candidate report written to articles/{date}/research_results.md."""
    lines = [f"# 리서치 결과 ({result.get('publication_date', '')})", ""]

    if result.get("errors"):
        lines.append("> 수집 중 오류:")
        lines += [f"> - {error}" for error in result["errors"]]
        lines.append("")

    for i, candidate in enumerate(result.get("candidates", []), 1):
        cafe = " / 스터디카페" if candidate.get("topic_type") == "study_cafe" else ""
        lines.append(f"## {i}. {candidate['title']}")
        lines.append(f"- 카테고리: {_label(candidate)}{cafe}")
        lines.append(f"- 중요도: {_importance(candidate)}")
        lines.append(f"- 게시일: {candidate.get('published_at') or '날짜 미상'}")
        lines.append(f"- URL: {candidate['url']}")
        original = candidate.get("original_url")
        if original and original != candidate["url"]:
            lines.append(f"- 원문 URL: {original}  (사실 검증은 이 URL 우선)")
        lines.append(f"- 요약: {candidate.get('summary', '')}")
        for fact in candidate.get("key_facts") or []:
            lines.append(f"  - {fact}")
        if candidate.get("why_it_matters"):
            lines.append(f"- 왜 중요한가: {candidate['why_it_matters']}")
        lines.append("")

    return "\n".join(lines)


def render_selection_list(candidates: list[dict]) -> str:
    """Render the compact one-line-per-candidate list shown at the interrupt."""
    return "\n".join(
        f"{i:2}. [{_label(c)}] {c['title']}"
        f"  ({c.get('published_at') or '날짜 미상'}, 중요도 {_importance(c)})"
        for i, c in enumerate(candidates, 1)
    )


def parse_selection(text, candidates: list[dict], expected: int) -> list[dict]:
    """Resolve a user's "3,7" into candidate dicts. Raises ValueError on bad input."""
    numbers = [int(n) for n in re.findall(r"\d+", str(text))]

    if len(numbers) != expected:
        raise ValueError(f"토픽 {expected}개를 선택해야 합니다 (입력: {len(numbers)}개)")

    out_of_range = [n for n in numbers if not 1 <= n <= len(candidates)]
    if out_of_range:
        raise ValueError(f"1~{len(candidates)} 범위를 벗어난 번호: {out_of_range}")

    return [candidates[n - 1] for n in numbers]


def auto_select(candidates: list[dict], n: int) -> list[dict]:
    """Pick the top n (already score-sorted), reserving a study_cafe slot last."""
    if n <= 0:
        return []

    cafe = next((c for c in candidates if c.get("topic_type") == "study_cafe"), None)
    if cafe is None or n == 1:
        return candidates[:n]

    mains = [c for c in candidates if c is not cafe]
    return mains[: n - 1] + [cafe]
