"""Main orchestrator agent for newsletter automation."""

import os
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from deepagents import create_deep_agent

from .config import ORCHESTRATOR_PROMPT, ARTICLES_DIR, ANTHROPIC_API_KEY, TAVILY_API_KEY
from .agents import create_research_subagent, topic_selection_agent, tone_agent
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


def create_newsletter_agent(
    articles_root: str = None,
    use_hitl: bool = False,
    user_context: Optional[Dict[str, Any]] = None,
):
    """Create the main newsletter orchestrator agent.

    Args:
        articles_root: Root directory for article storage (default: ./articles)
        use_hitl: Whether to use human-in-the-loop for topic selection
        user_context: Optional user context for personalized research
            - topic: str - Main topic to research
            - topic_description: str (optional) - Detailed description
            - subtopics: list[str] (optional) - Specific areas of interest
            - preferred_sources: list[str] (optional) - Preferred source types
            - goal: str (optional) - User's purpose (work/learning/business/hobby)
            - difficulty: str (optional) - User's level (beginner/intermediate/advanced)

    Returns:
        Configured deep agent for newsletter automation
    """
    if articles_root is None:
        articles_root = ARTICLES_DIR

    # Ensure articles directory exists
    Path(articles_root).mkdir(parents=True, exist_ok=True)

    # Create research subagent (personalized if context provided)
    research_agent = create_research_subagent(user_context)

    # Build agent configuration
    agent_config = {
        "system_prompt": ORCHESTRATOR_PROMPT,
        "tools": [save_article, merge_newsletter],
        "subagents": [research_agent, topic_selection_agent, tone_agent],
    }

    # Only add interrupt_on if human-in-the-loop is enabled
    if use_hitl:
        agent_config["interrupt_on"] = {
            "topic-selector": {
                "allowed_decisions": ["approve", "edit", "reject"]
            }
        }

    agent = create_deep_agent(**agent_config)

    return agent


def run_newsletter_generation(
    target_date: str = None, user_context: Optional[Dict[str, Any]] = None
):
    """Run the full newsletter generation workflow.

    Args:
        target_date: Target date for the newsletter (YYYY-MM-DD format)
                    Defaults to next Wednesday
        user_context: Optional user context for personalized research (see create_newsletter_agent)

    Returns:
        Path to the generated newsletter
    """
    # Validate API keys first
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print("🔧 에이전트 초기화 중...")
    agent = create_newsletter_agent(user_context=user_context)

    prompt = f"""이번 주 오토마타 뉴스레터를 작성해주세요.

발행 예정일: {target_date}

## 작업 순서
1. research-agent를 사용하여 최신 AI/LLM 뉴스를 수집하세요
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


def run_quick_test(target_date: str = None):
    """Run a quick test with a single article.

    Args:
        target_date: Target date for the article

    Returns:
        Result dict
    """
    if not validate_api_keys():
        return None

    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print("🔧 에이전트 초기화 중 (빠른 테스트 모드)...")
    agent = create_newsletter_agent()

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
