"""Tests for personalization features in research agent."""

import pytest
from src.tools.search_tools import generate_search_queries
from src.config import build_research_agent_prompt
from src.agents.research import create_research_subagent


class TestGenerateSearchQueries:
    """Test query generation with user context."""

    def test_basic_topic_only(self):
        """Test with topic only."""
        queries = generate_search_queries("의료 AI")
        assert "의료 AI" in queries
        assert len(queries) >= 1

    def test_with_subtopics(self):
        """Test with subtopics."""
        queries = generate_search_queries(
            topic="의료 AI", subtopics=["진단", "영상분석"]
        )
        assert "의료 AI" in queries
        assert "의료 AI 진단" in queries
        assert "의료 AI 영상분석" in queries

    def test_with_learning_goal(self):
        """Test with learning goal."""
        queries = generate_search_queries(topic="블록체인", goal="learning")
        assert "블록체인" in queries
        # Should include learning-specific modifier
        assert any("tutorial" in q or "introduction" in q or "guide" in q for q in queries)

    def test_with_work_goal(self):
        """Test with work goal."""
        queries = generate_search_queries(topic="머신러닝", goal="work")
        assert any(
            "implementation" in q or "case study" in q or "best practices" in q
            for q in queries
        )

    def test_with_business_goal(self):
        """Test with business goal."""
        queries = generate_search_queries(topic="AI 시장", goal="business")
        assert any("market analysis" in q or "trends" in q or "industry report" in q for q in queries)

    def test_with_hobby_goal(self):
        """Test with hobby goal."""
        queries = generate_search_queries(topic="게임 개발", goal="hobby")
        assert any("getting started" in q or "examples" in q or "projects" in q for q in queries)

    def test_with_beginner_difficulty(self):
        """Test with beginner difficulty."""
        queries = generate_search_queries(topic="파이썬", difficulty="beginner")
        assert any("introduction" in q for q in queries)

    def test_with_intermediate_difficulty(self):
        """Test with intermediate difficulty (no modifier added)."""
        queries = generate_search_queries(topic="자바", difficulty="intermediate")
        # Intermediate shouldn't add extra difficulty modifier
        assert not any("advanced techniques" in q or "introduction" in q for q in queries)

    def test_with_advanced_difficulty(self):
        """Test with advanced difficulty."""
        queries = generate_search_queries(topic="양자컴퓨팅", difficulty="advanced")
        assert any("research papers" in q for q in queries)

    def test_combined_context(self):
        """Test with combined context."""
        queries = generate_search_queries(
            topic="웹 개발",
            subtopics=["React", "Node.js"],
            goal="work",
            difficulty="intermediate",
        )
        assert "웹 개발" in queries
        assert "웹 개발 React" in queries
        assert "웹 개발 Node.js" in queries
        assert any("implementation" in q or "case study" in q for q in queries)


