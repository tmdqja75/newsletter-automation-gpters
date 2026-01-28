"""Comprehensive tests for Supabase client."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from .supabase_client import SupabaseClient, get_supabase_client
from .models import NewsletterContext, UserAnswer, NewsletterContent


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://test-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        },
    ):
        yield


@pytest.fixture
def mock_supabase_create_client():
    """Mock supabase create_client function."""
    with patch("src.api.supabase_client.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_create, mock_client


@pytest.fixture
def supabase_client(mock_env, mock_supabase_create_client):
    """Create SupabaseClient instance with mocked dependencies."""
    _, mock_client = mock_supabase_create_client
    client = SupabaseClient()
    return client, mock_client


# =============================================================================
# SupabaseClient Initialization Tests
# =============================================================================


class TestSupabaseClientInit:
    """Tests for SupabaseClient initialization."""

    def test_init_success(self, mock_env, mock_supabase_create_client):
        """Test successful initialization with valid credentials."""
        mock_create, _ = mock_supabase_create_client
        client = SupabaseClient()

        assert client is not None
        mock_create.assert_called_once_with(
            "https://test-project.supabase.co", "test-service-role-key"
        )

    def test_init_missing_url(self, mock_supabase_create_client):
        """Test initialization fails without SUPABASE_URL."""
        with patch.dict(os.environ, {"SUPABASE_SERVICE_ROLE_KEY": "test-key"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SupabaseClient()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set" in str(
                exc_info.value
            )

    def test_init_missing_service_key(self, mock_supabase_create_client):
        """Test initialization fails without SUPABASE_SERVICE_ROLE_KEY."""
        with patch.dict(
            os.environ, {"SUPABASE_URL": "https://test.supabase.co"}, clear=True
        ):
            with pytest.raises(ValueError) as exc_info:
                SupabaseClient()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set" in str(
                exc_info.value
            )

    def test_init_missing_both(self):
        """Test initialization fails without any credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                SupabaseClient()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set" in str(
                exc_info.value
            )


# =============================================================================
# get_topic_and_answers Tests
# =============================================================================


