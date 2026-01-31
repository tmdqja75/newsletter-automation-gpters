#!/usr/bin/env python3
"""Test script for personalized research agent with 의료 AI topic."""

from src.tools.search_tools import generate_search_queries
from src.config import build_research_agent_prompt
from src.agents.research import create_research_subagent

print("=" * 60)
print("🧪 Testing Personalized Research Agent: 의료 AI")
print("=" * 60)
print()

# Define user context for medical AI research
user_context = {
    "topic": "의료 AI",
    "topic_description": "의료 진단 및 치료를 돕는 인공지능 시스템",
    "subtopics": ["의료 영상 진단", "질병 예측", "신약 개발"],
    "preferred_sources": ["papers", "news"],
    "goal": "learning",
    "difficulty": "intermediate",
}

print("📋 User Context:")
print("-" * 60)
for key, value in user_context.items():
    print(f"  {key}: {value}")
print()

# Test 1: Generate search queries
print("🔍 Test 1: Generated Search Queries")
print("-" * 60)
queries = generate_search_queries(
    topic=user_context["topic"],
    subtopics=user_context["subtopics"],
    goal=user_context["goal"],
    difficulty=user_context["difficulty"],
)
for i, query in enumerate(queries, 1):
    print(f"  {i}. {query}")
print()

# Test 2: Build research agent prompt
print("📝 Test 2: Research Agent System Prompt")
print("-" * 60)
prompt = build_research_agent_prompt(
    topic=user_context["topic"],
    topic_description=user_context["topic_description"],
    subtopics=user_context["subtopics"],
    preferred_sources=user_context["preferred_sources"],
    goal=user_context["goal"],
    difficulty=user_context["difficulty"],
)
print(prompt)
print()

# Test 3: Create personalized research agent
print("🤖 Test 3: Personalized Research Agent")
print("-" * 60)
agent = create_research_subagent(user_context)
print(f"  Agent name: {agent['name']}")
print(f"  Agent description: {agent['description']}")
print(f"  Number of tools: {len(agent['tools'])}")
print(f"  Tool names: {[tool.__name__ for tool in agent['tools']]}")
print()

# Test 4: Compare with default AI/LLM agent
print("🔄 Test 4: Comparison with Default AI/LLM Agent")
print("-" * 60)
default_agent = create_research_subagent()
print("Default Agent:")
print(f"  Description: {default_agent['description']}")
print()
print("Personalized Agent:")
print(f"  Description: {agent['description']}")
print()

# Test 5: Demonstrate actual search (if API keys are set)
print("🌐 Test 5: Testing Actual Search (Optional)")
print("-" * 60)
import os
if os.getenv("TAVILY_API_KEY"):
    print("  ✅ TAVILY_API_KEY found - running actual search...")
    from src.tools.search_tools import search_ai_news

    # Search for medical AI with preferred domains
    medical_ai_domains = [
        "arxiv.org",
        "nature.com",
        "pubmed.ncbi.nlm.nih.gov",
        "nejm.org",
        "sciencedirect.com",
        "techcrunch.com",
        "theverge.com",
    ]

    print(f"  Searching: {queries[0]}")
    print(f"  Preferred domains: {medical_ai_domains}")
    print()

    result = search_ai_news(
        query=queries[0],
        max_results=3,
        preferred_domains=medical_ai_domains,
    )

    import json
    results = json.loads(result)

    if "error" in results:
        print(f"  ❌ Error: {results['error']}")
    else:
        print(f"  ✅ Found {len(results)} results:")
        for i, item in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    Title: {item.get('title', 'N/A')}")
            print(f"    URL: {item.get('url', 'N/A')}")
            print(f"    Score: {item.get('score', 'N/A')}")
            print(f"    Content: {item.get('content', 'N/A')[:100]}...")
else:
    print("  ⚠️  TAVILY_API_KEY not set - skipping actual search")
    print("  💡 To test actual search, set TAVILY_API_KEY in .env file")
print()

print("=" * 60)
print("✅ All tests completed!")
print("=" * 60)
