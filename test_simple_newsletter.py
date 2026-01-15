#!/usr/bin/env python3
"""Simplified newsletter agent test."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_simple_newsletter():
    """Test a simplified newsletter agent."""
    print("=" * 50)
    print("Simplified Newsletter Agent Test")
    print("=" * 50)

    from deepagents import create_deep_agent
    from src.tools.search_tools import search_ai_news

    # Simple research subagent
    research_subagent = {
        "name": "researcher",
        "description": "AI 뉴스 검색 전문가",
        "system_prompt": "AI 관련 뉴스를 검색하고 요약해주세요.",
        "tools": [search_ai_news],
    }

    # Create simple orchestrator
    agent = create_deep_agent(
        system_prompt="""당신은 뉴스레터 작성 에이전트입니다.

사용자가 요청하면:
1. researcher 서브에이전트를 사용해 AI 뉴스를 검색합니다
2. 검색 결과를 바탕으로 간단한 뉴스 요약을 작성합니다

간단하고 짧게 응답하세요.""",
        subagents=[research_subagent],
    )
    print("✅ Agent created")

    print("\n🔧 Running simple newsletter task...")
    print("   (streaming output)")
    print()

    config = {"configurable": {"thread_id": "test-simple"}}

    final_content = None
    for event in agent.stream(
        {"messages": [{"role": "user", "content": "AI 에이전트 뉴스 1개만 찾아서 한 문장으로 요약해줘"}]},
        config=config
    ):
        # Debug: print all events
        print(f"🔄 Event keys: {list(event.keys())}")

        for key, value in event.items():
            if key == "agent":
                if "messages" in value:
                    for msg in value["messages"]:
                        if hasattr(msg, 'content') and msg.content:
                            final_content = msg.content
                            print(f"📝 Agent: {msg.content[:500]}")
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"🔨 Tool call: {tc.get('name', 'unknown')}")
            elif key == "tools":
                if "messages" in value:
                    for msg in value["messages"]:
                        tool_name = getattr(msg, 'name', 'tool')
                        content = getattr(msg, 'content', '')[:200] if hasattr(msg, 'content') else ''
                        print(f"✅ {tool_name}: {content}...")

        sys.stdout.flush()

    print("\n" + "=" * 50)
    print("Final response:")
    print("=" * 50)
    if final_content:
        print(final_content)
    else:
        print("(No final content captured)")
    print("\n✅ Test completed!")


if __name__ == "__main__":
    try:
        test_simple_newsletter()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