class TestGetTopicAndAnswers:
    """Tests for get_topic_and_answers method."""

    @pytest.mark.asyncio
    async def test_get_topic_and_answers_success(self, supabase_client):
        """Test successful retrieval of topic and answers."""
        client, mock_client = supabase_client

        # Mock topic response
        mock_topic_table = MagicMock()
        mock_topic_response = MagicMock()
        mock_topic_response.data = [
            {
                "id": "topic-123",
                "user_id": "user-456",
                "topic_text": "AI 에이전트 아키텍처",
                "topic_description": "심층 분석",
                "metadata": {},
            }
        ]
        mock_topic_table.select.return_value.eq.return_value.execute.return_value = (
            mock_topic_response
        )

        # Mock questions response
        mock_questions_table = MagicMock()
        mock_questions_response = MagicMock()
        mock_questions_response.data = [
            {
                "id": "q1",
                "question_text": "학습 목표는?",
                "question_type": "goal",
                "display_order": 1,
            },
            {
                "id": "q2",
                "question_text": "난이도는?",
                "question_type": "difficulty",
                "display_order": 2,
            },
        ]
        mock_questions_table.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_questions_response
        )

        # Mock answers response
        mock_answers_table = MagicMock()
        mock_answers_response = MagicMock()
        mock_answers_response.data = [
            {
                "question_id": "q1",
                "answer_text": "AI 에이전트 개발 배우기",
                "answer_value": None,
            },
            {
                "question_id": "q2",
                "answer_text": None,
                "answer_value": {"level": "intermediate"},
            },
        ]
        mock_answers_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = (
            mock_answers_response
        )

        # Mock preferences response
        mock_prefs_table = MagicMock()
        mock_prefs_response = MagicMock()
        mock_prefs_response.data = [
            {
                "preferred_difficulty": "intermediate",
                "preferred_length": "medium",
                "source_whitelist": ["anthropic.com"],
                "source_blacklist": [],
            }
        ]
        mock_prefs_table.select.return_value.eq.return_value.execute.return_value = (
            mock_prefs_response
        )

        # Setup table returns
        def table_side_effect(name):
            if name == "user_topics":
                return mock_topic_table
            elif name == "personalization_questions":
                return mock_questions_table
            elif name == "user_answers":
                return mock_answers_table
            elif name == "user_preferences":
                return mock_prefs_table

        mock_client.table.side_effect = table_side_effect

        # Execute
        context = await client.get_topic_and_answers("topic-123")

        # Verify
        assert isinstance(context, NewsletterContext)
        assert context.topic_id == "topic-123"
        assert context.topic_text == "AI 에이전트 아키텍처"
        assert context.topic_description == "심층 분석"
        assert len(context.user_answers) == 2
        assert context.user_answers[0].question_id == "q1"
        assert context.user_answers[0].answer_text == "AI 에이전트 개발 배우기"
        assert context.user_answers[1].answer_value == {"level": "intermediate"}
        assert context.user_preferences["difficulty"] == "intermediate"
        assert context.user_preferences["source_whitelist"] == ["anthropic.com"]

    @pytest.mark.asyncio
    async def test_get_topic_not_found(self, supabase_client):
        """Test error when topic is not found."""
        client, mock_client = supabase_client

        mock_topic_table = MagicMock()
        mock_topic_response = MagicMock()
        mock_topic_response.data = []
        mock_topic_table.select.return_value.eq.return_value.execute.return_value = (
            mock_topic_response
        )
        mock_client.table.return_value = mock_topic_table

        with pytest.raises(ValueError) as exc_info:
            await client.get_topic_and_answers("nonexistent-topic")
        assert "Topic nonexistent-topic not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_topic_no_answers(self, supabase_client):
        """Test retrieval when there are no user answers."""
        client, mock_client = supabase_client

        mock_topic_table = MagicMock()
        mock_topic_response = MagicMock()
        mock_topic_response.data = [
            {
                "id": "topic-123",
                "user_id": "user-456",
                "topic_text": "Test Topic",
                "topic_description": None,
                "metadata": {},
            }
        ]
        mock_topic_table.select.return_value.eq.return_value.execute.return_value = (
            mock_topic_response
        )

        mock_questions_table = MagicMock()
        mock_questions_response = MagicMock()
        mock_questions_response.data = []
        mock_questions_table.select.return_value.eq.return_value.order.return_value.execute.return_value = (
            mock_questions_response
        )

        mock_answers_table = MagicMock()
        mock_answers_response = MagicMock()
        mock_answers_response.data = []
        mock_answers_table.select.return_value.eq.return_value.in_.return_value.execute.return_value = (
            mock_answers_response
        )

        mock_prefs_table = MagicMock()
        mock_prefs_response = MagicMock()
        mock_prefs_response.data = []
        mock_prefs_table.select.return_value.eq.return_value.execute.return_value = (
            mock_prefs_response
        )

        def table_side_effect(name):
            if name == "user_topics":
                return mock_topic_table
            elif name == "personalization_questions":
                return mock_questions_table
            elif name == "user_answers":
                return mock_answers_table
            elif name == "user_preferences":
                return mock_prefs_table

        mock_client.table.side_effect = table_side_effect

        context = await client.get_topic_and_answers("topic-123")

        assert context.topic_id == "topic-123"
        assert len(context.user_answers) == 0
        assert context.user_preferences == {}


# =============================================================================
# create_newsletter_request Tests
# =============================================================================


class TestCreateNewsletterRequest:
    """Tests for create_newsletter_request method."""

    @pytest.mark.asyncio
    async def test_create_newsletter_request_success(self, supabase_client):
        """Test successful newsletter request creation."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "req-123"}]
        mock_table.insert.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table

        request_id = await client.create_newsletter_request(
            user_id="user-456", topic_id="topic-789"
        )

        assert request_id == "req-123"
        mock_client.table.assert_called_with("newsletter_requests")

        # Verify insert was called with correct data structure
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["user_id"] == "user-456"
        assert insert_call["topic_id"] == "topic-789"
        assert insert_call["status"] == "pending"
        assert "requested_at" in insert_call

    @pytest.mark.asyncio
    async def test_create_newsletter_request_failure(self, supabase_client):
        """Test newsletter request creation failure."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_table.insert.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table

        with pytest.raises(ValueError) as exc_info:
            await client.create_newsletter_request(
                user_id="user-456", topic_id="topic-789"
            )
        assert "Failed to create newsletter request" in str(exc_info.value)


