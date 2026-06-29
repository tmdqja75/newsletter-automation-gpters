"""Interrupt-based tools for human-in-the-loop workflows."""

from langgraph.types import interrupt


def request_topic_selection(topic_candidates: str) -> str:
    """Present topic candidates to the user and wait for their selection.

    Args:
        topic_candidates: a markdown string containing the list of topic candidates for selection.

    Returns:
        User's selection result as a string
    """
    selection = interrupt({
        "type": "topic_selection",
        "topics": topic_candidates,
        "message": "research_results.md에 있는 토픽 후보 중 원하는 토픽을 자유롭게 선택해주세요. (예: 1,3,5,7)",
    })
    return f"사용자 선택 결과: {selection}"
