"""
test_main_state_handling.py — main.py의 event_stream()에서
StateManager.apply_client_state가 올바르게 호출되는지 검증
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ag_ui.core.events import StateSnapshotEvent, EventType


@pytest.mark.asyncio
async def test_apply_client_state_called_with_body_state():
    """event_stream 내에서 body['state']가 apply_client_state에 전달된다."""
    from main import app
    from httpx import AsyncClient, ASGITransport

    raw_state = {
        "travel_context": {"destination": "도쿄"},
        "ui_context": {"selected_hotel_code": "HTL-001"},
    }

    mock_snapshot = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "client_state", "travel_context": {}, "ui_context": {}},
    )

    captured_args: dict = {}

    async def mock_apply_client_state(thread_id, raw):
        captured_args["thread_id"] = thread_id
        captured_args["raw_state"] = raw
        yield mock_snapshot

    mock_state_mgr = MagicMock()
    mock_state_mgr.apply_client_state = mock_apply_client_state
    mock_state_mgr.get.return_value = MagicMock(
        travel_context=MagicMock(
            destination=None, origin=None, check_in=None,
            check_out=None, nights=None, guests=None, trip_type=None,
        ),
        ui_context=MagicMock(selected_hotel_code=None),
    )

    async def empty_stream():
        return
        yield  # async generator

    with patch("main.state_manager", mock_state_mgr), \
         patch("main.httpx.AsyncClient") as mock_http:
        mock_http_instance = AsyncMock()
        mock_http.return_value.__aenter__.return_value = mock_http_instance
        mock_http_instance.get.return_value = MagicMock(
            json=lambda: {
                "name": "test", "url": "http://localhost:8001",
                "version": "1.0", "capabilities": {},
            },
            raise_for_status=lambda: None,
        )

        with patch("main.A2AClient") as mock_a2a_cls:
            mock_a2a_instance = MagicMock()
            mock_a2a_cls.return_value = mock_a2a_instance
            mock_a2a_instance.send_message_streaming.return_value = empty_stream()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payload = {
                    "threadId": "test-thread",
                    "runId": "test-run",
                    "messages": [{"id": "m1", "role": "user", "content": "테스트"}],
                    "tools": [],
                    "context": [],
                    "forwardedProps": {},
                    "state": raw_state,
                }
                response = await ac.post("/agui/run", json=payload)
                _ = response.content

    assert captured_args.get("raw_state") == raw_state
