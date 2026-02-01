"""Comprehensive tests for config normalization functions."""

import pytest
from .config import (
    normalize_difficulty,
    normalize_duration,
    DIFFICULTY_TONE,
    DURATION_TONE,
)


# =============================================================================
# normalize_difficulty Tests
# =============================================================================


class TestNormalizeDifficulty:
    """Tests for difficulty normalization function."""

    def test_korean_beginner_variations(self):
        """Test various Korean beginner inputs."""
        beginner_inputs = [
            "초급",
            "초급 (기본 개념부터)",
            "기본",
            "기본 개념",
            "초급자",
        ]
        for input_text in beginner_inputs:
            assert normalize_difficulty(input_text) == "beginner", f"Failed for: {input_text}"

    def test_english_beginner(self):
        """Test English beginner input."""
        assert normalize_difficulty("beginner") == "beginner"
        assert normalize_difficulty("Beginner") == "beginner"
        assert normalize_difficulty("BEGINNER") == "beginner"

    def test_korean_intermediate_variations(self):
        """Test various Korean intermediate inputs."""
        intermediate_inputs = [
            "중급",
            "중급 (실무 활용)",
            "실무",
            "실무 활용",
            "중급자",
        ]
        for input_text in intermediate_inputs:
            assert normalize_difficulty(input_text) == "intermediate", f"Failed for: {input_text}"

    def test_english_intermediate(self):
        """Test English intermediate input."""
        assert normalize_difficulty("intermediate") == "intermediate"
        assert normalize_difficulty("Intermediate") == "intermediate"
        assert normalize_difficulty("INTERMEDIATE") == "intermediate"

    def test_korean_advanced_variations(self):
        """Test various Korean advanced inputs."""
        advanced_inputs = [
            "고급",
            "고급 (전문가 수준)",
            "전문가",
            "전문가 수준",
            "고급자",
        ]
        for input_text in advanced_inputs:
            assert normalize_difficulty(input_text) == "advanced", f"Failed for: {input_text}"

    def test_english_advanced(self):
        """Test English advanced input."""
        assert normalize_difficulty("advanced") == "advanced"
        assert normalize_difficulty("Advanced") == "advanced"
        assert normalize_difficulty("ADVANCED") == "advanced"

    def test_invalid_input_defaults_to_intermediate(self):
        """Test that invalid inputs default to intermediate."""
        invalid_inputs = [
            "unknown",
            "random",
            "master",
            "expert",
            "",
            "   ",
        ]
        for input_text in invalid_inputs:
            assert normalize_difficulty(input_text) == "intermediate", f"Failed for: {input_text}"

    def test_mixed_case_inputs(self):
        """Test mixed case inputs."""
        assert normalize_difficulty("초급") == "beginner"
        assert normalize_difficulty("BEGINNER") == "beginner"
        assert normalize_difficulty("BeGiNnEr") == "beginner"

    def test_whitespace_handling(self):
        """Test inputs with extra whitespace."""
        assert normalize_difficulty("  초급  ") == "beginner"
        assert normalize_difficulty("중급 ") == "intermediate"
        assert normalize_difficulty(" 고급") == "advanced"


# =============================================================================
# normalize_duration Tests
# =============================================================================


