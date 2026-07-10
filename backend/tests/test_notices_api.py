import asyncio
import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from fastapi.testclient import TestClient

from app.dependencies import get_authenticated_session
from app.main import app
from app.services.session_store import AuthState, Session

FIXTURES = Path(__file__).parent / "fixtures"


def test_notices_are_paginated_and_normalized():
    fixture = json.loads((FIXTURES / "notices_page.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/component/queryTongZhiGongGaoPage"
        assert parse_qs(request.content.decode()) == {
            "pageNum": ["1"],
            "pageSize": ["2"],
        }
        return httpx.Response(200, json=fixture)

    upstream = httpx.Client(transport=httpx.MockTransport(handler))
    session = Session(
        client=upstream,
        state=AuthState.ACTIVE,
        authenticated=True,
        lock=asyncio.Lock(),
    )
    app.dependency_overrides[get_authenticated_session] = lambda: session

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/notices", params={"page": 1, "page_size": 2})
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "notice-1",
                "title": "考试安排通知",
                "sender": "教务处",
                "sent_at": "2026-07-09 10:00:00",
                "content": "<p>请查看考试安排。</p>",
                "is_read": False,
                "is_pinned": True,
                "has_attachment": True,
                "external_url": None,
            },
            {
                "id": "notice-2",
                "title": "系统维护通知",
                "sender": "信息中心",
                "sent_at": "2026-07-08 09:00:00",
                "content": "<p>系统维护。</p>",
                "is_read": True,
                "is_pinned": False,
                "has_attachment": False,
                "external_url": "https://example.edu/notice/2",
            },
        ],
        "page": 1,
        "page_size": 2,
        "total": 3,
    }
