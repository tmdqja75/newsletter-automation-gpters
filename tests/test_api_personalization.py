"""Tests for API personalization features (duration extraction)."""

import pytest
from unittest.mock import Mock, patch
from src.api.models import NewsletterContext, UserAnswer
from src.api.newsletter_generator import NewsletterGenerator


class TestExtractResearchContext:
    """Test research context extraction from newsletter context."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the Supabase client to avoid requiring credentials
        with patch("src.api.newsletter_generator.get_supabase_client"):
            self.generator = NewsletterGenerator()
            self.generator.supabase = Mock()  # Mock supabase client

    def test_basic_topic_only(self):
        """Test extraction with topic only."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="AI 에이전트",
            user_answers=[],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "AI 에이전트"
        assert "subtopics" not in research_context
        assert "duration" not in research_context

    def test_with_topic_description(self):
        """Test extraction with topic description."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="블록체인",
            topic_description="탈중앙화 기술과 스마트 컨트랙트",
            user_answers=[],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "블록체인"
        assert research_context["topic_description"] == "탈중앙화 기술과 스마트 컨트랙트"

    def test_extract_subtopics_from_answers(self):
        """Test extracting subtopics from user answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="머신러닝",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="관심 있는 세부 주제는?",
                    question_type="subtopic",
                    answer_value={"values": ["딥러닝", "강화학습"]},
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert "subtopics" in research_context
        assert "딥러닝" in research_context["subtopics"]
        assert "강화학습" in research_context["subtopics"]

    def test_extract_goal_from_answers(self):
        """Test extracting goal from user answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="파이썬",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="학습 목적은?",
                    question_type="goal",
                    answer_value={"value": "learning"},
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["goal"] == "learning"

    def test_extract_difficulty_from_answers(self):
        """Test extracting difficulty from user answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="웹 개발",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="난이도는?",
                    question_type="difficulty",
                    answer_value={"value": "intermediate"},
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["difficulty"] == "intermediate"

    def test_extract_duration_from_time_answers(self):
        """Test extracting duration from time question answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="AI 트렌드",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="읽기 시간은?",
                    question_type="time",
                    answer_value={"value": "short"},
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "short"

    def test_extract_duration_from_text_answer(self):
        """Test extracting duration from text answer."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="클라우드",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="읽기 시간은?",
                    question_type="time",
                    answer_text="medium",
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "medium"

    def test_duration_from_user_preferences(self):
        """Test extracting duration from user preferences when not in answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="데이터 사이언스",
            user_answers=[],
            user_preferences={"preferred_length": "long"},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "long"

    def test_answer_duration_overrides_preferences(self):
        """Test that answer duration takes precedence over preferences."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="사이버보안",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="읽기 시간은?",
                    question_type="time",
                    answer_value={"value": "short"},
                    skipped=False,
                )
            ],
            user_preferences={"preferred_length": "long"},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "short"

    def test_skip_skipped_answers(self):
        """Test that skipped answers are not included."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="게임 개발",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="난이도는?",
                    question_type="difficulty",
                    answer_value={"value": "beginner"},
                    skipped=True,  # Skipped
                ),
                UserAnswer(
                    question_id="q2",
                    question_text="목적은?",
                    question_type="goal",
                    answer_value={"value": "hobby"},
                    skipped=False,
                ),
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert "difficulty" not in research_context
        assert research_context["goal"] == "hobby"

    def test_extract_preferred_sources(self):
        """Test extracting preferred sources from answers."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="양자컴퓨팅",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="선호 출처는?",
                    question_type="source",
                    answer_value={"values": ["papers", "blogs"]},
                    skipped=False,
                )
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert "preferred_sources" in research_context
        assert "papers" in research_context["preferred_sources"]
        assert "blogs" in research_context["preferred_sources"]

    def test_combined_extraction(self):
        """Test extracting multiple fields together."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="DevOps",
            topic_description="CI/CD 및 자동화",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="관심 주제",
                    question_type="subtopic",
                    answer_value={"values": ["Kubernetes", "Docker"]},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q2",
                    question_text="목적",
                    question_type="goal",
                    answer_value={"value": "work"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q3",
                    question_text="난이도",
                    question_type="difficulty",
                    answer_value={"value": "advanced"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q4",
                    question_text="읽기 시간",
                    question_type="time",
                    answer_value={"value": "long"},
                    skipped=False,
                ),
            ],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "DevOps"
        assert research_context["topic_description"] == "CI/CD 및 자동화"
        assert "Kubernetes" in research_context["subtopics"]
        assert "Docker" in research_context["subtopics"]
        assert research_context["goal"] == "work"
        assert research_context["difficulty"] == "advanced"
        assert research_context["duration"] == "long"

    def test_difficulty_from_preferences_fallback(self):
        """Test difficulty fallback to preferences."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="테스트",
            user_answers=[],
            user_preferences={"difficulty": "beginner"},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["difficulty"] == "beginner"

    def test_empty_answers_and_preferences(self):
        """Test with no answers and no preferences."""
        context = NewsletterContext(
            topic_id="topic-1",
            topic_text="최소 컨텍스트",
            user_answers=[],
            user_preferences={},
        )
        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "최소 컨텍스트"
        assert len(research_context) == 2  # topic + topic_description (None)