class TestNormalizeDuration:
    """Tests for duration normalization function."""

    def test_korean_3min_variations(self):
        """Test various Korean 3min inputs."""
        three_min_inputs = [
            "3분",
            "3분 (빠른 요약)",
            "빠른",
            "빠른 요약",
            "요약",
        ]
        for input_text in three_min_inputs:
            assert normalize_duration(input_text) == "3min", f"Failed for: {input_text}"

    def test_english_3min(self):
        """Test English 3min input."""
        assert normalize_duration("3min") == "3min"
        assert normalize_duration("3MIN") == "3min"
        assert normalize_duration("3Min") == "3min"

    def test_korean_5min_variations(self):
        """Test various Korean 5min inputs."""
        five_min_inputs = [
            "5분",
            "5분 (핵심 정리)",
            "핵심",
            "핵심 정리",
        ]
        for input_text in five_min_inputs:
            assert normalize_duration(input_text) == "5min", f"Failed for: {input_text}"

    def test_english_5min(self):
        """Test English 5min input."""
        assert normalize_duration("5min") == "5min"
        assert normalize_duration("5MIN") == "5min"
        assert normalize_duration("5Min") == "5min"

    def test_korean_10min_variations(self):
        """Test various Korean 10min inputs."""
        ten_min_inputs = [
            "10분",
            "10분 (상세 설명)",
            "상세",
            "상세 설명",
        ]
        for input_text in ten_min_inputs:
            assert normalize_duration(input_text) == "10min", f"Failed for: {input_text}"

    def test_english_10min(self):
        """Test English 10min input."""
        assert normalize_duration("10min") == "10min"
        assert normalize_duration("10MIN") == "10min"
        assert normalize_duration("10Min") == "10min"

    def test_korean_15min_variations(self):
        """Test various Korean 15min+ inputs."""
        fifteen_min_inputs = [
            "15분",
            "15분+",
            "15분+ (깊이 있는 분석)",
            "깊이",
            "깊이 있는",
            "분석",
        ]
        for input_text in fifteen_min_inputs:
            assert normalize_duration(input_text) == "15min+", f"Failed for: {input_text}"

    def test_english_15min(self):
        """Test English 15min+ input."""
        assert normalize_duration("15min") == "15min+"
        assert normalize_duration("15min+") == "15min+"
        assert normalize_duration("15MIN+") == "15min+"

    def test_invalid_input_defaults_to_5min(self):
        """Test that invalid inputs default to 5min."""
        invalid_inputs = [
            "unknown",
            "random",
            "20min",
            "1hour",
            "",
            "   ",
        ]
        for input_text in invalid_inputs:
            assert normalize_duration(input_text) == "5min", f"Failed for: {input_text}"

    def test_mixed_case_inputs(self):
        """Test mixed case inputs."""
        assert normalize_duration("3분") == "3min"
        assert normalize_duration("3MIN") == "3min"
        assert normalize_duration("3MiN") == "3min"

    def test_whitespace_handling(self):
        """Test inputs with extra whitespace."""
        assert normalize_duration("  3분  ") == "3min"
        assert normalize_duration("5분 ") == "5min"
        assert normalize_duration(" 10분") == "10min"


# =============================================================================
# Configuration Dictionaries Tests
# =============================================================================


class TestDifficultyToneConfig:
    """Tests for DIFFICULTY_TONE configuration."""

    def test_has_all_levels(self):
        """Test that all difficulty levels are defined."""
        assert "beginner" in DIFFICULTY_TONE
        assert "intermediate" in DIFFICULTY_TONE
        assert "advanced" in DIFFICULTY_TONE

    def test_beginner_config_structure(self):
        """Test beginner configuration has required keys."""
        config = DIFFICULTY_TONE["beginner"]
        assert "term_explanation" in config
        assert "analogy_usage" in config
        assert "technical_depth" in config

    def test_intermediate_config_structure(self):
        """Test intermediate configuration has required keys."""
        config = DIFFICULTY_TONE["intermediate"]
        assert "term_explanation" in config
        assert "analogy_usage" in config
        assert "technical_depth" in config

    def test_advanced_config_structure(self):
        """Test advanced configuration has required keys."""
        config = DIFFICULTY_TONE["advanced"]
        assert "term_explanation" in config
        assert "analogy_usage" in config
        assert "technical_depth" in config

    def test_beginner_values(self):
        """Test beginner has appropriate values."""
        config = DIFFICULTY_TONE["beginner"]
        assert config["term_explanation"] == "detailed"
        assert config["analogy_usage"] == "high"
        assert config["technical_depth"] == "low"

    def test_intermediate_values(self):
        """Test intermediate has appropriate values."""
        config = DIFFICULTY_TONE["intermediate"]
        assert config["term_explanation"] == "brief"
        assert config["analogy_usage"] == "medium"
        assert config["technical_depth"] == "medium"

    def test_advanced_values(self):
        """Test advanced has appropriate values."""
        config = DIFFICULTY_TONE["advanced"]
        assert config["term_explanation"] == "minimal"
        assert config["analogy_usage"] == "low"
        assert config["technical_depth"] == "high"


