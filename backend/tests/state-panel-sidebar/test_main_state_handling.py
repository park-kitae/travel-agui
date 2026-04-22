"""Runtime-backed state handling tests for main.py."""
from types import SimpleNamespace

import pytest  # type: ignore[reportMissingImports]
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_runtime_merges_client_state_and_saves_for_thread():
    """event_stream delegates request preparation to the runtime helper."""
    from main import app
    from httpx import AsyncClient, ASGITransport  # type: ignore[reportMissingImports]

    raw_state = {
        "travel_context": {"destination": "도쿄"},
        "ui_context": {"selected_hotel_code": "HTL-001"},
    }

    mock_runtime = MagicMock()
    mock_runtime.prepare_request.return_value = SimpleNamespace(
        state={"travel_context": {"destination": "도쿄"}, "ui_context": {"selected_hotel_code": "HTL-001"}},
        user_message="[runtime-context] 테스트",
    )

    async def empty_stream():
        return
        yield  # async generator

    with patch("main.initialize_runtime_or_die"), \
         patch("main.get_runtime", return_value=mock_runtime), \
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

    mock_runtime.prepare_request.assert_called_once_with("test-thread", raw_state, "테스트")
