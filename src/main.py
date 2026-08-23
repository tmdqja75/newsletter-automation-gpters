"""Main orchestrator agent for newsletter automation."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite3

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

import re

from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    THREADS_DB,
    to_model_spec,
)
from .agents import topic_researcher_agent, article_writer_agent
from .tools.research_collector import run_weekly_research
from .tools.interrupt_tools import auto_select_topics, request_topic_selection
from .utils.merge_articles import merge_newsletter


def _agent_model_spec() -> str:
    """Return a DeepAgents-compatible model spec from MODEL_NAME."""
    return to_model_spec(MODEL_NAME)


def _increment_count(counter: dict[str, int], key: str, amount: int = 1) -> None:
    counter[key] = counter.get(key, 0) + amount


def _extract_usage_metadata(message: Any) -> dict[str, int]:
    """Extract token usage from LangChain messages when providers expose it."""
    usage = getattr(message, "usage_metadata", None)
    if not usage:
        response_metadata = getattr(message, "response_metadata", None) or {}
        usage = response_metadata.get("token_usage") or response_metadata.get("usage")

    if not isinstance(usage, dict):
        return {}

    token_usage: dict[str, int] = {}
    for source_key, target_key in (
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
        ("total_tokens", "total_tokens"),
        ("prompt_tokens", "input_tokens"),
        ("completion_tokens", "output_tokens"),
    ):
        value = usage.get(source_key)
        if isinstance(value, int):
            token_usage[target_key] = token_usage.get(target_key, 0) + value
    return token_usage


class NewsletterRunMetrics:
    """Lightweight generation telemetry persisted beside newsletter outputs."""

    def __init__(self, date_dir: str, mode: str, model: str):
        self.date_dir = date_dir
        self._started = time.perf_counter()
        self.data: dict[str, Any] = {
            "date_dir": date_dir,
            "mode": mode,
            "model": model,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "status": "running",
            "duration_seconds": None,
            "stream_events": 0,
            "model_events": 0,
            "tool_events": 0,
            "interrupt_events": 0,
            "model_messages": 0,
            "model_messages_with_usage": 0,
            "assistant_output_chars": 0,
            "final_content_chars": 0,
            "tool_calls": {},
            "tool_results": {},
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

    def record_stream_event(self, event: dict[str, Any]) -> None:
        self.data["stream_events"] += 1
        for key in event:
            if key == "model" or key == "agent":
                self.data["model_events"] += 1
            elif key == "tools":
                self.data["tool_events"] += 1
            elif key == "__interrupt__":
                self.data["interrupt_events"] += 1

    def record_model_message(self, message: Any) -> None:
        self.data["model_messages"] += 1

        content = getattr(message, "content", "")
        if content:
            self.data["assistant_output_chars"] += len(str(content))

        usage = _extract_usage_metadata(message)
        if usage:
            self.data["model_messages_with_usage"] += 1
            for key, value in usage.items():
                self.data["token_usage"][key] += value

        for tool_call in getattr(message, "tool_calls", None) or []:
            tool_name = tool_call.get("name", "unknown")
            _increment_count(self.data["tool_calls"], tool_name)

    def record_tool_result(self, tool_name: str) -> None:
        _increment_count(self.data["tool_results"], tool_name or "tool")

    def save(self, status: str, final_content: Any = None, error: str | None = None) -> str:
        self.data["status"] = status
        self.data["completed_at"] = datetime.now().isoformat(timespec="seconds")
        self.data["duration_seconds"] = round(time.perf_counter() - self._started, 2)
        if final_content:
            self.data["final_content_chars"] = len(str(final_content))
        if error:
            self.data["error"] = error

        metrics_path = Path(ARTICLES_DIR) / self.date_dir / "run_metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(metrics_path)


def validate_api_keys() -> bool:
    """Validate that required API keys are set."""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")

    if missing:
        print(f"❌ 필수 API 키가 설정되지 않았습니다: {', '.join(missing)}", file=sys.stderr)
        print("   .env 파일을 확인하세요.", file=sys.stderr)
        return False
    return True

def save_article(content: str, filename: str, date_dir: str) -> str:
    """Save an article to the articles directory.

    Args:
        content: The article content in markdown format
        filename: Name of the file (e.g., "01_topic1.md")
        date_dir: Date directory name (e.g., "2026-01-15")

    Returns:
        Path to the saved file
    """
    articles_path = Path(ARTICLES_DIR) / date_dir
    articles_path.mkdir(parents=True, exist_ok=True)

    file_path = articles_path / filename
    file_path.write_text(content, encoding="utf-8")

    return str(file_path)


def _build_checkpointer() -> SqliteSaver:
    """Persistent checkpointer so a thread's message history survives process restarts."""
    Path(THREADS_DB).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(THREADS_DB, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer


def create_newsletter_agent(target_date: str, open_slots: int = 4, use_hitl: bool = False):
    """Create the newsletter orchestrator.

    Tool registration encodes the run mode, so "should I ask the user?" and
    "should I research?" are never model decisions:
      open_slots == 0  -> no research or selection tools at all
      use_hitl         -> request_topic_selection (interrupts)
      otherwise        -> auto_select_topics (no interrupts)
    """
    Path(ARTICLES_DIR).mkdir(parents=True, exist_ok=True)

    tools = [save_article, merge_newsletter]
    if open_slots > 0:
        tools.append(run_weekly_research)
        tools.append(request_topic_selection if use_hitl else auto_select_topics)

    agent_config = {
        "model": _agent_model_spec(),
        "system_prompt": ORCHESTRATOR_PROMPT,
        "tools": tools,
        "subagents": [topic_researcher_agent, article_writer_agent],
        "backend": FilesystemBackend(root_dir=".", virtual_mode=True),
        "checkpointer": _build_checkpointer(),
    }

    return create_deep_agent(**agent_config)


_TODO_STATUS_ICON = {"pending": "⬜", "in_progress": "🔄", "completed": "✅"}


def _print_todos(todos: list[dict]) -> None:
    print("📋 할 일 목록:")
    for todo in todos:
        icon = _TODO_STATUS_ICON.get(todo.get("status"), "•")
        print(f"   {icon} {todo.get('content', '')}")


def _handle_event(event: dict, metrics, final):
    """Print one stream event. Returns (final_content, interrupt_payload_or_None)."""
    pending = None

    for key, value in event.items():
        messages = value.get("messages", []) if isinstance(value, dict) else []

        if key in ("model", "agent"):
            for msg in messages:
                metrics.record_model_message(msg)
                if getattr(msg, "content", None):
                    final = msg.content
                    print(f"📝 응답 수신 ({len(str(msg.content))} 글자)")
                for tool_call in getattr(msg, "tool_calls", None) or []:
                    print(f"🔨 도구 호출: {tool_call.get('name', 'unknown')}")
                    if tool_call.get("name") == "write_todos":
                        _print_todos(tool_call.get("args", {}).get("todos", []))

        elif key == "tools":
            for msg in messages:
                name = getattr(msg, "name", "tool")
                metrics.record_tool_result(name)
                print(f"✅ {name} 완료")

        elif key == "__interrupt__":
            for item in value:
                pending = getattr(item, "value", item)

    return final, pending


def _prompt_user(payload) -> str:
    """Render an interrupt and read a valid selection. Loops until input is sane."""
    if not isinstance(payload, dict) or payload.get("type") != "topic_selection":
        return input(f"⏸️ {payload}\n입력: ").strip()

    print("\n" + "=" * 50)
    for title in payload.get("confirmed") or []:
        print(f"✅ 확정된 토픽: {title}")
    print(payload.get("topics", ""))
    print("=" * 50)

    slots = payload.get("open_slots", 1)
    total = payload.get("total", 0)

    while True:
        raw = input(f"토픽 {slots}개를 선택하세요 (예: 3,7): ").strip()
        numbers = [int(n) for n in re.findall(r"\d+", raw)]
        if len(numbers) != slots:
            print(f"❌ {slots}개를 입력하세요 (입력: {len(numbers)}개)")
        elif any(not 1 <= n <= total for n in numbers):
            print(f"❌ 1~{total} 범위의 번호만 입력하세요")
        else:
            return raw


def _run_with_interrupts(agent, initial, config, metrics):
    """Stream the agent, pausing for input on each interrupt. Unbounded rounds."""
    stream_input, final = initial, None

    while True:
        pending = None
        for event in agent.stream(stream_input, config=config):
            metrics.record_stream_event(event)
            final, payload = _handle_event(event, metrics, final)
            pending = payload or pending
            sys.stdout.flush()

        if pending is None:
            return final

        stream_input = Command(resume=_prompt_user(pending))


def _build_prompt(target_date: str, topics: list[str], open_slots: int) -> str:
    lines = [f"{target_date} 발행 오토마타 뉴스레터를 작성해주세요.", ""]
    if topics:
        lines.append("사용자 지정 토픽 (각각 topic-researcher로 조사하세요):")
        lines += [f"- {topic}" for topic in topics]
        lines.append("")
    lines.append(f"후보에서 추가로 선택할 토픽 수: {open_slots}")
    lines.append(f"아티클 저장 디렉토리: articles/{target_date}/")
    return "\n".join(lines)


def run_newsletter_generation(target_date: str = None, use_hitl: bool = False,
                              user_topics: str = None, count: int = 4):
    """Run the full newsletter generation workflow.

    Args:
        target_date: Publication date (YYYY-MM-DD). Defaults to today.
        use_hitl: Ask the user to pick topics instead of auto-selecting.
        user_topics: Comma-separated topics to research and include.
        count: Total articles in the issue.

    Returns:
        {"final_content": ..., "metrics_path": ...} or None on failure.
    """
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    topics = [t.strip() for t in (user_topics or "").split(",") if t.strip()]
    open_slots = count - len(topics)

    print("🔧 에이전트 초기화 중...")
    if use_hitl and open_slots > 0:
        print("👤 Human-in-the-Loop 모드 활성화")

    agent = create_newsletter_agent(target_date, open_slots=open_slots, use_hitl=use_hitl)
    prompt = _build_prompt(target_date, topics, open_slots)

    print("🤖 에이전트 실행 중 (스트리밍)...\n")
    metrics = NewsletterRunMetrics(target_date, "full", _agent_model_spec())
    final_content = None

    try:
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}
        final_content = _run_with_interrupts(
            agent, {"messages": [{"role": "user", "content": prompt}]}, config, metrics
        )

        print("\n" + "=" * 40)
        print("📋 최종 결과:")
        print("=" * 40)
        print(final_content or "(응답 없음)")

        metrics_path = metrics.save("completed", final_content=final_content)
        print(f"📊 실행 메트릭 저장: {metrics_path}")
        return {"final_content": final_content, "metrics_path": metrics_path}

    except Exception as e:
        metrics_path = metrics.save("failed", final_content=final_content, error=str(e))
        print(f"\n❌ 에이전트 실행 중 오류: {e}", file=sys.stderr)
        print(f"📊 실행 메트릭 저장: {metrics_path}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def run_quick_test(target_date: str = None, use_hitl: bool = False,
                   user_topics: str = None, count: int = 1):
    """Generate a single article to smoke-test the pipeline."""
    topic = (user_topics or "AI 에이전트 최신 소식").split(",")[0].strip()
    return run_newsletter_generation(target_date, use_hitl=False, user_topics=topic, count=1)
