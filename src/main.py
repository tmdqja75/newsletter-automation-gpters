"""Main orchestrator agent for newsletter automation."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .config import (
    ORCHESTRATOR_PROMPT,
    ARTICLES_DIR,
    ANTHROPIC_API_KEY,
    TAVILY_API_KEY,
    MODEL_NAME,
    to_model_spec,
)
from .agents import topic_researcher_agent, article_writer_agent
from .tools.interrupt_tools import request_topic_selection
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


def create_newsletter_agent(target_date: str, articles_root: str = None, use_hitl: bool = False):
    """Create the main newsletter orchestrator agent.

    Args:
        target_date: The date for which to create the newsletter (YYYY-MM-DD format)
        articles_root: Root directory for article storage (default: ./articles)
        use_hitl: Whether to use human-in-the-loop for topic selection

    Returns:
        Configured deep agent for newsletter automation
    """
    if articles_root is None:
        articles_root = ARTICLES_DIR

    # Ensure articles directory exists
    Path(articles_root).mkdir(parents=True, exist_ok=True)

    # Build tool list
    tools = [save_article, merge_newsletter]
    system_prompt = ORCHESTRATOR_PROMPT

    if use_hitl:
        tools.append(request_topic_selection)
        
        system_prompt = f"""이번 주 오토마타 뉴스레터를 작성해주세요.

발행 예정일: {target_date}

## 작업 순서 (HITL 모드)
1. 요청한 날짜 아티클 저장 디렉토리 폴더 안에 이미 research_results.md가 존재한다면, 리서치를 하지 말고 해당 파일을 그대로 사용하세요. 그리고, request_topic_selction 도구를 호출하여 사용자에게 토픽 선택을 요청하세요.
2. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요. AI 에이전트나 LLM 관련하여 최근 일주일에 일어난 일들을 위주로 수집해주세요.
3. research-agent의 결과를 그대로 markdown 파일로 아티클 저장 디렉토리에 저장해 주세요. (research_results.md)
4. request_topic_selection 도구를 호출하여 사용자에게 토픽 선택을 요청하세요
5. 사용자가 선택한 모든 토픽에 대해 article-writer를 **동시에(병렬로)** 호출하여 아티클을 작성하세요 (선택 개수는 사용자 자유, research_results.md에 있는 넘버링 기준으로 아티클 주제·요약·출처 URL을 전달). 토픽별로 순차 호출하지 말고, 한 번의 turn에서 선택된 토픽 수만큼 article-writer tool call을 함께 내보내세요.
6. 완성된 아티클을 순서대로 저장하세요 (01_[토픽명].md, 02_[토픽명].md, ...)
- 스터디 카페 토픽이 포함되어 있다면 마지막 번호로 study_cafe.md로 저장하세요
7. merge_newsletter를 호출하여 최종 뉴스레터를 생성하세요

