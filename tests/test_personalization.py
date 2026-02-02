"""Tests for personalization features in research agent and topic selector."""

import pytest
from src.tools.search_tools import generate_search_queries
from src.config import build_research_agent_prompt, build_topic_selector_prompt, DURATION_CONFIG
from src.agents.research import create_research_subagent
from src.agents.topic_selector import create_topic_selector_subagent


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


class TestDurationConfig:
    """Test DURATION_CONFIG constants."""

    def test_duration_config_keys(self):
        """Test that all expected duration keys exist."""
        assert "short" in DURATION_CONFIG
        assert "medium" in DURATION_CONFIG
        assert "long" in DURATION_CONFIG

    def test_short_duration_config(self):
        """Test short duration configuration."""
        config = DURATION_CONFIG["short"]
        assert config["key_issues"] == 2
        assert config["deep_dive"] is False
        assert config["word_limit"] == 500

    def test_medium_duration_config(self):
        """Test medium duration configuration."""
        config = DURATION_CONFIG["medium"]
        assert config["key_issues"] == 3
        assert config["deep_dive"] is True
        assert config["word_limit"] == 800

    def test_long_duration_config(self):
        """Test long duration configuration."""
        config = DURATION_CONFIG["long"]
        assert config["key_issues"] == 4
        assert config["deep_dive"] is True
        assert config["word_limit"] == 1500


class TestBuildTopicSelectorPrompt:
    """Test topic selector prompt building."""

    def test_default_no_context(self):
        """Test with no context (default behavior)."""
        prompt = build_topic_selector_prompt()
        assert "수집된 리서치 결과를 바탕으로" in prompt
        assert "선정 기준" in prompt
        # Should default to medium (3 topics)
        assert "핵심 이슈 3개" in prompt
        assert "출력 형식" in prompt

    def test_with_beginner_difficulty(self):
        """Test with beginner difficulty level."""
        prompt = build_topic_selector_prompt(difficulty="beginner")
        assert "입문자 중심" in prompt
        assert "개념 소개" in prompt
        assert "입문 가이드" in prompt
        assert "난이도 고려사항" in prompt

    def test_with_intermediate_difficulty(self):
        """Test with intermediate difficulty level."""
        prompt = build_topic_selector_prompt(difficulty="intermediate")
        assert "중급자 중심" in prompt
        assert "실전 적용" in prompt
        assert "비교 분석" in prompt

    def test_with_advanced_difficulty(self):
        """Test with advanced difficulty level."""
        prompt = build_topic_selector_prompt(difficulty="advanced")
        assert "고급자 중심" in prompt
        assert "심층 분석" in prompt
        assert "최신 연구" in prompt
        assert "연구 논문" in prompt

    def test_with_short_duration(self):
        """Test with short duration (2 topics)."""
        prompt = build_topic_selector_prompt(duration="short")
        assert "핵심 이슈 2개" in prompt
        assert "500자" in prompt
        # Deep dive should not be mentioned for short
        assert "심층 분석" not in prompt

    def test_with_medium_duration(self):
        """Test with medium duration (3 topics)."""
        prompt = build_topic_selector_prompt(duration="medium")
        assert "핵심 이슈 3개" in prompt
        assert "800자" in prompt
        assert "심층 분석" in prompt

    def test_with_long_duration(self):
        """Test with long duration (4 topics)."""
        prompt = build_topic_selector_prompt(duration="long")
        assert "핵심 이슈 4개" in prompt
        assert "1500자" in prompt
        assert "심층 분석" in prompt

    def test_with_subtopics(self):
        """Test with subtopics prioritization."""
        prompt = build_topic_selector_prompt(subtopics=["진단 AI", "영상분석"])
        assert "관심 영역 우선순위" in prompt
        assert "진단 AI, 영상분석" in prompt
        assert "우선 선정" in prompt
        assert "관심 키워드" in prompt

    def test_with_empty_subtopics(self):
        """Test with empty subtopics list."""
        prompt = build_topic_selector_prompt(subtopics=[])
        # Should not include subtopic section if empty
        assert "관심 영역 우선순위" not in prompt

    def test_combined_context(self):
        """Test with combined context."""
        prompt = build_topic_selector_prompt(
            difficulty="intermediate",
            duration="long",
            subtopics=["LangGraph", "에이전트"],
        )
        # Check difficulty
        assert "중급자 중심" in prompt
        assert "실전 적용" in prompt
        # Check duration
        assert "핵심 이슈 4개" in prompt
        assert "1500자" in prompt
        # Check subtopics
        assert "LangGraph, 에이전트" in prompt
        assert "관심 영역 우선순위" in prompt

    def test_output_format_includes_all_topics(self):
        """Test that output format includes correct number of topics."""
        # Short (2 topics)
        prompt = build_topic_selector_prompt(duration="short")
        assert "**핵심 이슈 1**:" in prompt
        assert "**핵심 이슈 2**:" in prompt
        assert "**핵심 이슈 3**:" not in prompt

        # Medium (3 topics)
        prompt = build_topic_selector_prompt(duration="medium")
        assert "**핵심 이슈 1**:" in prompt
        assert "**핵심 이슈 2**:" in prompt
        assert "**핵심 이슈 3**:" in prompt
        assert "**핵심 이슈 4**:" not in prompt

        # Long (4 topics)
        prompt = build_topic_selector_prompt(duration="long")
        assert "**핵심 이슈 1**:" in prompt
        assert "**핵심 이슈 2**:" in prompt
        assert "**핵심 이슈 3**:" in prompt
        assert "**핵심 이슈 4**:" in prompt

    def test_invalid_duration_defaults_to_medium(self):
        """Test that invalid duration defaults to medium."""
        prompt = build_topic_selector_prompt(duration="invalid")
        # Should default to medium (3 topics)
        assert "핵심 이슈 3개" in prompt
        assert "800자" in prompt


