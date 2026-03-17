"""Main orchestrator agent for newsletter automation."""

import sys
from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .config import ORCHESTRATOR_PROMPT, ARTICLES_DIR, ANTHROPIC_API_KEY, TAVILY_API_KEY
from .agents import research_subagent, topic_selection_agent, tone_agent
from .tools.interrupt_tools import request_topic_selection
from .utils.merge_articles import merge_newsletter


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


def create_newsletter_agent(articles_root: str = None, use_hitl: bool = False):
    """Create the main newsletter orchestrator agent.

    Args:
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
        system_prompt += """

## HITL 토픽 선정 모드
이 세션은 Human-in-the-Loop 모드입니다. 다음 절차를 따르세요:

1. research-agent로 뉴스를 수집합니다
2. topic-selector를 호출하여 10개 토픽 후보를 받습니다
3. topic-selector의 결과를 그대로 request_topic_selection 도구에 전달하여 사용자에게 선택을 요청합니다
4. 사용자가 선택한 토픽에 대해서만 아티클을 작성합니다 (선택 개수는 사용자 자유)
5. 사용자가 reject하면 topic-selector만 다시 호출하고 (리서치는 재사용), 다시 request_topic_selection을 호출합니다

반드시 request_topic_selection 도구를 호출하여 사용자 승인을 받은 후에 아티클을 작성하세요.
"""

    # Build agent configuration
    agent_config = {
        "system_prompt": system_prompt,
        "tools": tools,
        "subagents": [research_subagent, topic_selection_agent, tone_agent],
    }

    if use_hitl:
        agent_config["checkpointer"] = MemorySaver()

    agent = create_deep_agent(**agent_config)

    return agent


def run_newsletter_generation(target_date: str = None, use_hitl: bool = False):
    """Run the full newsletter generation workflow.

    Args:
        target_date: Target date for the newsletter (YYYY-MM-DD format)
                    Defaults to next Wednesday
        use_hitl: Whether to enable human-in-the-loop for topic selection

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

    agent = create_newsletter_agent(use_hitl=use_hitl)

    if use_hitl:
        prompt = f"""이번 주 오토마타 뉴스레터를 작성해주세요.

발행 예정일: {target_date}

## 작업 순서 (HITL 모드)
1. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요. AI 에이전트나 LLM 관련하여 최근 일주일에 일어난 일들을 위주로 수집해주세요.
2. topic-selector를 사용하여 10개 토픽 후보를 선정하세요
3. request_topic_selection 도구를 호출하여 사용자에게 토픽 선택을 요청하세요
4. 사용자가 선택한 토픽에 대해서만 400-600 단어의 아티클을 작성하세요 (선택 개수는 사용자 자유)
5. tone-editor를 사용하여 각 아티클을 오토마타 스타일로 교정하세요
6. 완성된 아티클을 순서대로 저장하세요 (01_[토픽명].md, 02_[토픽명].md, ...)
   - 스터디 카페 토픽이 포함되어 있다면 마지막 번호로 study_cafe.md로 저장하세요
7. merge_newsletter를 호출하여 최종 뉴스레터를 생성하세요

아티클 저장 디렉토리: articles/{target_date}/
"""
    else:
        prompt = f"""이번 주 오토마타 뉴스레터를 작성해주세요.

발행 예정일: {target_date}

## 작업 순서
1. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요. AI 에이전트나 LLM 관련하여 최근 일주일에 일어난 일들을 위주로 수집해주세요.
2. topic-selector를 사용하여 3개 메인 토픽 + 1개 스터디 카페 토픽을 선정하세요
3. 각 토픽에 대해 400-600 단어의 아티클을 작성하세요
4. tone-editor를 사용하여 각 아티클을 오토마타 스타일로 교정하세요
5. 완성된 아티클을 저장하세요:
   - 01_[토픽명].md
   - 02_[토픽명].md
   - 03_[토픽명].md
   - 04_study_cafe.md
6. merge_newsletter를 호출하여 최종 뉴스레터를 생성하세요

아티클 저장 디렉토리: articles/{target_date}/
"""

    print("🤖 에이전트 실행 중 (스트리밍)...")
    print()

    try:
        config = {"configurable": {"thread_id": f"newsletter-{target_date}"}}
        final_content = None

        for event in agent.stream({"messages": [{"role": "user", "content": prompt}]}, config=config):
            for key, value in event.items():
                # Handle model output (agent responses)
                if key == "model":
                    if "messages" in value:
                        for msg in value["messages"]:
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
                            print(f"✅ {tool_name} 완료")

                # Handle agent events (older format)
                elif key == "agent":
                    if "messages" in value:
                        for msg in value["messages"]:
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
                                    for k, v in event.items():
                                        if k == "model":
                                            if "messages" in v:
                                                for msg in v["messages"]:
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
                                                        for ek, ev_val in ev.items():
                                                            if ek == "model" and "messages" in ev_val:
                                                                for msg in ev_val["messages"]:
                                                                    if hasattr(msg, 'content') and msg.content:
                                                                        final_content = msg.content
                                                                        print(f"📝 {str(msg.content)[:200]}...")
                                                            elif ek == "tools" and "messages" in ev_val:
                                                                for msg in ev_val["messages"]:
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

        return {"final_content": final_content}

    except Exception as e:
        print(f"\n❌ 에이전트 실행 중 오류: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def run_quick_test(target_date: str = None, use_hitl: bool = False):
    """Run a quick test with a single article.

    Args:
        target_date: Target date for the article
        use_hitl: Whether to enable human-in-the-loop for topic selection

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

    agent = create_newsletter_agent(use_hitl=use_hitl)

    prompt = f"""AI 에이전트 관련 뉴스 1개만 찾아서 짧은 아티클을 작성해주세요.

## 작업 순서
1. research-agent를 사용하여 AI 에이전트 관련 뉴스 1개를 검색하세요
2. 검색 결과를 바탕으로 200자 내외의 짧은 요약 아티클을 작성하세요
3. save_article 도구로 articles/{target_date}/test_article.md에 저장하세요

간결하게 작업해주세요.
"""

    print("🤖 에이전트 실행 중...")
    print()

    try:
        config = {"configurable": {"thread_id": f"quick-test-{target_date}"}}
        final_content = None

        for event in agent.stream({"messages": [{"role": "user", "content": prompt}]}, config=config):
            for key, value in event.items():
                if key == "model":
                    if "messages" in value:
                        for msg in value["messages"]:
                            if hasattr(msg, 'content') and msg.content:
                                final_content = msg.content
                                print(f"📝 {str(msg.content)[:200]}...")
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    print(f"🔨 {tc.get('name', 'unknown')}")

                elif key == "tools":
                    if "messages" in value:
                        for msg in value["messages"]:
                            print(f"✅ {getattr(msg, 'name', 'tool')} 완료")

            sys.stdout.flush()

        print("\n" + "=" * 40)
        print("📋 결과:")
        print("=" * 40)
        if final_content:
            print(str(final_content)[:1000])

        return {"final_content": final_content}

    except Exception as e:
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None
