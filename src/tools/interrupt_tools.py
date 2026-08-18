"""Topic selection tools. Exactly one is registered per run (HITL vs automatic).

Both load candidates from disk and resolve the user's numbers in Python, so the
list the user approves is the list that reaches the writer.
"""

import json

from langgraph.types import interrupt

from .research_collector import load_candidates
from .research_report import auto_select, parse_selection, render_selection_list

_NO_CANDIDATES = "오류: 후보가 없습니다. run_weekly_research를 먼저 호출하세요."


def request_topic_selection(publication_date: str, open_slots: int,
                            confirmed_titles: list[str]) -> str:
    """리서치 후보 목록을 사용자에게 보여주고 토픽을 직접 고르게 합니다.

    반드시 run_weekly_research가 끝난 뒤에 호출하세요.

    Args:
        publication_date: 뉴스레터 발행일 (YYYY-MM-DD 형식)
        open_slots: 사용자가 골라야 할 토픽 개수
        confirmed_titles: 이미 확정된 사용자 지정 토픽 제목 목록 (화면 표시용)

    Returns:
        선택된 토픽 정보 JSON 배열. 실패 시 "오류:"로 시작하는 문자열.
    """
    candidates = load_candidates(publication_date)
    if not candidates:
        return _NO_CANDIDATES

    selection = interrupt({
        "type": "topic_selection",
        "topics": render_selection_list(candidates),
        "confirmed": confirmed_titles,
        "open_slots": open_slots,
        "total": len(candidates),
    })

    try:
        picked = parse_selection(selection, candidates, open_slots)
    except ValueError as exc:
        return f"오류: {exc}. 이 도구를 다시 호출하세요."

    return json.dumps(picked, ensure_ascii=False)


def auto_select_topics(publication_date: str, open_slots: int) -> str:
    """리서치 후보 중 상위 토픽을 자동으로 선택합니다 (비대화형 모드).

    반드시 run_weekly_research가 끝난 뒤에 호출하세요.

    Args:
        publication_date: 뉴스레터 발행일 (YYYY-MM-DD 형식)
        open_slots: 자동으로 선택할 토픽 개수

    Returns:
        선택된 토픽 정보 JSON 배열. 실패 시 "오류:"로 시작하는 문자열.
    """
    candidates = load_candidates(publication_date)
    if not candidates:
        return _NO_CANDIDATES

    return json.dumps(auto_select(candidates, open_slots), ensure_ascii=False)