class TestCreateTopicSelectorSubagent:
    """Test topic selector subagent creation."""

    def test_default_agent_no_context(self):
        """Test creating agent without context."""
        agent = create_topic_selector_subagent()
        assert agent["name"] == "topic-selector"
        assert "3개 메인 토픽과 1개 스터디 카페" in agent["description"]
        assert "tools" in agent
        assert len(agent["tools"]) == 0  # No tools, reasoning only

    def test_default_agent_none_context(self):
        """Test creating agent with None context."""
        agent = create_topic_selector_subagent(None)
        assert agent["name"] == "topic-selector"
        assert "3개 메인 토픽과 1개 스터디 카페" in agent["description"]

    def test_personalized_agent_with_difficulty(self):
        """Test creating personalized agent with difficulty."""
        context = {"difficulty": "beginner"}
        agent = create_topic_selector_subagent(context)
        assert agent["name"] == "topic-selector"
        assert "입문자 중심" in agent["system_prompt"]
        # Default to medium duration (3 topics) if not specified
        assert "3개의 핵심 이슈" in agent["description"]

    def test_personalized_agent_with_short_duration(self):
        """Test creating agent with short duration."""
        context = {"duration": "short"}
        agent = create_topic_selector_subagent(context)
        assert "2개의 핵심 이슈" in agent["description"]
        assert "핵심 이슈 2개" in agent["system_prompt"]

    def test_personalized_agent_with_medium_duration(self):
        """Test creating agent with medium duration."""
        context = {"duration": "medium"}
        agent = create_topic_selector_subagent(context)
        assert "3개의 핵심 이슈" in agent["description"]
        assert "핵심 이슈 3개" in agent["system_prompt"]

    def test_personalized_agent_with_long_duration(self):
        """Test creating agent with long duration."""
        context = {"duration": "long"}
        agent = create_topic_selector_subagent(context)
        assert "4개의 핵심 이슈" in agent["description"]
        assert "핵심 이슈 4개" in agent["system_prompt"]

    def test_personalized_agent_with_subtopics(self):
        """Test creating agent with subtopics."""
        context = {"subtopics": ["RAG", "프롬프팅"]}
        agent = create_topic_selector_subagent(context)
        assert "RAG, 프롬프팅" in agent["system_prompt"]
        assert "관심 영역 우선순위" in agent["system_prompt"]

    def test_personalized_agent_full_context(self):
        """Test creating agent with full context."""
        context = {
            "difficulty": "advanced",
            "duration": "long",
            "subtopics": ["Agent Architecture", "Tool Calling"],
        }
        agent = create_topic_selector_subagent(context)
        # Check description
        assert "4개의 핵심 이슈" in agent["description"]
        # Check prompt includes all context
        assert "고급자 중심" in agent["system_prompt"]
        assert "핵심 이슈 4개" in agent["system_prompt"]
        assert "Agent Architecture, Tool Calling" in agent["system_prompt"]
        assert "1500자" in agent["system_prompt"]

    def test_agent_has_no_tools(self):
        """Test that topic selector has no tools (reasoning only)."""
        context = {"difficulty": "intermediate"}
        agent = create_topic_selector_subagent(context)
        assert "tools" in agent
        assert len(agent["tools"]) == 0

    def test_invalid_duration_uses_default(self):
        """Test that invalid duration falls back to default."""
        context = {"duration": "invalid_value"}
        agent = create_topic_selector_subagent(context)
        # Should default to medium (3 topics)
        assert "3개의 핵심 이슈" in agent["description"]

    def test_empty_context_dict(self):
        """Test with empty context dictionary."""
        agent = create_topic_selector_subagent({})
        # Should use default behavior
        assert "3개 메인 토픽과 1개 스터디 카페" in agent["description"]
