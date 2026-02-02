"""Comprehensive tests for tone editor personalization."""

import pytest
from .tone_editor import (
    build_personalized_tone_prompt,
    create_tone_editor_agent,
    tone_agent,
)
from ..config import TONE_EDITOR_PROMPT


# =============================================================================
# build_personalized_tone_prompt Tests
# =============================================================================


class TestBuildPersonalizedTonePrompt:
    """Tests for prompt building with personalization."""

    def test_no_personalization_returns_base_prompt(self):
        """Test that no parameters returns base prompt unchanged."""
        result = build_personalized_tone_prompt()
        assert result == TONE_EDITOR_PROMPT

    def test_difficulty_only(self):
        """Test personalization with difficulty only."""
        result = build_personalized_tone_prompt(difficulty="초급")
        assert TONE_EDITOR_PROMPT in result
        assert "난이도별 조정" in result
        assert "초급" in result
        assert "용어 설명 수준" in result

    def test_duration_only(self):
        """Test personalization with duration only."""
        result = build_personalized_tone_prompt(duration="5분")
        assert TONE_EDITOR_PROMPT in result
        assert "분량별 조정" in result
        assert "5분" in result
        assert "섹션 상세도" in result

    def test_both_difficulty_and_duration(self):
        """Test personalization with both difficulty and duration."""
        result = build_personalized_tone_prompt(difficulty="중급", duration="10분")
        assert TONE_EDITOR_PROMPT in result
        assert "난이도별 조정" in result
        assert "분량별 조정" in result
        assert "중급" in result
        assert "10분" in result

    def test_beginner_difficulty_includes_examples(self):
        """Test beginner difficulty includes detailed examples."""
        result = build_personalized_tone_prompt(difficulty="초급")
        assert "모든 기술 용어를 상세히 설명" in result
        assert "RAG(Retrieval-Augmented Generation" in result
        assert "일상적인 비유를 많이 사용" in result

    def test_intermediate_difficulty_includes_examples(self):
        """Test intermediate difficulty includes balanced examples."""
        result = build_personalized_tone_prompt(difficulty="중급")
        assert "핵심 용어만 간단히 설명" in result
        assert "RAG(검색 증강 생성)" in result
        assert "실무 적용에 초점" in result

    def test_advanced_difficulty_includes_examples(self):
        """Test advanced difficulty includes minimal examples."""
        result = build_personalized_tone_prompt(difficulty="고급")
        assert "기술 용어 설명을 최소화" in result
        assert "RAG 아키텍처에서 retriever" in result
        assert "전문적인 내용에 집중" in result

    def test_3min_duration_includes_guidance(self):
        """Test 3min duration includes concise guidance."""
        result = build_personalized_tone_prompt(duration="3분")
        assert "핵심만 간결하게 전달" in result
        assert "예시는 생략" in result

    def test_5min_duration_includes_guidance(self):
        """Test 5min duration includes balanced guidance."""
        result = build_personalized_tone_prompt(duration="5분")
        assert "균형잡힌 분량" in result
        assert "중요한 예시 1개 정도" in result

    def test_10min_duration_includes_guidance(self):
        """Test 10min duration includes detailed guidance."""
        result = build_personalized_tone_prompt(duration="10분")
        assert "상세한 설명" in result
        assert "예시 2개" in result
        assert "코드 스니펫" in result

    def test_15min_duration_includes_guidance(self):
        """Test 15min+ duration includes comprehensive guidance."""
        result = build_personalized_tone_prompt(duration="15분+")
        assert "깊이 있는 분석" in result
        assert "다양한 예시" in result
        assert "종합적으로 설명" in result

    def test_english_difficulty_inputs(self):
        """Test English difficulty inputs are handled."""
        result = build_personalized_tone_prompt(difficulty="beginner")
        assert "난이도별 조정" in result
        assert len(result) > len(TONE_EDITOR_PROMPT)

    def test_english_duration_inputs(self):
        """Test English duration inputs are handled."""
        result = build_personalized_tone_prompt(duration="10min")
        assert "분량별 조정" in result
        assert len(result) > len(TONE_EDITOR_PROMPT)

    def test_custom_base_prompt(self):
        """Test using a custom base prompt."""
        custom_prompt = "Custom tone editor prompt"
        result = build_personalized_tone_prompt(
            difficulty="초급",
            duration="5분",
            base_prompt=custom_prompt
        )
        assert custom_prompt in result
        assert "난이도별 조정" in result
        assert "분량별 조정" in result

    def test_none_values_treated_as_no_personalization(self):
        """Test that None values don't add personalization."""
        result = build_personalized_tone_prompt(difficulty=None, duration=None)
        assert result == TONE_EDITOR_PROMPT

    def test_empty_string_values_treated_as_no_personalization(self):
        """Test that empty strings are treated as no personalization."""
        result = build_personalized_tone_prompt(difficulty="", duration="")
        # Empty strings are falsy in Python, so they're treated like None
        assert result == TONE_EDITOR_PROMPT