# =============================================================================
# update_request_status Tests
# =============================================================================


class TestUpdateRequestStatus:
    """Tests for update_request_status method."""

    @pytest.mark.asyncio
    async def test_update_status_to_processing(self, supabase_client):
        """Test updating status to processing."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        await client.update_request_status(request_id="req-123", status="processing")

        mock_client.table.assert_called_with("newsletter_requests")
        update_call = mock_table.update.call_args[0][0]
        assert update_call["status"] == "processing"
        assert "processing_started_at" in update_call

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, supabase_client):
        """Test updating status to completed."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        await client.update_request_status(request_id="req-123", status="completed")

        update_call = mock_table.update.call_args[0][0]
        assert update_call["status"] == "completed"
        assert "processing_completed_at" in update_call

    @pytest.mark.asyncio
    async def test_update_status_to_failed_with_error(self, supabase_client):
        """Test updating status to failed with error message."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        await client.update_request_status(
            request_id="req-123",
            status="failed",
            error_message="API 요청 실패",
        )

        update_call = mock_table.update.call_args[0][0]
        assert update_call["status"] == "failed"
        assert update_call["error_message"] == "API 요청 실패"
        assert "processing_completed_at" in update_call

    @pytest.mark.asyncio
    async def test_update_status_with_agent_metadata(self, supabase_client):
        """Test updating status with LangSmith metadata."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        metadata = {"run_id": "ls-run-123", "tokens": 5000}
        await client.update_request_status(
            request_id="req-123",
            status="completed",
            agent_metadata=metadata,
        )

        update_call = mock_table.update.call_args[0][0]
        assert update_call["agent_metadata"] == metadata


# =============================================================================
# save_newsletter Tests
# =============================================================================


class TestSaveNewsletter:
    """Tests for save_newsletter method."""

    @pytest.mark.asyncio
    async def test_save_newsletter_success(self, supabase_client):
        """Test successful newsletter save."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": "news-123"}]
        mock_table.insert.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table

        content = NewsletterContent(
            title="AI 뉴스레터",
            body="# AI 뉴스레터\n\n이것은 테스트 뉴스레터입니다.",
            word_count=1500,
            estimated_reading_time=7,
        )

        newsletter_id = await client.save_newsletter(
            request_id="req-456",
            user_id="user-789",
            topic_id="topic-012",
            content=content,
        )

        assert newsletter_id == "news-123"
        mock_client.table.assert_called_with("newsletters")

        # Verify insert data structure
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["request_id"] == "req-456"
        assert insert_call["user_id"] == "user-789"
        assert insert_call["topic_id"] == "topic-012"
        assert insert_call["title"] == "AI 뉴스레터"
        assert insert_call["body"] == "# AI 뉴스레터\n\n이것은 테스트 뉴스레터입니다."
        assert insert_call["word_count"] == 1500
        assert insert_call["estimated_reading_time"] == 7
        assert insert_call["is_published"] is False

    @pytest.mark.asyncio
    async def test_save_newsletter_failure(self, supabase_client):
        """Test newsletter save failure."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_table.insert.return_value.execute.return_value = mock_response
        mock_client.table.return_value = mock_table

        content = NewsletterContent(
            title="AI 뉴스레터",
            body="# AI 뉴스레터\n\n테스트 내용",
        )

        with pytest.raises(ValueError) as exc_info:
            await client.save_newsletter(
                request_id="req-456",
                user_id="user-789",
                topic_id="topic-012",
                content=content,
            )
        assert "Failed to save newsletter" in str(exc_info.value)


# =============================================================================
# get_newsletter_request_status Tests
# =============================================================================


class TestGetNewsletterRequestStatus:
    """Tests for get_newsletter_request_status method."""

    @pytest.mark.asyncio
    async def test_get_request_status_success(self, supabase_client):
        """Test successful request status retrieval."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "req-123",
                "status": "processing",
                "user_id": "user-456",
                "topic_id": "topic-789",
                "requested_at": "2026-01-24T10:00:00Z",
                "processing_started_at": "2026-01-24T10:01:00Z",
            }
        ]
        mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )
        mock_client.table.return_value = mock_table

        status = await client.get_newsletter_request_status("req-123")

        assert status["id"] == "req-123"
        assert status["status"] == "processing"
        mock_client.table.assert_called_with("newsletter_requests")

    @pytest.mark.asyncio
    async def test_get_request_status_not_found(self, supabase_client):
        """Test request status retrieval when request not found."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )
        mock_client.table.return_value = mock_table

        with pytest.raises(ValueError) as exc_info:
            await client.get_newsletter_request_status("nonexistent-req")
        assert "Request nonexistent-req not found" in str(exc_info.value)