아티클 저장 디렉토리: articles/{target_date}/
"""

    # Build agent configuration
    model_spec = _agent_model_spec()
    agent_config = {
        "model": model_spec,
        "system_prompt": system_prompt,
        "tools": tools,
        "subagents": [topic_researcher_agent, article_writer_agent],
        "backend": FilesystemBackend(root_dir=".", virtual_mode=True),
    }

    if use_hitl:
        agent_config["checkpointer"] = MemorySaver()

    agent = create_deep_agent(**agent_config)

    return agent


def run_newsletter_generation(target_date: str = None, use_hitl: bool = False, user_topics: str = None):
    """Run the full newsletter generation workflow.

    Args:
        target_date: Target date for the newsletter (YYYY-MM-DD format)
                    Defaults to next Wednesday
        use_hitl: Whether to enable human-in-the-loop for topic selection
        user_topics: Comma-separated list of topics to force-include as articles

    Returns:
        Path to the generated newsletter
    """
    # Validate API keys first
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print("🔧 에이전트 초기화 중...")
    if use_hitl:
        print("👤 Human-in-the-Loop 모드 활성화")

    agent = create_newsletter_agent(target_date=target_date, use_hitl=use_hitl)

    prompt = "이번 주 오토마타 뉴스레터를 작성해주세요."
    
    # Build mandatory topics block if provided
    mandatory_topics_block = ""
    if user_topics:
        topics_list = [t.strip() for t in user_topics.split(",") if t.strip()]
        topics_formatted = "\n".join(f"- {t}" for t in topics_list)
        mandatory_topics_block = f"\n\n**필수 포함 토픽 (사용자 요청):**\n{topics_formatted}\n\n위 토픽들은 반드시 본문 기사로 작성되어야 합니다. 나머지 슬롯은 리서치 결과에서 토픽 선택 에이전트가 채워도 됩니다."

        prompt += mandatory_topics_block

    print("🤖 에이전트 실행 중 (스트리밍)...")
    print()
    metrics = NewsletterRunMetrics(target_date, "full", _agent_model_spec())
    final_content = None

    try:
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}

        for event in agent.stream({"messages": [{"role": "user", "content": prompt}]}, config=config):
            metrics.record_stream_event(event)
            for key, value in event.items():
                # Handle model output (agent responses)
                if key == "model":
                    if "messages" in value:
                        for msg in value["messages"]:
                            metrics.record_model_message(msg)
                            if hasattr(msg, 'content') and msg.content:
                                final_content = msg.content
                                # Show progress but truncate very long responses
                                if len(msg.content) > 500:
                                    print(f"📝 응답 수신 중... ({len(msg.content)} 글자)")
                                else:
                                    print(f"📝 {msg.content}")
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get('name', 'unknown')
                                    print(f"🔨 도구 호출: {tool_name}")

                # Handle tool execution results
                elif key == "tools":
                    if "messages" in value:
                        for msg in value["messages"]:
                            tool_name = getattr(msg, 'name', 'tool')
                            metrics.record_tool_result(tool_name)
                            print(f"✅ {tool_name} 완료")

                # Handle agent events (older format)
                elif key == "agent":
                    if "messages" in value:
                        for msg in value["messages"]:
                            metrics.record_model_message(msg)
                            if hasattr(msg, 'content') and msg.content:
                                final_content = msg.content

                elif key == "__interrupt__":
                    if use_hitl:
                        for interrupt_data in value:
                            payload = interrupt_data.value if hasattr(interrupt_data, 'value') else interrupt_data
                            if isinstance(payload, dict) and payload.get("type") == "topic_selection":
                                print("\n" + "=" * 50)
                                print("📋 토픽 후보 목록:")
                                print("=" * 50)
                                print(payload.get("topics", ""))
                                print("=" * 50)
                                print(payload.get("message", "원하는 토픽을 선택해주세요."))
                                print("(예: 1,3,5,9 또는 reject)")
                                print()
                                user_input = input("선택: ").strip()

                                if user_input.lower() == "reject":
                                    resume_value = "reject: 토픽을 다시 선정해주세요. topic-selector만 다시 호출하고, 리서치는 재사용하세요."
                                else:
                                    resume_value = f"선택된 토픽 번호: {user_input}"

                                # Resume the agent with user's selection
                                for event in agent.stream(
                                    Command(resume=resume_value),
                                    config=config,
                                ):
                                    metrics.record_stream_event(event)
                                    for k, v in event.items():
                                        if k == "model":
                                            if "messages" in v:
                                                for msg in v["messages"]:
                                                    metrics.record_model_message(msg)
                                                    if hasattr(msg, 'content') and msg.content:
                                                        final_content = msg.content
                                                        if len(msg.content) > 500:
                                                            print(f"📝 응답 수신 중... ({len(msg.content)} 글자)")
                                                        else:
                                                            print(f"📝 {msg.content}")
                                                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                                        for tc in msg.tool_calls:
                                                            print(f"🔨 도구 호출: {tc.get('name', 'unknown')}")
                                        elif k == "tools":
                                            if "messages" in v:
                                                for msg in v["messages"]:
                                                    metrics.record_tool_result(getattr(msg, 'name', 'tool'))
                                                    print(f"✅ {getattr(msg, 'name', 'tool')} 완료")
                                        elif k == "__interrupt__":
                                            # Handle subsequent interrupts (e.g., after reject)
                                            for int_data in v:
                                                pl = int_data.value if hasattr(int_data, 'value') else int_data
                                                if isinstance(pl, dict) and pl.get("type") == "topic_selection":
                                                    print("\n" + "=" * 50)
                                                    print("📋 토픽 후보 목록 (재선정):")
                                                    print("=" * 50)
                                                    print(pl.get("topics", ""))
                                                    print("=" * 50)
                                                    print(pl.get("message", "원하는 토픽을 선택해주세요."))
                                                    retry_input = input("선택: ").strip()
                                                    if retry_input.lower() == "reject":
                                                        retry_value = "reject: 토픽을 다시 선정해주세요."
                                                    else:
                                                        retry_value = f"선택된 토픽 번호: {retry_input}"
                                                    # Resume again
                                                    for ev in agent.stream(Command(resume=retry_value), config=config):
                                                        metrics.record_stream_event(ev)
                                                        for ek, ev_val in ev.items():
                                                            if ek == "model" and "messages" in ev_val:
                                                                for msg in ev_val["messages"]:
                                                                    metrics.record_model_message(msg)
                                                                    if hasattr(msg, 'content') and msg.content:
                                                                        final_content = msg.content
                                                                        print(f"📝 {str(msg.content)[:200]}...")
                                                            elif ek == "tools" and "messages" in ev_val:
                                                                for msg in ev_val["messages"]:
                                                                    metrics.record_tool_result(getattr(msg, 'name', 'tool'))
                                                                    print(f"✅ {getattr(msg, 'name', 'tool')} 완료")
                                                        sys.stdout.flush()
                                    sys.stdout.flush()
                            else:
                                print(f"⏸️ 인터럽트: {payload}")
                    else:
                        print(f"⏸️ 인터럽트: {value}")

            sys.stdout.flush()


        # Print final result
        print("\n" + "=" * 40)
        print("📋 최종 결과:")
        print("=" * 40)
        if final_content:
            print(final_content)
        else:
            print("(응답 없음)")

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


def run_quick_test(target_date: str = None, use_hitl: bool = False, user_topics: str = None):
    """Run a quick test with a single article.

    Args:
        target_date: Target date for the article
        use_hitl: Whether to enable human-in-the-loop for topic selection
        user_topics: Comma-separated list of topics to force-include as articles

    Returns:
        Result dict
    """
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print("🔧 에이전트 초기화 중 (빠른 테스트 모드)...")
    if use_hitl:
        print("👤 Human-in-the-Loop 모드 활성화")

    agent = create_newsletter_agent(target_date=target_date, use_hitl=use_hitl)

    # Build mandatory topics block if provided
    mandatory_topics_block = ""
    if user_topics:
        topics_list = [t.strip() for t in user_topics.split(",") if t.strip()]
        topics_formatted = "\n".join(f"- {t}" for t in topics_list)
        mandatory_topics_block = f"\n\n**필수 포함 토픽 (사용자 요청):**\n{topics_formatted}\n\n위 토픽 중 첫 번째 토픽을 아티클로 작성해주세요."

    prompt = f"""AI 에이전트 관련 뉴스 1개만 찾아서 짧은 아티클을 작성해주세요.{mandatory_topics_block}

