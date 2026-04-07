"""
/agui/run 엔드포인트 테스트
A2A 서버를 mock하여 실제 서버 없이 SSE 스트림 검증
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def make_request_body(user_message: str = "서울 호텔 추천해줘") -> dict:
    return {
        "thread_id": "test-thread-001",
        "run_id": "test-run-001",
        "messages": [
            {
                "id": "msg-001",
                "role": "user",
                "content": user_message,
            }
        ],
        "state": {},
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


def parse_sse_events(raw: str) -> list[dict]:
    """SSE 응답 텍스트에서 data 필드만 파싱하여 이벤트 목록 반환."""
    events = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload:
                try:
                    events.append(json.loads(payload))
                except json.JSONDecodeError:
                    pass
    return events


async def test_run_agent_empty_messages_uses_fallback(client):
    """messages가 빈 리스트이면 기본 메시지('안녕하세요')로 A2A 호출."""
    body = make_request_body()
    body["messages"] = []

    with patch("main.httpx.AsyncClient") as mock_http:
        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(side_effect=Exception("연결 실패"))
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=body)

    # 연결 실패여도 RUN_STARTED/RUN_ERROR/RUN_FINISHED 구조는 유지
    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert any(e.get("type") == "RUN_STARTED" for e in events)


async def test_run_agent_sse_starts_and_ends(client):
    """A2A 서버 mock — RUN_STARTED / RUN_FINISHED 이벤트가 반드시 포함되어야 한다."""

    async def mock_a2a_stream(_):
        # 빈 스트림: A2A 응답 없이 종료
        return
        yield  # async generator로 만들기 위한 더미

    mock_card = MagicMock()
    mock_a2a_client = MagicMock()
    mock_a2a_client.send_message_streaming = mock_a2a_stream

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
    ):
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"name": "test-agent", "url": "http://test"})
        mock_response.raise_for_status = MagicMock()

        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=make_request_body())

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "RUN_STARTED" in event_types
    assert "RUN_FINISHED" in event_types
    # RUN_STARTED가 RUN_FINISHED보다 먼저
    assert event_types.index("RUN_STARTED") < event_types.index("RUN_FINISHED")


async def test_run_agent_a2a_error_returns_run_error(client):
    """A2A 서버 연결 실패 시 RUN_ERROR 이벤트가 포함되어야 한다."""

    with patch("main.httpx.AsyncClient") as mock_http:
        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(side_effect=Exception("연결 실패"))
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=make_request_body())

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    event_types = [e.get("type") for e in events]

    assert "RUN_ERROR" in event_types
    assert "RUN_FINISHED" in event_types
