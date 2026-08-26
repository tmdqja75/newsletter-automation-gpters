"""Topic selection tools. Exactly one is registered per run (HITL vs automatic).

Both load candidates from disk and resolve the user's numbers in Python, so the
list the user approves is the list that reaches the writer.
"""

import json
import re

from langgraph.types import interrupt

from .research_collector import load_candidates, load_more_candidates
from .research_report import auto_select, parse_selection, render_selection_list

_NO_CANDIDATES = "오류: 후보가 없습니다. run_weekly_research를 먼저 호출하세요."
_CYCLE_COMMANDS = {"c", "cycle"}


def request_topic_selection(publication_date: str, open_slots: int,
                            confirmed_titles: list[str]) -> str:
    """리서치 후보 목록을 사용자에게 보여주고 토픽을 직접 고르게 합니다.

    반드시 run_weekly_research가 끝난 뒤에 호출하세요.

    선택은 여러 라운드에 나눠 할 수 있습니다 (예: 2개는 지금 목록에서,
    나머지는 다른 후보 묶음에서). "c"를 입력하면 raw_search_results.json에서
    아직 안 보여준 후보 묶음으로 넘어갑니다.

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

    shown = candidates
    seen_urls = {c["url"] for c in shown}
    picked: list[dict] = []
    remaining = open_slots
    message = None

    while True:
        payload = {
            "type": "topic_selection",
            "topics": render_selection_list(shown),
            "confirmed": confirmed_titles,
            "picked": [c["title"] for c in picked],
            "open_slots": remaining,
            "total": len(shown),
        }
        if message:
            payload["message"] = message
        message = None

        text = str(interrupt(payload)).strip()

        if text.lower() in _CYCLE_COMMANDS:
            batch = load_more_candidates(publication_date, seen_urls, len(candidates))
            if not batch:
                message = "더 이상 보여줄 후보가 없습니다."
                continue
            shown = batch
            seen_urls |= {c["url"] for c in shown}
            continue

        numbers = [int(n) for n in re.findall(r"\d+", text)]
        if not numbers or len(numbers) > remaining:
            message = f"1~{remaining}개 사이로 선택하거나 c를 입력하세요 (입력: {len(numbers)}개)"
            continue

        try:
            picked_now = parse_selection(text, shown, expected=len(numbers))
        except ValueError as exc:
            message = f"오류: {exc}"
            continue

        picked.extend(picked_now)
        remaining -= len(picked_now)
        if remaining == 0:
            return json.dumps(picked, ensure_ascii=False)

        picked_urls_now = {c["url"] for c in picked_now}
        shown = [c for c in shown if c["url"] not in picked_urls_now]


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
