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


def test_feedback_loop_keeps_going_until_stop_word(monkeypatch):
    inputs = iter(["짧게 줄여줘", "제목도 바꿔줘", "done"])
    monkeypatch.setattr(main, "_read_feedback", lambda _: next(inputs))
    agent = _ScriptedFeedbackAgent(["수정된 초안", "두 번째 수정"])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "두 번째 수정"
    assert [r["messages"][0]["content"] for r in agent.received] == ["짧게 줄여줘", "제목도 바꿔줘"]


def test_feedback_loop_blank_input_reprompts_instead_of_ending(monkeypatch):
    inputs = iter(["", "", "done"])
    monkeypatch.setattr(main, "_read_feedback", lambda _: next(inputs))
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")

    assert final == "원래 초안"
    assert agent.received == []
    assert next(inputs, None) is None  # both blanks consumed before "done"


def test_feedback_loop_stops_on_done_keyword(monkeypatch):
    monkeypatch.setattr(main, "_read_feedback", lambda _: "done")
    agent = _ScriptedFeedbackAgent([])

    final = main._run_feedback_loop(agent, {}, _Metrics(), "원래 초안")
    assert final == "원래 초안"


def test_resume_feedback_returns_none_when_newsletter_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "validate_api_keys", lambda: True)

    assert main.resume_feedback("2026-08-05") is None


def test_resume_feedback_reads_existing_newsletter_and_runs_loop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "validate_api_keys", lambda: True)
    monkeypatch.setattr(main, "_read_memory", lambda: "")
    monkeypatch.setattr(main, "_build_checkpointer", lambda: SimpleNamespace())
    monkeypatch.setattr(main, "create_deep_agent", lambda **kwargs: SimpleNamespace())

    articles_dir = tmp_path / "articles" / "2026-08-05"
    articles_dir.mkdir(parents=True)
    (articles_dir / "newsletter.md").write_text("기존 뉴스레터", encoding="utf-8")

    monkeypatch.setattr(main, "_read_feedback", lambda _: "done")  # end loop immediately

    result = main.resume_feedback("2026-08-05")

    assert result["final_content"] == "기존 뉴스레터"
    assert Path(result["metrics_path"]).exists()
