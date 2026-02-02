"""Shared pytest fixtures and configuration for API tests."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


# =============================================================================
# Environment Setup
# =============================================================================


@pytest.fixture
def reset_singleton():
    """Reset the SupabaseClient singleton before each test."""
    import sys
    if "src.api.supabase_client" in sys.modules:
        import src.api.supabase_client as sc
        sc._supabase_client = None
        yield
        sc._supabase_client = None
    else:
        yield


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables."""
    env_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "LANGSMITH_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_topic_data():
    """Sample topic data from Supabase."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "topic_text": "AI 에이전트 아키텍처",
        "topic_description": "심층 분석 및 최신 동향",
        "metadata": {"source": "web_app"},
    }


@pytest.fixture
def sample_questions_data():
    """Sample personalization questions data."""
    return [
        {
            "id": "q1",
            "topic_id": "550e8400-e29b-41d4-a716-446655440000",
            "question_text": "학습 목표가 무엇인가요?",
            "question_type": "goal",
            "display_order": 1,
        },
        {
            "id": "q2",
            "topic_id": "550e8400-e29b-41d4-a716-446655440000",
            "question_text": "선호하는 난이도는?",
            "question_type": "difficulty",
            "display_order": 2,
        },
        {
            "id": "q3",
            "topic_id": "550e8400-e29b-41d4-a716-446655440000",
            "question_text": "관심 있는 세부 주제는?",
            "question_type": "subtopic",
            "display_order": 3,
        },
    ]


@pytest.fixture
def sample_answers_data():
    """Sample user answers data."""
    return [
        {
            "id": "a1",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "question_id": "q1",
            "answer_text": "AI 에이전트 개발 능력 향상",
            "answer_value": None,
            "skipped": False,
        },
        {
            "id": "a2",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "question_id": "q2",
            "answer_text": None,
            "answer_value": {"level": "intermediate"},
            "skipped": False,
        },
    ]


@pytest.fixture
def sample_preferences_data():
    """Sample user preferences data."""
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "preferred_difficulty": "intermediate",
        "preferred_length": "medium",
        "source_whitelist": ["anthropic.com", "openai.com"],
        "source_blacklist": ["example-spam.com"],
    }


@pytest.fixture
def sample_newsletter_content():
    """Sample simplified newsletter content."""
    from .models import NewsletterContent

    body = """# AI 뉴스레터 - 2026년 1월 4주차

## 이번 주 주요 소식

이번 주는 AI 분야에서 여러 중요한 발표들이 있었습니다.

### Claude Opus 4.5 출시

Anthropic이 최신 모델 Claude Opus 4.5를 공개했습니다. 이번 업데이트로 AI 성능이 대폭 향상되었습니다.

- [Introducing Claude Opus 4.5](https://anthropic.com/blog/claude-opus-4-5)

### AI 에이전트 하니스 개발

새로운 에이전트 프레임워크가 오픈소스로 공개되었습니다.

- [Agent Harness on GitHub](https://github.com/example/agent-harness)

### LangGraph 2.0 베타 릴리즈

LangChain의 그래프 기반 워크플로우 엔진이 업데이트되었습니다.

- [LangGraph 2.0 Announcement](https://blog.langchain.com/langgraph-2-0)

## Deep Dive: AI 에이전트 아키텍처의 진화

AI 에이전트 시스템은 단순한 프롬프트 기반 모델에서 복잡한 다중 에이전트 시스템으로 발전하고 있습니다.

주요 변화:
1. 모듈화된 에이전트 구조
2. 도구 사용(Tool Use) 능력 향상
3. 메모리 및 컨텍스트 관리

이러한 발전은 더욱 강력하고 신뢰할 수 있는 AI 시스템 구축을 가능하게 합니다.

### 추가 자료

- [Agent Architecture Survey 2026](https://arxiv.org/abs/2024.12345)

## 다음 탐구 질문

- AI 에이전트의 메모리 시스템은 어떻게 설계하나요?
- 다중 에이전트 협업 패턴은 무엇이 있나요?
"""

    return NewsletterContent(
        title="AI 뉴스레터 - 2026년 1월 4주차",
        body=body,
        word_count=1500,
        estimated_reading_time=7,
    )


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    fixed_datetime = datetime(2026, 1, 24, 10, 0, 0)
    return fixed_datetime


@pytest.fixture
def mock_supabase_response_builder():
    """Factory fixture for building mock Supabase responses."""

    def builder(data, count=None):
        """Build a mock Supabase response."""
        mock_response = MagicMock()
        mock_response.data = data
        if count is not None:
            mock_response.count = count
        return mock_response

    return builder


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark asyncio tests
        if "asyncio" in item.keywords:
            item.add_marker(pytest.mark.asyncio)

        # Auto-mark based on test file location
        if "test_models" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "test_supabase_client" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
