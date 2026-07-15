"""Red tests defining the PyTorch-KR Discourse research-source adapter."""

import json
from urllib.parse import parse_qs, urlparse

import httpx

from src.tools.search_tools import (
    _extract_pytorch_kr_post_fields,
    _fetch_pytorch_kr_forum_posts,
    search_pytorch_kr_forum,
)


PUBLICATION_DATE = "2026-07-15"
FORUM_BASE_URL = "https://discuss.pytorch.kr"
LISTING_PATH = "/c/news/14/l/latest.json"

SAMPLE_TOPIC_HTML = """\
<p><img src="/uploads/default/original/1X/cover.png" alt="cover"></p>
<p>첫 번째 실제 본문입니다.</p>
<p>두 번째 실제 본문입니다.</p>
<aside class="onebox" data-onebox-src="https://github.com/example/project">
  <header class="source"><a href="https://github.com/example/project">project</a></header>
</aside>
<footer>
  <a href="https://discuss.pytorch.kr">PyTorchKR</a>
  <a href="https://www.discourse.org">Powered by Discourse</a>
</footer>
"""

SAMPLE_PLAIN_LINK_HTML = """\
<p>논문을 소개합니다.</p>
<p><a href="https://arxiv.org/abs/2601.00001">논문 원문</a>을 참고하세요.</p>
"""

SAMPLE_NO_SOURCE_HTML = """\
<p>외부 원문이 없는 안내입니다.</p>
<p>토론은 포럼에서 이어집니다.</p>
"""

SAMPLE_INELIGIBLE_LINKS_HTML = """\
<p>유효한 원문 링크가 없는 게시글입니다.</p>
<p>관련 커뮤니티 링크만 있습니다.</p>
<a href="https://discuss.pytorch.kr/t/related/8">포럼 내부 글</a>
<a href="https://discuss.pytorch.kr/uploads/default/original/1X/image.png">업로드 이미지</a>
<a href="#reply-1">댓글 앵커</a>
<a href="https://discuss.pytorch.kr/signup">가입</a>
<a href="https://pytorch.kr/">PyTorchKR 홈</a>
<a href="https://t.me/pytorchkr">텔레그램</a>
<footer>
  <a href="https://discuss-noti.pytorch.kr/">알림</a>
  <a href="https://www.discourse.org">Powered by Discourse</a>
</footer>
"""


class FakeResponse:
    """Small httpx-response stand-in for deterministic adapter tests."""

    def __init__(self, payload, *, url: str, status_code: int = 200):
        self._payload = payload
        self.url = url
        self.status_code = status_code

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if not self.is_success:
            request = httpx.Request("GET", self.url)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"Server error {self.status_code} for url {self.url}",
                request=request,
                response=response,
            )


class RecordingForumClient:
    """Routes Discourse listing/detail requests from inline fixture payloads."""

    def __init__(self, listing_pages, topic_details):
        self.listing_pages = listing_pages
        self.topic_details = topic_details
        self.requested_listing_pages = []
        self.requested_topic_ids = []

    def get(self, url, **kwargs):
        parsed = urlparse(str(url))
        if parsed.path == LISTING_PATH:
            params = kwargs.get("params") or {}
            page = int(parse_qs(parsed.query).get("page", [params.get("page", 0)])[0])
            self.requested_listing_pages.append(page)
            if page >= len(self.listing_pages):
                raise AssertionError(f"unexpected listing page request: {page}")
            return FakeResponse(self.listing_pages[page], url=str(url))

        if parsed.path.startswith("/t/") and parsed.path.endswith(".json"):
            topic_id = int(parsed.path.removesuffix(".json").rsplit("/", 1)[-1])
            self.requested_topic_ids.append(topic_id)
            response = self.topic_details[topic_id]
            if isinstance(response, FakeResponse):
                return response
            return FakeResponse(response, url=str(url))

        raise AssertionError(f"unexpected URL requested: {url}")


