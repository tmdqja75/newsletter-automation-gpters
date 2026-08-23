"""Tests for preference-memory reading and prompt injection."""

from pathlib import Path

import src.main as main


def test_read_memory_returns_empty_string_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")

    assert main._read_memory() == ""


def test_read_memory_returns_file_contents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "MEMORY_FILE", "memory/preferences.md")
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "preferences.md").write_text("이모지 쓰지 마세요", encoding="utf-8")

    assert main._read_memory() == "이모지 쓰지 마세요"


def test_build_prompt_includes_preferences_when_present():
    prompt = main._build_prompt("2026-08-05", [], 4, "이모지 쓰지 마세요")
    assert "이모지 쓰지 마세요" in prompt
    assert "사용자 선호" in prompt


def test_build_prompt_omits_preferences_section_when_empty():
    prompt = main._build_prompt("2026-08-05", [], 4, "")
    assert "사용자 선호" not in prompt


from types import SimpleNamespace


class _Metrics:
    def record_stream_event(self, event):
        pass

    def record_model_message(self, msg):
        pass

    def record_tool_result(self, name):
        pass


class _ScriptedFeedbackAgent:
    """Returns one fixed reply per stream() call, no interrupts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.received = []

    def stream(self, stream_input, config=None):
        self.received.append(stream_input)
        reply = self.replies.pop(0)
        yield {"model": {"messages": [SimpleNamespace(content=reply, tool_calls=[])]}}


def test_feedback_loop_streams_feedback_and_stops_on_blank_input(monkeypatch):
    inputs = iter(["짧게 줄여줘", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    agent = _ScriptedFeedbackAgent(["수정된 초안"])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "수정된 초안"
    assert agent.received[0]["messages"][0]["content"] == "짧게 줄여줘"


def test_feedback_loop_returns_immediately_when_first_input_blank(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "원래 초안"
    assert agent.received == []


def test_feedback_loop_stops_on_done_keyword(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "done")
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")
    assert final == "원래 초안"
