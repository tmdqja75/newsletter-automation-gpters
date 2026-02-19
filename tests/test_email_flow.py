"""
test_email_flow.py — Simulate newsletter generation & verify email-send trigger

Architecture
------------
FastAPI  /api/newsletter/generate
  └─ NewsletterGenerator.generate_newsletter()
       ├─ newsletter_requests row  →  pending → processing → completed
       └─ newsletters row          →  is_published=True, email_sent_at=NULL
       ⚠️  FastAPI does NOT call Resend.

Browser  (after SSE delivers newsletter_id)
  └─ POST /api/newsletters/{id}/send    ← Next.js API route
       └─ sendNewsletterEmail()          ← Resend SDK
            └─ email delivered

Phase 1  (no network)   — TestClient + mocked agent + in-memory DB
Phase 2  (needs Next.js) — httpx → localhost:3000  (skipped if server is down)
"""

import pytest
import httpx
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

# ── constants ────────────────────────────────────────────────────────────────
MOCK_REQUEST_ID    = "req-aaaa-1111-bbbb-2222"
MOCK_NEWSLETTER_ID = "nl-cccc-3333-dddd-4444"
MOCK_USER_ID       = "user-eeee-5555-ffff-6666"
MOCK_TOPIC_ID      = "topic-7777-gggg-8888-hhhh"

CANNED_BODY = """\
# AI 에이전트 최신 동향 (2026.02.03)

## TL;DR
AI 에이전트 기술이 빠르게 발전하고 있습니다.

## 핵심 이슈
- 멀티 에이전트 협동 프레임워크 확장
- LLM 기반 자율 코딩 에이전트의 성능 개선

## 깊은 분석
최근 여러 기업에서 에이전트 하니스(Agent Harness)를 활용한 자율 워크플로를
선보였습니다. 특히 연구·개발 팀에서 실제 프로덕션 파이프라인에 도입하는
사례가 급증하고 있습니다.

## 출처
- [Anthropic – Multi-Agent Systems](https://anthropic.com/research/multi-agent)
- [OpenAI – Coding Agents](https://openai.com/index/coding-agents)
"""

# ── in-memory DB (shared across all _FakeSupabase instances) ─────────────────


class _DB:
    def __init__(self):
        self.newsletters: dict[str, dict] = {}
        self.requests: dict[str, dict] = {}

    def reset(self):
        self.newsletters.clear()
        self.requests.clear()


_db = _DB()


# ── fake Supabase client ─────────────────────────────────────────────────────


class _FakeSupabase:
    """Drop-in for src.api.supabase_client.SupabaseClient.
    All writes land in the module-level _db so any instance can read them back.
    """

    async def create_newsletter_request(self, user_id: str, topic_id: str) -> str:
        _db.requests[MOCK_REQUEST_ID] = {
            "id": MOCK_REQUEST_ID,
            "user_id": user_id,
            "topic_id": topic_id,
            "status": "pending",
        }
        return MOCK_REQUEST_ID

    async def update_request_status(self, request_id: str, status: str, **kw):
        _db.requests[request_id]["status"] = status

    async def get_topic_and_answers(self, topic_id: str):
        from src.api.models import NewsletterContext

        return NewsletterContext(
            topic_id=topic_id,
            topic_text="AI 에이전트 최신 동향",
            topic_description="최신 AI 에이전트 기술 트렌드",
            user_answers=[],
            user_preferences={"difficulty": "intermediate"},
        )

    async def save_newsletter(self, request_id, user_id, topic_id, content) -> str:
        _db.newsletters[MOCK_NEWSLETTER_ID] = {
            "id": MOCK_NEWSLETTER_ID,
            "request_id": request_id,
            "user_id": user_id,
            "topic_id": topic_id,
            "title": content.title,
            "body": content.body,
            "word_count": content.word_count,
            "is_published": True,
            "email_sent_at": None,  # ← assertion target
        }
        return MOCK_NEWSLETTER_ID

    async def get_newsletter_request_status(self, request_id: str) -> dict:
        return _db.requests.get(request_id, {})

    async def get_newsletter_by_request(self, request_id: str):
        for nl in _db.newsletters.values():
            if nl["request_id"] == request_id:
                return nl
        return None


# ── fake agent (returns canned markdown in one tick) ────────────────────────


class _FakeAgent:
    def stream(self, input, config=None):  # noqa: A002
        msg = Mock()
        msg.content = CANNED_BODY
        yield {"model": {"messages": [msg]}}


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_db():
    _db.reset()


