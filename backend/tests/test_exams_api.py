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


def test_exams_are_paginated_and_normalized_from_the_detailed_endpoint():
    fixture = json.loads((FIXTURES / "exams_page.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/kscxtj/queryXsksByxhList"
        assert parse_qs(request.content.decode(), keep_blank_values=True) == {
            "ppylx": ["1"],
            "pxn": ["2025-2026"],
            "pxq": ["2"],
            "pkssjdm": [""],
            "pkkyx": [""],
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
            response = client.get(
                "/api/exams",
                params={"term": "2025-2026-2", "page": 1, "page_size": 2},
            )
    finally:
        app.dependency_overrides.clear()
        upstream.close()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": "exam-1",
                "term": "2025-2026-2",
                "course_code": "CS101",
                "course_name": "程序设计",
                "course_name_en": "Programming",
                "exam_type": "期末考试",
                "exam_type_en": "Final Exam",
                "date": "2026-06-20",
                "date_display": "2026年6月20日",
                "time": "09:00-11:00",
                "week": 17,
                "weekday": 6,
                "weekday_name": "星期六",
                "start_period": 1,
                "end_period": 2,
                "building": "教学楼",
                "room": "101",
                "seat_number": "12",
                "college": "计算机与通信工程学院",
                "remark": "请提前十五分钟入场",
            },
            {
                "id": "exam-2",
                "term": "2025-2026-2",
                "course_code": "MATH001",
                "course_name": "高等数学",
                "course_name_en": "Advanced Mathematics",
                "exam_type": "期末考试",
                "exam_type_en": "Final Exam",
                "date": "2026-06-22",
                "date_display": "2026年6月22日",
                "time": "14:00-16:00",
                "week": 18,
                "weekday": 1,
                "weekday_name": "星期一",
                "start_period": 5,
                "end_period": 6,
                "building": "逸夫楼",
                "room": "202",
                "seat_number": None,
                "college": "理学院",
                "remark": "",
            },
        ],
        "page": 1,
        "page_size": 2,
        "total": 3,
    }