class TestBuildResearchAgentPrompt:
    """Test research agent prompt building."""

    def test_basic_topic_only(self):
        """Test with topic only."""
        prompt = build_research_agent_prompt(topic="AI 에이전트")
        assert "AI 에이전트" in prompt
        assert "**주제**: AI 에이전트" in prompt
        assert "리서치 전문가" in prompt

    def test_with_topic_description(self):
        """Test with topic description."""
        prompt = build_research_agent_prompt(
            topic="의료 AI", topic_description="의료 진단 및 치료를 돕는 AI 시스템"
        )
        assert "의료 AI" in prompt
        assert "의료 진단 및 치료를 돕는 AI 시스템" in prompt
        assert "**상세 설명**:" in prompt

    def test_with_subtopics(self):
        """Test with subtopics."""
        prompt = build_research_agent_prompt(
            topic="블록체인", subtopics=["스마트 컨트랙트", "DeFi"]
        )
        assert "**관심 영역**: 스마트 컨트랙트, DeFi" in prompt

    def test_with_preferred_sources(self):
        """Test with preferred sources."""
        prompt = build_research_agent_prompt(
            topic="머신러닝", preferred_sources=["papers", "blogs"]
        )
        assert "연구 논문" in prompt or "기술 블로그" in prompt
        assert "우선적으로 검색" in prompt

    def test_with_goal(self):
        """Test with different goals."""
        # Learning goal
        prompt = build_research_agent_prompt(topic="파이썬", goal="learning")
        assert "**목적**: 학습 및 이해" in prompt

        # Work goal
        prompt = build_research_agent_prompt(topic="자바", goal="work")
        assert "**목적**: 업무/프로젝트 적용" in prompt

        # Business goal
        prompt = build_research_agent_prompt(topic="AI 시장", goal="business")
        assert "**목적**: 비즈니스 분석" in prompt

        # Hobby goal
        prompt = build_research_agent_prompt(topic="게임 개발", goal="hobby")
        assert "**목적**: 취미/개인 프로젝트" in prompt

    def test_with_difficulty(self):
        """Test with difficulty levels."""
        # Beginner
        prompt = build_research_agent_prompt(topic="코딩", difficulty="beginner")
        assert "**난이도**: 입문" in prompt
        assert "기초 개념 중심" in prompt

        # Intermediate
        prompt = build_research_agent_prompt(topic="웹 개발", difficulty="intermediate")
        assert "**난이도**: 중급" in prompt
        assert "실무 적용 중심" in prompt

        # Advanced
        prompt = build_research_agent_prompt(topic="양자컴퓨팅", difficulty="advanced")
        assert "**난이도**: 고급" in prompt
        assert "최신 연구 및 심화 내용" in prompt

    def test_output_format_included(self):
        """Test that output format instructions are included."""
        prompt = build_research_agent_prompt(topic="테스트")
        assert "출력 형식" in prompt
        assert "제목" in prompt
        assert "요약" in prompt
        assert "출처 URL" in prompt

    def test_combined_context(self):
        """Test with full context."""
        prompt = build_research_agent_prompt(
            topic="클라우드 컴퓨팅",
            topic_description="AWS, GCP, Azure 등 클라우드 플랫폼 기술",
            subtopics=["서버리스", "컨테이너"],
            preferred_sources=["docs", "blogs"],
            goal="work",
            difficulty="intermediate",
        )
        assert "클라우드 컴퓨팅" in prompt
        assert "AWS, GCP, Azure" in prompt
        assert "서버리스, 컨테이너" in prompt
        assert "**목적**: 업무/프로젝트 적용" in prompt
        assert "**난이도**: 중급" in prompt


class TestCreateResearchSubagent:
    """Test research subagent creation."""

    def test_default_agent_no_context(self):
        """Test creating agent without context (AI/LLM default)."""
        agent = create_research_subagent()
        assert agent["name"] == "research-agent"
        assert "AI/LLM" in agent["description"]
        assert "tools" in agent
        assert len(agent["tools"]) == 3  # search_ai_news, search_hackernews, fetch_article_content

    def test_default_agent_none_context(self):
        """Test creating agent with None context."""
        agent = create_research_subagent(None)
        assert agent["name"] == "research-agent"
        assert "AI/LLM" in agent["description"]

    def test_personalized_agent_with_topic(self):
        """Test creating personalized agent with topic."""
        context = {"topic": "의료 AI"}
        agent = create_research_subagent(context)
        assert agent["name"] == "research-agent"
        assert "의료 AI" in agent["description"]
        assert "의료 AI" in agent["system_prompt"]

    def test_personalized_agent_full_context(self):
        """Test creating agent with full context."""
        context = {
            "topic": "블록체인",
            "topic_description": "탈중앙화 기술",
            "subtopics": ["스마트 컨트랙트", "NFT"],
            "preferred_sources": ["papers", "news"],
            "goal": "learning",
            "difficulty": "beginner",
        }
        agent = create_research_subagent(context)
        assert "블록체인" in agent["description"]
        assert "블록체인" in agent["system_prompt"]
        assert "탈중앙화 기술" in agent["system_prompt"]
        assert "스마트 컨트랙트, NFT" in agent["system_prompt"]

    def test_agent_has_required_tools(self):
        """Test that agent always has required tools."""
        context = {"topic": "테스트"}
        agent = create_research_subagent(context)
        assert "tools" in agent
        assert len(agent["tools"]) == 3
        # Verify tool names by checking function names
        tool_names = [tool.__name__ for tool in agent["tools"]]
        assert "search_ai_news" in tool_names
        assert "search_hackernews" in tool_names
        assert "fetch_article_content" in tool_names