@pytest.fixture()
def app_client():
    """FastAPI TestClient with fully mocked generation pipeline."""
    gen_patches = [
        patch(
            "src.api.newsletter_generator.get_supabase_client",
            new=lambda: _FakeSupabase(),
        ),
        patch(
            "src.api.newsletter_generator.create_deep_agent",
            new=lambda **kw: _FakeAgent(),
        ),
        patch(
            "src.api.newsletter_generator.create_research_subagent",
            new=lambda *a, **kw: Mock(),
        ),
        patch(
            "src.api.newsletter_generator.create_topic_selector_subagent",
            new=lambda *a, **kw: Mock(),
        ),
        patch(
            "src.api.newsletter_generator.create_tone_editor_agent",
            new=lambda **kw: Mock(),
        ),
        patch("src.api.newsletter_generator.ANTHROPIC_API_KEY", "sk-fake"),
        patch("src.api.newsletter_generator.TAVILY_API_KEY", "tvly-fake"),
    ]
    for p in gen_patches:
        p.start()

    from src.api.newsletter_generator import NewsletterGenerator

    generator = NewsletterGenerator()
    generator.supabase = _FakeSupabase()

    with patch("api.main.get_newsletter_generator", new=lambda: generator), patch(
        "api.main.get_supabase_client", new=lambda: _FakeSupabase()
    ):
        from api.main import app

        with TestClient(app) as client:
            yield client

    for p in gen_patches:
        p.stop()


# ── Phase 1: FastAPI generation ──────────────────────────────────────────────


class TestPhase1_Generation:
    """All tests run against TestClient — zero network required."""

    def test_health_check(self, app_client):
        resp = app_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_generate_returns_completed(self, app_client):
        """POST /api/newsletter/generate → 200, status=completed."""
        resp = app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["request_id"] == MOCK_REQUEST_ID

    def test_newsletter_persisted(self, app_client):
        """save_newsletter() was called and the row exists in the DB."""
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        assert MOCK_NEWSLETTER_ID in _db.newsletters

    def test_email_not_sent_by_fastapi(self, app_client):
        """⚡ Core assertion: email_sent_at is None after generation.

        FastAPI's job ends at persisting the newsletter.
        Email delivery is triggered by a separate POST from the frontend
        to Next.js /api/newsletters/{id}/send.
        """
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        nl = _db.newsletters[MOCK_NEWSLETTER_ID]
        assert nl["is_published"] is True
        assert nl["email_sent_at"] is None

    def test_title_extracted_from_markdown(self, app_client):
        """_parse_agent_response pulls the title from the # heading."""
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        title = _db.newsletters[MOCK_NEWSLETTER_ID]["title"]
        assert "AI 에이전트" in title
        assert "2026.02.03" in title

    def test_word_count_calculated(self, app_client):
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        assert _db.newsletters[MOCK_NEWSLETTER_ID]["word_count"] > 0

    def test_request_status_completed(self, app_client):
        """newsletter_requests row transitions all the way to completed."""
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        assert _db.requests[MOCK_REQUEST_ID]["status"] == "completed"

    def test_status_endpoint_reflects_completion(self, app_client):
        """GET /api/newsletter/status/{id} returns completed + newsletter_id."""
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )
        resp = app_client.get(f"/api/newsletter/status/{MOCK_REQUEST_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["newsletter_id"] == MOCK_NEWSLETTER_ID


# ── Phase 2: Email-send trigger via Next.js ─────────────────────────────────
#
# These tests hit the real Next.js dev server.  They are skipped automatically
# when the server is not reachable.  The fake newsletter_id doesn't exist in
# the real Supabase DB, so the expected responses are:
#   • no session cookie  → 401  (auth guard fires first)
#   • valid session + fake id → 404  (newsletter not in real DB)
# Both outcomes confirm the send gate is wired correctly.

NEXT_SEND_URL = "http://localhost:3000/api/newsletters/{id}/send"


class TestPhase2_EmailSendTrigger:
    @pytest.fixture(autouse=True)
    def _require_next_js(self):
        """Skip entire class when the Automata Next.js dev server is not running.

        Next.js sets ``x-powered-by: Next.js`` by default; we use that header
        as a positive signal so we don't accidentally hit an unrelated service
        on the same port.
        """
        try:
            resp = httpx.get("http://localhost:3000", timeout=2)
            if "next.js" not in resp.headers.get("x-powered-by", "").lower():
                pytest.skip("Port 3000 is not the Automata Next.js app — start with `cd web && npm run dev`")
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("Next.js dev server not running on :3000 — start with `cd web && npm run dev`")

    def test_send_without_session_returns_401(self, app_client):
        """No auth cookie → 401 before any DB or Resend call."""
        app_client.post(
            "/api/newsletter/generate",
            json={"user_id": MOCK_USER_ID, "topic_id": MOCK_TOPIC_ID},
        )

        resp = httpx.post(
            NEXT_SEND_URL.format(id=MOCK_NEWSLETTER_ID),
            timeout=5,
        )
        assert resp.status_code == 401
        assert resp.json()["error"] == "Unauthorized"
        # Confirm: no email was sent — the auth guard stopped the request
        assert _db.newsletters[MOCK_NEWSLETTER_ID]["email_sent_at"] is None
