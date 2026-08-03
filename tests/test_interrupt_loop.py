"""The interrupt loop must handle unbounded reject rounds, unlike the old
three-level nesting that dead-ended after two."""

from types import SimpleNamespace

import src.main as main


class _Metrics:
    def __init__(self):
        self.events = 0

    def record_stream_event(self, event):
        self.events += 1

    def record_model_message(self, msg):
        pass

    def record_tool_result(self, name):
        pass


class _ScriptedAgent:
    """Yields one interrupt per scripted round, then a final message."""

    def __init__(self, rounds: int):
        self.rounds = rounds
        self.resumes = []

    def stream(self, stream_input, config=None):
        if not isinstance(stream_input, dict):
            self.resumes.append(stream_input.resume)
        if len(self.resumes) < self.rounds:
            payload = SimpleNamespace(value={
                "type": "topic_selection",
                "topics": " 1. [에이전트] 토픽 1\n 2. [연구] 토픽 2",
                "confirmed": [],
                "open_slots": 1,
                "total": 2,
            })
            yield {"__interrupt__": [payload]}
        else:
            yield {"model": {"messages": [SimpleNamespace(content="완료", tool_calls=[])]}}


def test_loop_handles_three_interrupt_rounds(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "1")
    agent = _ScriptedAgent(rounds=3)

    final = main._run_with_interrupts(agent, {"messages": []}, {}, _Metrics())

    assert final == "완료"
    assert agent.resumes == ["1", "1", "1"]


def test_loop_returns_without_interrupts(monkeypatch):
    agent = _ScriptedAgent(rounds=0)
    assert main._run_with_interrupts(agent, {"messages": []}, {}, _Metrics()) == "완료"


def test_prompt_user_rejects_wrong_count_then_accepts(monkeypatch, capsys):
    answers = iter(["1,2", "9", "2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    resume = main._prompt_user({
        "type": "topic_selection",
        "topics": " 1. 토픽 1\n 2. 토픽 2",
        "confirmed": [],
        "open_slots": 1,
        "total": 2,
    })

    assert resume == "2"
    assert "1개" in capsys.readouterr().out


def test_create_agent_registers_hitl_tool_only_with_hitl(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=True)
    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "request_topic_selection" in names
    assert "auto_select_topics" not in names
    assert "checkpointer" in captured

    captured.clear()
    main.create_newsletter_agent("2026-08-05", open_slots=2, use_hitl=False)
    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "auto_select_topics" in names
    assert "request_topic_selection" not in names
    assert "checkpointer" not in captured


def test_create_agent_omits_research_tools_when_no_open_slots(monkeypatch):
    """Every topic named by the user means the run cannot reach Tavily."""
    captured = {}
    monkeypatch.setattr(
        "src.main.create_deep_agent",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )

    main.create_newsletter_agent("2026-08-05", open_slots=0, use_hitl=True)

    names = {getattr(t, "__name__", "") for t in captured["tools"]}
    assert "run_weekly_research" not in names
    assert "request_topic_selection" not in names
    assert "save_article" in names