## 작업 순서
1. research-agent를 사용하여 AI 에이전트 관련 뉴스 1개를 검색하세요
2. 검색 결과를 바탕으로 200자 내외의 짧은 요약 아티클을 작성하세요
3. save_article 도구로 articles/{target_date}/test_article.md에 저장하세요

간결하게 작업해주세요.
"""

    print("🤖 에이전트 실행 중...")
    print()
    metrics = NewsletterRunMetrics(target_date, "quick", _agent_model_spec())
    final_content = None

    try:
        config = {"configurable": {"thread_id": f"quick-test-{target_date}"}}

        for event in agent.stream({"messages": [{"role": "user", "content": prompt}]}, config=config):
            metrics.record_stream_event(event)
            for key, value in event.items():
                if key == "model":
                    if "messages" in value:
                        for msg in value["messages"]:
                            metrics.record_model_message(msg)
                            if hasattr(msg, 'content') and msg.content:
                                final_content = msg.content
                                print(f"📝 {str(msg.content)[:200]}...")
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    print(f"🔨 {tc.get('name', 'unknown')}")

                elif key == "tools":
                    if "messages" in value:
                        for msg in value["messages"]:
                            metrics.record_tool_result(getattr(msg, 'name', 'tool'))
                            print(f"✅ {getattr(msg, 'name', 'tool')} 완료")

            sys.stdout.flush()

        print("\n" + "=" * 40)
        print("📋 결과:")
        print("=" * 40)
        if final_content:
            print(str(final_content)[:1000])

        metrics_path = metrics.save("completed", final_content=final_content)
        print(f"📊 실행 메트릭 저장: {metrics_path}")

        return {"final_content": final_content, "metrics_path": metrics_path}

    except Exception as e:
        metrics_path = metrics.save("failed", final_content=final_content, error=str(e))
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        print(f"📊 실행 메트릭 저장: {metrics_path}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None