# =============================================================================
# create_tone_editor_agent Tests
# =============================================================================


class TestCreateToneEditorAgent:
    """Tests for agent factory function."""

    def test_returns_dict_with_required_keys(self):
        """Test that agent dict has all required keys."""
        agent = create_tone_editor_agent()
        assert "name" in agent
        assert "description" in agent
        assert "system_prompt" in agent
        assert "tools" in agent

    def test_agent_name_is_correct(self):
        """Test agent name is 'tone-editor'."""
        agent = create_tone_editor_agent()
        assert agent["name"] == "tone-editor"

    def test_agent_description_is_korean(self):
        """Test agent description is in Korean."""
        agent = create_tone_editor_agent()
        assert "오토마타" in agent["description"]
        assert "톤앤매너" in agent["description"]

    def test_agent_has_empty_tools_list(self):
        """Test agent has no tools."""
        agent = create_tone_editor_agent()
        assert agent["tools"] == []
        assert isinstance(agent["tools"], list)

    def test_default_agent_has_base_prompt(self):
        """Test agent created with no args has base prompt."""
        agent = create_tone_editor_agent()
        assert agent["system_prompt"] == TONE_EDITOR_PROMPT

    def test_agent_with_difficulty(self):
        """Test agent with difficulty personalization."""
        agent = create_tone_editor_agent(difficulty="초급")
        assert len(agent["system_prompt"]) > len(TONE_EDITOR_PROMPT)
        assert "난이도별 조정" in agent["system_prompt"]

    def test_agent_with_duration(self):
        """Test agent with duration personalization."""
        agent = create_tone_editor_agent(duration="10분")
        assert len(agent["system_prompt"]) > len(TONE_EDITOR_PROMPT)
        assert "분량별 조정" in agent["system_prompt"]

    def test_agent_with_both_parameters(self):
        """Test agent with both difficulty and duration."""
        agent = create_tone_editor_agent(difficulty="고급", duration="15분+")
        assert "난이도별 조정" in agent["system_prompt"]
        assert "분량별 조정" in agent["system_prompt"]
        assert "고급" in agent["system_prompt"]
        assert "15분+" in agent["system_prompt"]

    def test_multiple_agents_are_independent(self):
        """Test that creating multiple agents doesn't cause interference."""
        agent1 = create_tone_editor_agent(difficulty="초급")
        agent2 = create_tone_editor_agent(difficulty="고급")
        agent3 = create_tone_editor_agent()

        assert "초급" in agent1["system_prompt"]
        assert "고급" in agent2["system_prompt"]
        assert agent3["system_prompt"] == TONE_EDITOR_PROMPT


# =============================================================================
# Default tone_agent Tests
# =============================================================================


