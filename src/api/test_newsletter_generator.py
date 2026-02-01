"""Tests for newsletter generator duration extraction."""

import pytest
from .newsletter_generator import NewsletterGenerator
from .models import NewsletterContext, UserAnswer


class TestExtractResearchContext:
    """Tests for _extract_research_context method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = NewsletterGenerator()

    def test_extract_duration_from_answer_value(self):
        """Test extracting duration from answer_value."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_value={"value": "5분 (핵심 정리)"},
                    skipped=False,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "duration" in research_context
        assert research_context["duration"] == "5분 (핵심 정리)"

    def test_extract_duration_from_answer_text(self):
        """Test extracting duration from answer_text."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_text="10분 (상세 설명)",
                    skipped=False,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "duration" in research_context
        assert research_context["duration"] == "10분 (상세 설명)"

    def test_skipped_duration_answer_not_extracted(self):
        """Test that skipped time answers are not extracted."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_value={"value": "5분"},
                    skipped=True,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "duration" not in research_context

    def test_duration_from_user_preferences(self):
        """Test duration extracted from user_preferences."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_preferences={"duration": "15분+"},
        )

        research_context = self.generator._extract_research_context(context)
        assert "duration" in research_context
        assert research_context["duration"] == "15분+"

    def test_duration_answer_overrides_preferences(self):
        """Test that answer value takes precedence over preferences."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_value={"value": "10분"},
                    skipped=False,
                )
            ],
            user_preferences={"duration": "5분"},
        )

        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "10분"

    def test_extract_difficulty_still_works(self):
        """Test that existing difficulty extraction still works."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="어느 정도 수준의 설명을 원하시나요?",
                    question_type="difficulty",
                    answer_value={"value": "중급 (실무 활용)"},
                    skipped=False,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "difficulty" in research_context
        assert research_context["difficulty"] == "중급 (실무 활용)"

    def test_extract_both_difficulty_and_duration(self):
        """Test extracting both difficulty and duration together."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="어느 정도 수준의 설명을 원하시나요?",
                    question_type="difficulty",
                    answer_value={"value": "초급 (기본 개념부터)"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q2",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_value={"value": "3분 (빠른 요약)"},
                    skipped=False,
                ),
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "difficulty" in research_context
        assert "duration" in research_context
        assert research_context["difficulty"] == "초급 (기본 개념부터)"
        assert research_context["duration"] == "3분 (빠른 요약)"

    def test_extract_all_question_types(self):
        """Test extracting all supported question types."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="AI 에이전트",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="목적",
                    question_type="goal",
                    answer_value={"value": "업무 적용"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q2",
                    question_text="난이도",
                    question_type="difficulty",
                    answer_value={"value": "중급"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q3",
                    question_text="시간",
                    question_type="time",
                    answer_value={"value": "10분"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q4",
                    question_text="소스",
                    question_type="source",
                    answer_value={"values": ["공식 문서", "기술 블로그"]},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q5",
                    question_text="관심 범위",
                    question_type="scope",
                    answer_value={"values": ["기술 구현", "오픈소스"]},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q6",
                    question_text="하위 주제",
                    question_type="subtopic",
                    answer_text="LangChain, LangGraph",
                    skipped=False,
                ),
            ],
        )

        research_context = self.generator._extract_research_context(context)

        # Check all fields are extracted
        assert research_context["topic"] == "AI 에이전트"
        assert research_context["goal"] == "업무 적용"
        assert research_context["difficulty"] == "중급"
        assert research_context["duration"] == "10분"
        assert "공식 문서" in research_context["preferred_sources"]
        assert "기술 블로그" in research_context["preferred_sources"]
        assert "LangChain, LangGraph" in research_context["subtopics"]

    def test_no_duration_answer_no_duration_in_context(self):
        """Test that absence of duration answer results in no duration key."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="난이도",
                    question_type="difficulty",
                    answer_value={"value": "초급"},
                    skipped=False,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert "difficulty" in research_context
        assert "duration" not in research_context

    def test_multiple_time_answers_uses_last(self):
        """Test that multiple time answers uses the last one."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="시간1",
                    question_type="time",
                    answer_value={"value": "3분"},
                    skipped=False,
                ),
                UserAnswer(
                    question_id="q2",
                    question_text="시간2",
                    question_type="time",
                    answer_value={"value": "10분"},
                    skipped=False,
                ),
            ],
        )

        research_context = self.generator._extract_research_context(context)
        # Should use the last value encountered
        assert research_context["duration"] == "10분"

    def test_duration_text_is_lowercased(self):
        """Test that duration text answer is lowercased."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="시간",
                    question_type="time",
                    answer_text="10MIN",
                    skipped=False,
                )
            ],
        )

        research_context = self.generator._extract_research_context(context)
        assert research_context["duration"] == "10min"

    def test_empty_user_answers_list(self):
        """Test extraction with empty user answers list."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test Topic",
            user_answers=[],
        )

        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "Test Topic"
        assert "duration" not in research_context
        assert "difficulty" not in research_context

    def test_topic_description_included(self):
        """Test that topic description is included in context."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="AI 에이전트",
            topic_description="최신 AI 에이전트 기술 동향",
            user_answers=[],
        )

        research_context = self.generator._extract_research_context(context)
        assert research_context["topic"] == "AI 에이전트"
        assert research_context["topic_description"] == "최신 AI 에이전트 기술 동향"


class TestDurationIntegration:
    """Integration tests for duration in the full pipeline."""

    def test_duration_extraction_matches_default_questions(self):
        """Test that duration extraction works with default question format."""
        # This mirrors the actual question format from default-questions.ts
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="AI 에이전트 최신 동향",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                    question_type="time",
                    answer_value={"value": "5분 (핵심 정리)"},
                    skipped=False,
                )
            ],
        )

        generator = NewsletterGenerator()
        research_context = generator._extract_research_context(context)

        assert "duration" in research_context
        assert "5분" in research_context["duration"]

    def test_all_duration_options_from_default_questions(self):
        """Test all duration options from default questions."""
        duration_options = [
            "3분 (빠른 요약)",
            "5분 (핵심 정리)",
            "10분 (상세 설명)",
            "15분+ (깊이 있는 분석)",
        ]

        generator = NewsletterGenerator()

        for option in duration_options:
            context = NewsletterContext(
                topic_id="topic-123",
                topic_text="Test",
                user_answers=[
                    UserAnswer(
                        question_id="q1",
                        question_text="뉴스레터 분량은 어느 정도가 좋을까요?",
                        question_type="time",
                        answer_value={"value": option},
                        skipped=False,
                    )
                ],
            )

            research_context = generator._extract_research_context(context)
            assert research_context["duration"] == option
