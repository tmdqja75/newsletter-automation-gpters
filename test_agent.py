#!/usr/bin/env python3
"""Simple test script to verify deepagents API."""

import os
from dotenv import load_dotenv

load_dotenv()

def test_basic_agent():
    """Test basic agent creation and invocation."""
    print("=" * 50)
    print("Test 1: Basic Agent")
    print("=" * 50)

    from deepagents import create_deep_agent

    agent = create_deep_agent(
        system_prompt="You are a helpful assistant. Respond briefly.",
    )
    print("✅ Basic agent created")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Say 'Hello' in Korean."}]},
        config={"configurable": {"thread_id": "test1"}}
    )
    last_msg = result["messages"][-1]
    print(f"✅ Response: {last_msg.content[:100]}...")
    return True


def test_agent_with_tools():
    """Test agent with custom tools."""
    print("\n" + "=" * 50)
    print("Test 2: Agent with Tools")
    print("=" * 50)

    from deepagents import create_deep_agent

    def get_current_time() -> str:
        """Get the current time."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    agent = create_deep_agent(
        system_prompt="You are a helpful assistant. Use tools when needed.",
        tools=[get_current_time],
    )
    print("✅ Agent with tools created")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What time is it now?"}]},
        config={"configurable": {"thread_id": "test2"}}
    )
    last_msg = result["messages"][-1]
    print(f"✅ Response: {last_msg.content[:100]}...")
    return True


def test_agent_with_subagents():
    """Test agent with subagents."""
    print("\n" + "=" * 50)
    print("Test 3: Agent with Subagents")
    print("=" * 50)

    from deepagents import create_deep_agent

    research_subagent = {
        "name": "researcher",
        "description": "A research specialist that can search for information.",
        "system_prompt": "You are a research expert. Provide brief, factual answers.",
        "tools": [],
    }

    agent = create_deep_agent(
        system_prompt="You are an orchestrator. Delegate research tasks to the researcher subagent.",
        subagents=[research_subagent],
    )
    print("✅ Agent with subagents created")

    print("🔧 Running invoke (this may take a moment)...")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Tell me briefly about Python."}]},
        config={"configurable": {"thread_id": "test3"}}
    )
    last_msg = result["messages"][-1]
    print(f"✅ Response: {last_msg.content[:200]}...")
    return True


def test_newsletter_agent():
    """Test the actual newsletter agent."""
    print("\n" + "=" * 50)
    print("Test 4: Newsletter Agent (Simplified)")
    print("=" * 50)

    from deepagents import create_deep_agent
    from src.tools.search_tools import search_ai_news, search_hackernews

    research_subagent = {
        "name": "research-agent",
        "description": "AI/LLM 뉴스 리서치 전문가",
        "system_prompt": "최신 AI 뉴스를 간략히 요약해주세요.",
        "tools": [search_ai_news],
    }

    agent = create_deep_agent(
        system_prompt="뉴스레터 작성을 위한 오케스트레이터입니다.",
        subagents=[research_subagent],
    )
    print("✅ Newsletter agent created")

    print("🔧 Running invoke with research task...")
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "AI 에이전트 관련 최신 뉴스 1개만 찾아줘."}]},
        config={"configurable": {"thread_id": "test4"}}
    )
    last_msg = result["messages"][-1]
    print(f"✅ Response: {last_msg.content[:300]}...")
    return True


if __name__ == "__main__":
    try:
        test_basic_agent()
        test_agent_with_tools()
        test_agent_with_subagents()
        test_newsletter_agent()
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