class TestDefaultToneAgent:
    """Tests for the default exported tone_agent."""

    def test_tone_agent_exists(self):
        """Test that tone_agent is defined."""
        assert tone_agent is not None

    def test_tone_agent_is_dict(self):
        """Test that tone_agent is a dictionary."""
        assert isinstance(tone_agent, dict)

    def test_tone_agent_has_required_keys(self):
        """Test that tone_agent has all required keys."""
        assert "name" in tone_agent
        assert "description" in tone_agent
        assert "system_prompt" in tone_agent
        assert "tools" in tone_agent

    def test_tone_agent_uses_base_prompt(self):
        """Test that default tone_agent uses base prompt."""
        assert tone_agent["system_prompt"] == TONE_EDITOR_PROMPT

    def test_tone_agent_backward_compatibility(self):
        """Test that tone_agent maintains backward compatibility."""
        # The default agent should be identical to calling create_tone_editor_agent()
        new_agent = create_tone_editor_agent()
        assert tone_agent["name"] == new_agent["name"]
        assert tone_agent["description"] == new_agent["description"]
        assert tone_agent["system_prompt"] == new_agent["system_prompt"]
        assert tone_agent["tools"] == new_agent["tools"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for tone editor personalization."""

    def test_all_difficulty_levels(self):
        """Test creating agents for all difficulty levels."""
        difficulties = ["초급", "중급", "고급", "beginner", "intermediate", "advanced"]
        for difficulty in difficulties:
            agent = create_tone_editor_agent(difficulty=difficulty)
            assert "난이도별 조정" in agent["system_prompt"]
            assert agent["name"] == "tone-editor"

    def test_all_duration_levels(self):
        """Test creating agents for all duration levels."""
        durations = ["3분", "5분", "10분", "15분+", "3min", "5min", "10min", "15min+"]
        for duration in durations:
            agent = create_tone_editor_agent(duration=duration)
            assert "분량별 조정" in agent["system_prompt"]
            assert agent["name"] == "tone-editor"

    def test_all_combinations(self):
        """Test creating agents for all difficulty-duration combinations."""
        difficulties = ["초급", "중급", "고급"]
        durations = ["3분", "5분", "10분", "15분+"]

        for difficulty in difficulties:
            for duration in durations:
                agent = create_tone_editor_agent(difficulty=difficulty, duration=duration)
                assert "난이도별 조정" in agent["system_prompt"]
                assert "분량별 조정" in agent["system_prompt"]
                assert difficulty in agent["system_prompt"]
                assert duration in agent["system_prompt"]

    def test_prompt_length_increases_with_personalization(self):
        """Test that personalization increases prompt length."""
        base_agent = create_tone_editor_agent()
        diff_agent = create_tone_editor_agent(difficulty="초급")
        dur_agent = create_tone_editor_agent(duration="10분")
        both_agent = create_tone_editor_agent(difficulty="초급", duration="10분")

        base_len = len(base_agent["system_prompt"])
        diff_len = len(diff_agent["system_prompt"])
        dur_len = len(dur_agent["system_prompt"])
        both_len = len(both_agent["system_prompt"])

        assert diff_len > base_len
        assert dur_len > base_len
        assert both_len > diff_len
        assert both_len > dur_len


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_difficulty_gets_normalized(self):
        """Test invalid difficulty gets normalized to default."""
        agent = create_tone_editor_agent(difficulty="unknown")
        # Should normalize to "intermediate" default
        assert "난이도별 조정" in agent["system_prompt"]

    def test_invalid_duration_gets_normalized(self):
        """Test invalid duration gets normalized to default."""
        agent = create_tone_editor_agent(duration="100min")
        # Should normalize to "5min" default
        assert "분량별 조정" in agent["system_prompt"]

    def test_empty_string_difficulty(self):
        """Test empty string difficulty is treated as no personalization."""
        agent = create_tone_editor_agent(difficulty="")
        # Empty string is falsy, so treated like None
        assert agent["system_prompt"] == TONE_EDITOR_PROMPT

    def test_empty_string_duration(self):
        """Test empty string duration is treated as no personalization."""
        agent = create_tone_editor_agent(duration="")
        # Empty string is falsy, so treated like None
        assert agent["system_prompt"] == TONE_EDITOR_PROMPT

    def test_whitespace_only_inputs(self):
        """Test whitespace-only inputs are handled."""
        agent = create_tone_editor_agent(difficulty="   ", duration="   ")
        assert "난이도별 조정" in agent["system_prompt"]
        assert "분량별 조정" in agent["system_prompt"]

    def test_unicode_in_inputs(self):
        """Test unicode characters in inputs don't break functionality."""
        agent = create_tone_editor_agent(difficulty="초급 ✅", duration="5분 ⏱️")
        assert "난이도별 조정" in agent["system_prompt"]
        assert "분량별 조정" in agent["system_prompt"]

    def test_very_long_input_strings(self):
        """Test very long input strings are handled."""
        long_difficulty = "초급" + "x" * 1000
        long_duration = "5분" + "y" * 1000
        agent = create_tone_editor_agent(difficulty=long_difficulty, duration=long_duration)
        assert "난이도별 조정" in agent["system_prompt"]
        assert "분량별 조정" in agent["system_prompt"]

    def test_special_characters_in_inputs(self):
        """Test special characters in inputs are handled."""
        agent = create_tone_editor_agent(
            difficulty="초급 (beginner level)",
            duration="5분 - 핵심 정리"
        )
        assert "난이도별 조정" in agent["system_prompt"]
        assert "분량별 조정" in agent["system_prompt"]