class FailingForumClient:
    """Context-managed client whose listing request fails at the HTTP boundary."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def get(self, url, **kwargs):
        request = httpx.Request("GET", str(url))
        raise httpx.ConnectError("forum unavailable", request=request)


def _topic(topic_id, title, created_at, *, pinned=False, tags=None):
    return {
        "id": topic_id,
        "slug": title.lower().replace(" ", "-"),
        "title": title,
        "created_at": created_at,
        "pinned": pinned,
        "tags": tags or [],
    }


def _detail(cooked: str):
    return {"post_stream": {"posts": [{"cooked": cooked}]}}


def _listing(topics, *, more_topics_url=None):
    return {"topic_list": {"topics": topics, "more_topics_url": more_topics_url}}


# ---------------------------------------------------------------------------
# HTML extraction and primary-source selection
# ---------------------------------------------------------------------------


def test_extracts_two_meaningful_korean_paragraphs_and_onebox_source():
    content, original_url = _extract_pytorch_kr_post_fields(
        SAMPLE_TOPIC_HTML,
        f"{FORUM_BASE_URL}/t/example/101",
    )

    assert content == "첫 번째 실제 본문입니다.\n\n두 번째 실제 본문입니다."
    assert original_url == "https://github.com/example/project"


def test_uses_external_arxiv_link_when_no_onebox_exists():
    _, original_url = _extract_pytorch_kr_post_fields(
        SAMPLE_PLAIN_LINK_HTML,
        f"{FORUM_BASE_URL}/t/example/102",
    )

    assert original_url == "https://arxiv.org/abs/2601.00001"


def test_falls_back_to_forum_url_when_no_eligible_external_source_exists():
    forum_url = f"{FORUM_BASE_URL}/t/example/103"

    _, original_url = _extract_pytorch_kr_post_fields(SAMPLE_NO_SOURCE_HTML, forum_url)

    assert original_url == forum_url


def test_rejects_internal_media_anchor_signup_home_telegram_and_footer_links():
    forum_url = f"{FORUM_BASE_URL}/t/example/104"

    _, original_url = _extract_pytorch_kr_post_fields(SAMPLE_INELIGIBLE_LINKS_HTML, forum_url)

    assert original_url == forum_url


# ---------------------------------------------------------------------------
# Paginated Discourse collection and error isolation
# ---------------------------------------------------------------------------


def test_fetches_only_inclusive_non_pinned_window_and_stops_after_old_page():
    in_window = _topic(
        101,
        "In Window",
        "2026-07-15T09:00:00.000Z",
        tags=[{"slug": "llm"}, "research"],
    )
    seven_day_boundary = _topic(102, "Seven Day Boundary", "2026-07-08T00:00:00.000Z")
    old_topic = _topic(103, "Too Old", "2026-07-07T23:59:59.000Z")
    pinned_topic = _topic(104, "Pinned", "2026-07-15T08:00:00.000Z", pinned=True)
    page_one_old_topic = _topic(105, "Older Page", "2026-07-07T12:00:00.000Z")

    client = RecordingForumClient(
        [
            _listing(
                [in_window, seven_day_boundary, old_topic, pinned_topic],
                more_topics_url="/c/news/14/l/latest?page=1",
            ),
            _listing([page_one_old_topic], more_topics_url="/c/news/14/l/latest?page=2"),
        ],
        {
            101: _detail(SAMPLE_TOPIC_HTML),
            102: _detail(SAMPLE_PLAIN_LINK_HTML),
        },
    )

    posts, errors = _fetch_pytorch_kr_forum_posts(
        client,
        PUBLICATION_DATE,
        max_pages=5,
        request_delay_seconds=0,
    )

    assert errors == []
    assert [post["title"] for post in posts] == ["In Window", "Seven Day Boundary"]
    assert client.requested_listing_pages == [0, 1]
    assert client.requested_topic_ids == [101, 102]
    assert 103 not in client.requested_topic_ids
    assert 104 not in client.requested_topic_ids
    assert 105 not in client.requested_topic_ids

    required_fields = {"title", "forum_url", "original_url", "content", "published_at", "tags"}
    assert all(required_fields <= post.keys() for post in posts)
    assert posts[0] == {
        "title": "In Window",
        "forum_url": f"{FORUM_BASE_URL}/t/in-window/101",
        "original_url": "https://github.com/example/project",
        "content": "첫 번째 실제 본문입니다.\n\n두 번째 실제 본문입니다.",
        "published_at": "2026-07-15",
        "tags": ["llm", "research"],
    }
    assert posts[1]["forum_url"] == f"{FORUM_BASE_URL}/t/seven-day-boundary/102"
    assert posts[1]["published_at"] == "2026-07-08"


def test_records_failed_detail_and_continues_with_other_eligible_topics():
    successful_topic = _topic(201, "Successful Detail", "2026-07-14T12:00:00.000Z")
    failed_topic = _topic(202, "Failed Detail", "2026-07-13T12:00:00.000Z")
    client = RecordingForumClient(
        [_listing([successful_topic, failed_topic])],
        {
            201: _detail(SAMPLE_TOPIC_HTML),
            202: FakeResponse({}, url=f"{FORUM_BASE_URL}/t/202.json", status_code=503),
        },
    )

    posts, errors = _fetch_pytorch_kr_forum_posts(
        client,
        PUBLICATION_DATE,
        max_pages=1,
        request_delay_seconds=0,
    )

    assert [post["title"] for post in posts] == ["Successful Detail"]
    assert client.requested_topic_ids == [201, 202]
    assert len(errors) == 1
    assert "202" in errors[0]


# ---------------------------------------------------------------------------
# Public error-as-data wrapper
# ---------------------------------------------------------------------------


def test_public_wrapper_serializes_invalid_date_as_error_envelope():
    payload = json.loads(search_pytorch_kr_forum("not-a-date"))

    assert isinstance(payload["errors"], list)
    assert payload["errors"]


def test_public_wrapper_serializes_top_level_http_failure(monkeypatch):
    monkeypatch.setattr(
        "src.tools.search_tools.httpx.Client",
        lambda **kwargs: FailingForumClient(),
    )

    payload = json.loads(search_pytorch_kr_forum(PUBLICATION_DATE))

    assert payload["publication_date"] == PUBLICATION_DATE
    assert payload["posts"] == []
    assert isinstance(payload["errors"], list)
    assert payload["errors"]