class TestDurationToneConfig:
    """Tests for DURATION_TONE configuration."""

    def test_has_all_durations(self):
        """Test that all duration levels are defined."""
        assert "3min" in DURATION_TONE
        assert "5min" in DURATION_TONE
        assert "10min" in DURATION_TONE
        assert "15min+" in DURATION_TONE

    def test_3min_config_structure(self):
        """Test 3min configuration has required keys."""
        config = DURATION_TONE["3min"]
        assert "section_detail" in config
        assert "examples" in config
        assert "code_snippets" in config

    def test_5min_config_structure(self):
        """Test 5min configuration has required keys."""
        config = DURATION_TONE["5min"]
        assert "section_detail" in config
        assert "examples" in config
        assert "code_snippets" in config

    def test_10min_config_structure(self):
        """Test 10min configuration has required keys."""
        config = DURATION_TONE["10min"]
        assert "section_detail" in config
        assert "examples" in config
        assert "code_snippets" in config

    def test_15min_config_structure(self):
        """Test 15min+ configuration has required keys."""
        config = DURATION_TONE["15min+"]
        assert "section_detail" in config
        assert "examples" in config
        assert "code_snippets" in config

    def test_3min_values(self):
        """Test 3min has appropriate values."""
        config = DURATION_TONE["3min"]
        assert config["section_detail"] == "concise"
        assert config["examples"] == 0
        assert config["code_snippets"] is False

    def test_5min_values(self):
        """Test 5min has appropriate values."""
        config = DURATION_TONE["5min"]
        assert config["section_detail"] == "balanced"
        assert config["examples"] == 1
        assert config["code_snippets"] is False

    def test_10min_values(self):
        """Test 10min has appropriate values."""
        config = DURATION_TONE["10min"]
        assert config["section_detail"] == "detailed"
        assert config["examples"] == 2
        assert config["code_snippets"] is True

    def test_15min_values(self):
        """Test 15min+ has appropriate values."""
        config = DURATION_TONE["15min+"]
        assert config["section_detail"] == "comprehensive"
        assert config["examples"] == 3
        assert config["code_snippets"] is True

    def test_example_counts_are_progressive(self):
        """Test that example counts increase with duration."""
        assert DURATION_TONE["3min"]["examples"] < DURATION_TONE["5min"]["examples"]
        assert DURATION_TONE["5min"]["examples"] < DURATION_TONE["10min"]["examples"]
        assert DURATION_TONE["10min"]["examples"] < DURATION_TONE["15min+"]["examples"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in normalization functions."""

    def test_empty_string_difficulty(self):
        """Test empty string defaults to intermediate."""
        assert normalize_difficulty("") == "intermediate"

    def test_empty_string_duration(self):
        """Test empty string defaults to 5min."""
        assert normalize_duration("") == "5min"

    def test_only_whitespace_difficulty(self):
        """Test whitespace-only string defaults to intermediate."""
        assert normalize_difficulty("   ") == "intermediate"
        assert normalize_difficulty("\t\n") == "intermediate"

    def test_only_whitespace_duration(self):
        """Test whitespace-only string defaults to 5min."""
        assert normalize_duration("   ") == "5min"
        assert normalize_duration("\t\n") == "5min"

    def test_partial_match_difficulty(self):
        """Test partial matches work correctly."""
        assert normalize_difficulty("this is beginner level") == "beginner"
        assert normalize_difficulty("실무 중심 중급") == "intermediate"
        assert normalize_difficulty("전문가용 고급") == "advanced"

    def test_partial_match_duration(self):
        """Test partial matches work correctly."""
        assert normalize_duration("선택: 3분 빠른 요약") == "3min"
        assert normalize_duration("원하는 시간: 5분") == "5min"
        assert normalize_duration("깊이 있게 15분 이상") == "15min+"

    def test_unicode_characters(self):
        """Test handling of special unicode characters."""
        assert normalize_difficulty("초급 ✅") == "beginner"
        assert normalize_duration("5분 ⏱️") == "5min"

    def test_numbers_only(self):
        """Test numbers without 'min' suffix."""
        # Should not match since we look for "3분" or "3min"
        assert normalize_duration("3") == "5min"  # default
        assert normalize_duration("10") == "5min"  # default
