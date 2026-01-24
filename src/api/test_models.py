"""Comprehensive tests for Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from .models import (
    GenerationRequest,
    UserAnswer,
    NewsletterContext,
    ProgressUpdate,
    CoreIssue,
    DeepDive,
    Source,
    NewsletterContent,
    NewsletterRequestResponse,
    NewsletterStatusResponse,
    NewsletterResponse,
)


# =============================================================================
# GenerationRequest Tests
# =============================================================================


class TestGenerationRequest:
    """Tests for GenerationRequest model."""

    def test_valid_generation_request(self):
        """Test valid generation request creation."""
        request = GenerationRequest(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            topic_id="987fcdeb-51a2-43b1-89ab-123456789012",
        )
        assert request.user_id == "123e4567-e89b-12d3-a456-426614174000"
        assert request.topic_id == "987fcdeb-51a2-43b1-89ab-123456789012"

    def test_missing_user_id(self):
        """Test that missing user_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(topic_id="987fcdeb-51a2-43b1-89ab-123456789012")
        assert "user_id" in str(exc_info.value)

    def test_missing_topic_id(self):
        """Test that missing topic_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(user_id="123e4567-e89b-12d3-a456-426614174000")
        assert "topic_id" in str(exc_info.value)

    def test_empty_string_user_id(self):
        """Test that empty string user_id is allowed (validation in app layer)."""
        request = GenerationRequest(
            user_id="", topic_id="987fcdeb-51a2-43b1-89ab-123456789012"
        )
        assert request.user_id == ""


# =============================================================================
# UserAnswer Tests
# =============================================================================


class TestUserAnswer:
    """Tests for UserAnswer model."""

    def test_valid_user_answer_with_text(self):
        """Test user answer with text response."""
        answer = UserAnswer(
            question_id="q1",
            question_text="What is your learning goal?",
            question_type="goal",
            answer_text="Learn to build AI agents",
            skipped=False,
        )
        assert answer.question_id == "q1"
        assert answer.question_text == "What is your learning goal?"
        assert answer.question_type == "goal"
        assert answer.answer_text == "Learn to build AI agents"
        assert answer.answer_value is None
        assert answer.skipped is False

    def test_valid_user_answer_with_value(self):
        """Test user answer with structured value (e.g., radio/checkbox)."""
        answer = UserAnswer(
            question_id="q2",
            question_text="What is your difficulty level?",
            question_type="difficulty",
            answer_value={"level": "intermediate"},
            skipped=False,
        )
        assert answer.answer_value == {"level": "intermediate"}
        assert answer.answer_text is None

    def test_skipped_answer(self):
        """Test skipped answer."""
        answer = UserAnswer(
            question_id="q3",
            question_text="Any specific subtopics?",
            question_type="subtopic",
            skipped=True,
        )
        assert answer.skipped is True
        assert answer.answer_text is None
        assert answer.answer_value is None

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            UserAnswer(question_id="q1")
        assert "question_text" in str(exc_info.value)
        assert "question_type" in str(exc_info.value)


# =============================================================================
# NewsletterContext Tests
# =============================================================================


class TestNewsletterContext:
    """Tests for NewsletterContext model."""

    def test_valid_newsletter_context_minimal(self):
        """Test minimal valid newsletter context."""
        context = NewsletterContext(
            topic_id="topic-123", topic_text="AI Agent Architecture"
        )
        assert context.topic_id == "topic-123"
        assert context.topic_text == "AI Agent Architecture"
        assert context.topic_description is None
        assert context.user_answers == []
        assert context.user_preferences == {}

    def test_valid_newsletter_context_complete(self):
        """Test complete newsletter context with all fields."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="AI Agent Architecture",
            topic_description="Deep dive into agent systems",
            user_answers=[
                UserAnswer(
                    question_id="q1",
                    question_text="Goal?",
                    question_type="goal",
                    answer_text="Learn",
                )
            ],
            user_preferences={"difficulty": "intermediate", "length": "long"},
        )
        assert context.topic_description == "Deep dive into agent systems"
        assert len(context.user_answers) == 1
        assert context.user_preferences["difficulty"] == "intermediate"

    def test_empty_user_answers_list(self):
        """Test that empty user_answers list is valid."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="AI Agent Architecture",
            user_answers=[],
        )
        assert context.user_answers == []

    def test_missing_required_fields(self):
        """Test that missing topic_id or topic_text raises error."""
        with pytest.raises(ValidationError) as exc_info:
            NewsletterContext(topic_text="Test")
        assert "topic_id" in str(exc_info.value)


# =============================================================================
# ProgressUpdate Tests
# =============================================================================


class TestProgressUpdate:
    """Tests for ProgressUpdate model."""

    def test_valid_progress_update(self):
        """Test valid progress update."""
        progress = ProgressUpdate(
            step="research",
            progress=25,
            message="최신 AI 뉴스를 검색하고 있습니다...",
            details={"articles_found": 15},
        )
        assert progress.step == "research"
        assert progress.progress == 25
        assert progress.message == "최신 AI 뉴스를 검색하고 있습니다..."
        assert progress.details["articles_found"] == 15

    def test_progress_zero(self):
        """Test progress can be 0."""
        progress = ProgressUpdate(step="init", progress=0, message="시작 중...")
        assert progress.progress == 0

    def test_progress_hundred(self):
        """Test progress can be 100."""
        progress = ProgressUpdate(step="complete", progress=100, message="완료!")
        assert progress.progress == 100

    def test_invalid_progress_negative(self):
        """Test that negative progress raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ProgressUpdate(step="error", progress=-1, message="Error")
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_invalid_progress_over_hundred(self):
        """Test that progress > 100 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ProgressUpdate(step="error", progress=101, message="Error")
        assert "less than or equal to 100" in str(exc_info.value)

    def test_optional_details(self):
        """Test that details field is optional."""
        progress = ProgressUpdate(step="writing", progress=50, message="작성 중...")
        assert progress.details is None


# =============================================================================
# CoreIssue Tests
# =============================================================================


class TestCoreIssue:
    """Tests for CoreIssue model."""

    def test_valid_core_issue_with_links(self):
        """Test valid core issue with links."""
        issue = CoreIssue(
            title="Claude Opus 4.5 출시",
            summary="Anthropic이 최신 모델 Claude Opus 4.5를 공개했습니다.",
            links=[
                {"url": "https://anthropic.com", "title": "Anthropic Blog"},
                {"url": "https://techcrunch.com", "title": "TechCrunch Article"},
            ],
        )
        assert issue.title == "Claude Opus 4.5 출시"
        assert len(issue.links) == 2
        assert issue.links[0]["url"] == "https://anthropic.com"

    def test_valid_core_issue_no_links(self):
        """Test valid core issue without links."""
        issue = CoreIssue(
            title="AI 에이전트 트렌드", summary="2026년 주요 트렌드 분석"
        )
        assert issue.links == []

    def test_missing_required_fields(self):
        """Test that missing title or summary raises error."""
        with pytest.raises(ValidationError) as exc_info:
            CoreIssue(title="Title only")
        assert "summary" in str(exc_info.value)


# =============================================================================
# DeepDive Tests
# =============================================================================


class TestDeepDive:
    """Tests for DeepDive model."""

    def test_valid_deep_dive_with_readings(self):
        """Test valid deep dive with additional readings."""
        deep_dive = DeepDive(
            title="AI 에이전트 아키텍처 심층 분석",
            content="장문의 분석 내용...",
            additional_readings=[
                {
                    "url": "https://example.com/paper",
                    "title": "Research Paper",
                    "description": "Key findings on agent architecture",
                }
            ],
        )
        assert deep_dive.title == "AI 에이전트 아키텍처 심층 분석"
        assert len(deep_dive.additional_readings) == 1

    def test_valid_deep_dive_no_readings(self):
        """Test valid deep dive without additional readings."""
        deep_dive = DeepDive(title="Deep Dive Topic", content="Content here")
        assert deep_dive.additional_readings == []

    def test_missing_required_fields(self):
        """Test that missing title or content raises error."""
        with pytest.raises(ValidationError) as exc_info:
            DeepDive(content="Content only")
        assert "title" in str(exc_info.value)


# =============================================================================
# Source Tests
# =============================================================================


class TestSource:
    """Tests for Source model."""

    def test_valid_source(self):
        """Test valid source creation."""
        source = Source(
            url="https://anthropic.com/blog/claude-opus-4-5",
            title="Introducing Claude Opus 4.5",
            domain="anthropic.com",
            accessed_at="2026-01-24T10:30:00Z",
        )
        assert source.url == "https://anthropic.com/blog/claude-opus-4-5"
        assert source.title == "Introducing Claude Opus 4.5"
        assert source.domain == "anthropic.com"
        assert source.accessed_at == "2026-01-24T10:30:00Z"

    def test_missing_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            Source(url="https://example.com", title="Title", domain="example.com")
        assert "accessed_at" in str(exc_info.value)


# =============================================================================
# NewsletterContent Tests
# =============================================================================


class TestNewsletterContent:
    """Tests for NewsletterContent model."""

    def test_valid_newsletter_content_minimal(self):
        """Test valid newsletter content with minimal required fields."""
        content = NewsletterContent(
            title="AI 뉴스레터 2026년 1월 24일",
            tldr="이번 주 주요 AI 소식:\n- Claude Opus 4.5 출시\n- Agent 시스템 발전",
            core_issues=[
                CoreIssue(title="Issue 1", summary="Summary 1"),
                CoreIssue(title="Issue 2", summary="Summary 2"),
                CoreIssue(title="Issue 3", summary="Summary 3"),
            ],
            deep_dive=DeepDive(title="Deep Dive", content="Long content..."),
            sources=[
                Source(
                    url="https://example.com",
                    title="Source 1",
                    domain="example.com",
                    accessed_at="2026-01-24T10:00:00Z",
                )
            ],
        )
        assert content.title == "AI 뉴스레터 2026년 1월 24일"
        assert len(content.core_issues) == 3
        assert content.word_count is None
        assert content.estimated_reading_time is None

    def test_valid_newsletter_content_complete(self):
        """Test valid newsletter content with all optional fields."""
        content = NewsletterContent(
            title="AI 뉴스레터 2026년 1월 24일",
            tldr="이번 주 주요 AI 소식",
            core_issues=[
                CoreIssue(title=f"Issue {i}", summary=f"Summary {i}")
                for i in range(4)
            ],
            deep_dive=DeepDive(title="Deep Dive", content="Content"),
            next_questions=["What about X?", "How does Y work?"],
            sources=[
                Source(
                    url=f"https://example{i}.com",
                    title=f"Source {i}",
                    domain=f"example{i}.com",
                    accessed_at="2026-01-24T10:00:00Z",
                )
                for i in range(3)
            ],
            word_count=1500,
            estimated_reading_time=7,
        )
        assert len(content.core_issues) == 4
        assert len(content.next_questions) == 2
        assert len(content.sources) == 3
        assert content.word_count == 1500
        assert content.estimated_reading_time == 7

    def test_too_few_core_issues(self):
        """Test that less than 3 core issues raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NewsletterContent(
                title="Test",
                tldr="Test",
                core_issues=[
                    CoreIssue(title="Issue 1", summary="Summary 1"),
                    CoreIssue(title="Issue 2", summary="Summary 2"),
                ],
                deep_dive=DeepDive(title="Deep", content="Content"),
                sources=[
                    Source(
                        url="https://example.com",
                        title="Source",
                        domain="example.com",
                        accessed_at="2026-01-24T10:00:00Z",
                    )
                ],
            )
        assert "at least 3 items" in str(exc_info.value).lower()

    def test_too_many_core_issues(self):
        """Test that more than 5 core issues raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NewsletterContent(
                title="Test",
                tldr="Test",
                core_issues=[
                    CoreIssue(title=f"Issue {i}", summary=f"Summary {i}")
                    for i in range(6)
                ],
                deep_dive=DeepDive(title="Deep", content="Content"),
                sources=[
                    Source(
                        url="https://example.com",
                        title="Source",
                        domain="example.com",
                        accessed_at="2026-01-24T10:00:00Z",
                    )
                ],
            )
        assert "at most 5 items" in str(exc_info.value).lower()

    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            NewsletterContent(
                title="Test",
                tldr="Test",
            )
        assert "core_issues" in str(exc_info.value)
        assert "deep_dive" in str(exc_info.value)
        assert "sources" in str(exc_info.value)


# =============================================================================
# NewsletterRequestResponse Tests
# =============================================================================


class TestNewsletterRequestResponse:
    """Tests for NewsletterRequestResponse model."""

    def test_valid_request_response(self):
        """Test valid newsletter request response."""
        response = NewsletterRequestResponse(
            request_id="req-123",
            status="pending",
            message="뉴스레터 생성 요청이 접수되었습니다.",
        )
        assert response.request_id == "req-123"
        assert response.status == "pending"
        assert response.message == "뉴스레터 생성 요청이 접수되었습니다."

    def test_all_valid_statuses(self):
        """Test all valid status values."""
        statuses = ["pending", "processing", "completed", "failed"]
        for status in statuses:
            response = NewsletterRequestResponse(
                request_id="req-123", status=status, message="Test"
            )
            assert response.status == status


# =============================================================================
# NewsletterStatusResponse Tests
# =============================================================================


class TestNewsletterStatusResponse:
    """Tests for NewsletterStatusResponse model."""

    def test_valid_status_response_minimal(self):
        """Test minimal valid status response."""
        response = NewsletterStatusResponse(request_id="req-123", status="pending")
        assert response.request_id == "req-123"
        assert response.status == "pending"
        assert response.progress is None
        assert response.message is None
        assert response.newsletter_id is None

    def test_valid_status_response_complete(self):
        """Test complete status response with all fields."""
        now = datetime.utcnow()
        response = NewsletterStatusResponse(
            request_id="req-123",
            status="completed",
            progress=100,
            message="완료되었습니다",
            newsletter_id="news-456",
            error_message=None,
            processing_started_at=now,
            processing_completed_at=now,
        )
        assert response.status == "completed"
        assert response.progress == 100
        assert response.newsletter_id == "news-456"
        assert response.processing_started_at == now

    def test_failed_status_with_error(self):
        """Test failed status with error message."""
        response = NewsletterStatusResponse(
            request_id="req-123",
            status="failed",
            error_message="API 요청 실패",
        )
        assert response.status == "failed"
        assert response.error_message == "API 요청 실패"


# =============================================================================
# NewsletterResponse Tests
# =============================================================================


class TestNewsletterResponse:
    """Tests for NewsletterResponse model."""

    def test_valid_newsletter_response(self):
        """Test valid newsletter response."""
        now = datetime.utcnow()
        content = NewsletterContent(
            title="AI 뉴스레터",
            tldr="요약",
            core_issues=[
                CoreIssue(title=f"Issue {i}", summary=f"Summary {i}")
                for i in range(3)
            ],
            deep_dive=DeepDive(title="Deep", content="Content"),
            sources=[
                Source(
                    url="https://example.com",
                    title="Source",
                    domain="example.com",
                    accessed_at="2026-01-24T10:00:00Z",
                )
            ],
        )
        response = NewsletterResponse(
            id="news-123",
            request_id="req-456",
            user_id="user-789",
            topic_id="topic-012",
            content=content,
            is_published=False,
            created_at=now,
        )
        assert response.id == "news-123"
        assert response.request_id == "req-456"
        assert response.is_published is False
        assert response.published_at is None

    def test_published_newsletter_response(self):
        """Test published newsletter response."""
        now = datetime.utcnow()
        content = NewsletterContent(
            title="AI 뉴스레터",
            tldr="요약",
            core_issues=[
                CoreIssue(title=f"Issue {i}", summary=f"Summary {i}")
                for i in range(3)
            ],
            deep_dive=DeepDive(title="Deep", content="Content"),
            sources=[
                Source(
                    url="https://example.com",
                    title="Source",
                    domain="example.com",
                    accessed_at="2026-01-24T10:00:00Z",
                )
            ],
        )
        response = NewsletterResponse(
            id="news-123",
            request_id="req-456",
            user_id="user-789",
            topic_id="topic-012",
            content=content,
            published_at=now,
            is_published=True,
            created_at=now,
        )
        assert response.is_published is True
        assert response.published_at == now


# =============================================================================
# Edge Cases and Invalid Inputs
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and invalid inputs across models."""

    def test_empty_strings_in_core_issue(self):
        """Test that empty strings are allowed (app-level validation)."""
        issue = CoreIssue(title="", summary="")
        assert issue.title == ""
        assert issue.summary == ""

    def test_very_long_strings(self):
        """Test that very long strings are accepted."""
        long_text = "A" * 10000
        issue = CoreIssue(title=long_text, summary=long_text)
        assert len(issue.title) == 10000

    def test_unicode_characters(self):
        """Test that unicode characters are properly handled."""
        content = NewsletterContent(
            title="🤖 AI 뉴스레터 📰",
            tldr="이모지와 한글이 포함된 내용 ✨",
            core_issues=[
                CoreIssue(
                    title=f"이슈 {i} 🔥", summary=f"요약 {i} 📝"
                )
                for i in range(3)
            ],
            deep_dive=DeepDive(title="심층 분석 🔍", content="내용 💡"),
            sources=[
                Source(
                    url="https://example.com",
                    title="소스 📚",
                    domain="example.com",
                    accessed_at="2026-01-24T10:00:00Z",
                )
            ],
        )
        assert "🤖" in content.title
        assert "🔥" in content.core_issues[0].title

    def test_special_characters_in_urls(self):
        """Test that URLs with special characters are accepted."""
        source = Source(
            url="https://example.com/article?id=123&lang=ko#section-1",
            title="Article",
            domain="example.com",
            accessed_at="2026-01-24T10:00:00Z",
        )
        assert "?" in source.url
        assert "&" in source.url
        assert "#" in source.url

    def test_none_vs_empty_list(self):
        """Test distinction between None and empty list."""
        context = NewsletterContext(
            topic_id="topic-123",
            topic_text="Test",
            user_answers=[],  # Empty list
        )
        assert context.user_answers == []
        assert context.user_answers is not None

    def test_model_serialization(self):
        """Test that models can be serialized to dict."""
        issue = CoreIssue(
            title="Test Issue",
            summary="Test Summary",
            links=[{"url": "https://example.com", "title": "Example"}],
        )
        issue_dict = issue.model_dump()
        assert issue_dict["title"] == "Test Issue"
        assert issue_dict["summary"] == "Test Summary"
        assert len(issue_dict["links"]) == 1

    def test_model_deserialization(self):
        """Test that models can be deserialized from dict."""
        issue_dict = {
            "title": "Test Issue",
            "summary": "Test Summary",
            "links": [{"url": "https://example.com", "title": "Example"}],
        }
        issue = CoreIssue(**issue_dict)
        assert issue.title == "Test Issue"
        assert len(issue.links) == 1