# =============================================================================
# get_newsletter_by_request Tests
# =============================================================================


class TestGetNewsletterByRequest:
    """Tests for get_newsletter_by_request method."""

    @pytest.mark.asyncio
    async def test_get_newsletter_success(self, supabase_client):
        """Test successful newsletter retrieval."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "news-123",
                "request_id": "req-456",
                "user_id": "user-789",
                "topic_id": "topic-012",
                "title": "AI 뉴스레터",
                "created_at": "2026-01-24T10:00:00Z",
            }
        ]
        mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )
        mock_client.table.return_value = mock_table

        newsletter = await client.get_newsletter_by_request("req-456")

        assert newsletter is not None
        assert newsletter["id"] == "news-123"
        assert newsletter["request_id"] == "req-456"

    @pytest.mark.asyncio
    async def test_get_newsletter_not_found(self, supabase_client):
        """Test newsletter retrieval when newsletter doesn't exist."""
        client, mock_client = supabase_client

        mock_table = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )
        mock_client.table.return_value = mock_table

        newsletter = await client.get_newsletter_by_request("nonexistent-req")

        assert newsletter is None


# =============================================================================
# Singleton Pattern Tests
# =============================================================================


class TestGetSupabaseClient:
    """Tests for get_supabase_client singleton."""

    def test_singleton_returns_same_instance(self, mock_env, mock_supabase_create_client):
        """Test that get_supabase_client returns the same instance."""
        # Reset global instance
        import src.api.supabase_client as sc
        sc._supabase_client = None

        client1 = get_supabase_client()
        client2 = get_supabase_client()

        assert client1 is client2

    def test_singleton_creates_instance_once(self, mock_env, mock_supabase_create_client):
        """Test that Supabase client is created only once."""
        import src.api.supabase_client as sc
        sc._supabase_client = None

        mock_create, _ = mock_supabase_create_client

        get_supabase_client()
        get_supabase_client()
        get_supabase_client()

        # Should only be called once
        assert mock_create.call_count == 1


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestSupabaseClientIntegration:
    """Integration-style tests covering multiple operations."""

    @pytest.mark.asyncio
    async def test_full_newsletter_generation_flow(self, supabase_client):
        """Test complete flow from request creation to newsletter save."""
        client, mock_client = supabase_client

        # Setup mocks for all operations
        mock_tables = {
            "newsletter_requests": MagicMock(),
            "newsletters": MagicMock(),
        }

        def table_side_effect(name):
            return mock_tables.get(name, MagicMock())

        mock_client.table.side_effect = table_side_effect

        # Mock request creation
        mock_request_response = MagicMock()
        mock_request_response.data = [{"id": "req-123"}]
        mock_tables["newsletter_requests"].insert.return_value.execute.return_value = (
            mock_request_response
        )

        # Mock newsletter save
        mock_newsletter_response = MagicMock()
        mock_newsletter_response.data = [{"id": "news-456"}]
        mock_tables["newsletters"].insert.return_value.execute.return_value = (
            mock_newsletter_response
        )

        # Create request
        request_id = await client.create_newsletter_request(
            user_id="user-789", topic_id="topic-012"
        )
        assert request_id == "req-123"

        # Update to processing
        await client.update_request_status(request_id="req-123", status="processing")

        # Save newsletter
        content = NewsletterContent(
            title="AI 뉴스레터",
            body="# AI 뉴스레터\n\n테스트 내용",
        )

        newsletter_id = await client.save_newsletter(
            request_id=request_id,
            user_id="user-789",
            topic_id="topic-012",
            content=content,
        )
        assert newsletter_id == "news-456"

        # Update to completed
        await client.update_request_status(request_id="req-123", status="completed")

        # Verify all operations were called
        assert mock_tables["newsletter_requests"].insert.called
        assert mock_tables["newsletter_requests"].update.called
        assert mock_tables["newsletters"].insert.called
