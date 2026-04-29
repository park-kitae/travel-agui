"""
/agui/run 엔드포인트 테스트
A2A 서버를 mock하여 실제 서버 없이 SSE 스트림 검증
"""
import json
from types import SimpleNamespace
import pytest  # type: ignore[reportMissingImports]
from unittest.mock import AsyncMock, patch, MagicMock
from a2a.types import Artifact, DataPart, Part, TaskArtifactUpdateEvent, TextPart  # type: ignore[reportMissingImports]


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


def make_agent_state_artifact(snapshot: dict) -> MagicMock:
    event = TaskArtifactUpdateEvent(
        task_id="task-001",
        context_id="test-thread-001",
        artifact=Artifact(
            artifact_id="artifact-001",
            parts=[Part(root=DataPart(data=snapshot))],
        ),
        append=False,
        last_chunk=False,
    )
    response = MagicMock()
    response.root.result = event
    return response


def make_text_artifact(text: str, *, append: bool, last_chunk: bool) -> MagicMock:
    event = TaskArtifactUpdateEvent(
        task_id="task-001",
        context_id="test-thread-001",
        artifact=Artifact(
            artifact_id="artifact-text-001",
            parts=[Part(root=TextPart(text=text))],
        ),
        append=append,
        last_chunk=last_chunk,
    )
    response = MagicMock()
    response.root.result = event
    return response


def make_multi_text_artifact(texts: list[str], *, append: bool, last_chunk: bool) -> MagicMock:
    event = TaskArtifactUpdateEvent(
        task_id="task-001",
        context_id="test-thread-001",
        artifact=Artifact(
            artifact_id="artifact-text-001",
            parts=[Part(root=TextPart(text=text)) for text in texts],
        ),
        append=append,
        last_chunk=last_chunk,
    )
    response = MagicMock()
    response.root.result = event
    return response


def make_runtime(current_state=None, merged_state=None, enriched_message: str = "[enriched] 서울 호텔 추천해줘"):
    runtime = MagicMock()
    runtime.get_state.return_value = current_state if current_state is not None else {"stored": True}
    runtime.prepare_request.return_value = SimpleNamespace(
        state=merged_state if merged_state is not None else {"merged": True},
        user_message=enriched_message,
    )
    return runtime


async def test_run_agent_empty_messages_uses_fallback(client):
    """messages가 빈 리스트이면 기본 메시지('안녕하세요')로 A2A 호출."""
    body = make_request_body()
    body["messages"] = []
    runtime = make_runtime(enriched_message="안녕하세요")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
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
    runtime = make_runtime(enriched_message="[runtime-context] 서울 호텔 추천해줘")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"name": "test-agent", "url": "http://test"})
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

    runtime = make_runtime(enriched_message="[runtime-context] 서울 호텔 추천해줘")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
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


async def test_run_agent_forwards_client_state_in_metadata_and_avoids_duplicate_state_snapshot(client):
    """client_state는 A2A metadata로 전달되고 SSE에는 중복 없이 단일 agent_state만 노출된다."""

    snapshot = {
        "snapshot_type": "agent_state",
        "travel_context": {
            "destination": "도쿄",
            "origin": None,
            "check_in": "2026-04-23",
            "check_out": "2026-04-30",
            "nights": 7,
            "guests": 2,
            "rooms": None,
            "trip_type": None,
            "budget_range": None,
            "travel_purpose": None,
        },
        "agent_status": {
            "current_intent": "collecting_hotel_params",
            "missing_fields": ["check_in", "check_out", "guests"],
            "active_tool": "request_user_input",
        },
        "user_preferences": {
            "hotel_grade": "4성",
            "hotel_type": "비즈니스",
            "amenities": ["수영장"],
            "seat_class": None,
            "seat_position": None,
            "meal_preference": None,
            "airline_preference": [],
        },
    }

    async def mock_a2a_stream(_request):
        yield make_agent_state_artifact(snapshot)

    mock_card = MagicMock()
    mock_a2a_client = MagicMock()
    mock_a2a_client.send_message_streaming = MagicMock(side_effect=mock_a2a_stream)

    body = make_request_body("도쿄 호텔 추천해줘")
    body["state"] = {
        "travel_context": {"destination": "도쿄", "guests": 2},
        "user_preferences": {
            "hotel_grade": "4성",
            "hotel_type": "비즈니스",
            "amenities": ["수영장"],
        },
        "ui_context": {"selected_hotel_code": None, "selected_flight_id": None},
    }
    current_state = {"travel_context": {"destination": "서울"}}
    merged_state = {"travel_context": {"destination": "도쿄", "guests": 2}}
    runtime = make_runtime(
        current_state=current_state,
        merged_state=merged_state,
        enriched_message="[runtime-context] 도쿄 호텔 추천해줘",
    )

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"name": "test-agent", "url": "http://test"})
        mock_response.raise_for_status = MagicMock()

        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=body)

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    state_events = [event for event in events if event.get("type") == "STATE_SNAPSHOT"]
    assert len(state_events) == 1
    assert state_events[0]["snapshot"]["snapshot_type"] == "agent_state"
    assert state_events[0]["snapshot"]["user_preferences"]["hotel_grade"] == "4성"

    sent_request = mock_a2a_client.send_message_streaming.call_args.args[0]
    assert sent_request.params.metadata == {"client_state": body["state"]}
    runtime.prepare_request.assert_called_once_with("test-thread-001", body["state"], "도쿄 호텔 추천해줘")
    assert sent_request.params.message.parts[0].root.text == "[runtime-context] 도쿄 호텔 추천해줘"


async def test_run_agent_preserves_chunked_a2a_text_as_multiple_agui_events(client):
    """Chunked text artifacts should stay chunked after A2A -> AG-UI conversion."""

    async def mock_a2a_stream(_request):
        yield make_text_artifact("안", append=False, last_chunk=False)
        yield make_text_artifact("녕", append=True, last_chunk=True)

    mock_card = MagicMock()
    mock_a2a_client = MagicMock()
    mock_a2a_client.send_message_streaming = MagicMock(side_effect=mock_a2a_stream)
    runtime = make_runtime(enriched_message="[runtime-context] 안녕하세요")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"name": "test-agent", "url": "http://test"})
        mock_response.raise_for_status = MagicMock()

        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=make_request_body("안녕하세요"))

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["delta"] for event in events if event.get("type") == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]


async def test_run_agent_multi_part_final_artifact_stays_one_assistant_turn(client):
    """One final TaskArtifactUpdateEvent with multiple TextParts must stay one AG-UI message."""

    async def mock_a2a_stream(_request):
        yield make_multi_text_artifact(["안", "녕"], append=False, last_chunk=True)

    mock_card = MagicMock()
    mock_a2a_client = MagicMock()
    mock_a2a_client.send_message_streaming = MagicMock(side_effect=mock_a2a_stream)
    runtime = make_runtime(enriched_message="[runtime-context] 안녕하세요")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"name": "test-agent", "url": "http://test"})
        mock_response.raise_for_status = MagicMock()

        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=make_request_body("안녕하세요"))

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["delta"] for event in events if event.get("type") == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]
    assert [event["type"] for event in events].count("TEXT_MESSAGE_START") == 1
    assert [event["type"] for event in events].count("TEXT_MESSAGE_END") == 1


async def test_run_agent_runtime_preparation_error_returns_run_error(client):
    """Runtime-backed pre-A2A preparation failures still yield RUN_ERROR and RUN_FINISHED."""

    runtime = MagicMock()
    runtime.prepare_request.side_effect = RuntimeError("state merge failed")

    with (
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        response = await client.post("/agui/run", json=make_request_body())

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    event_types = [event.get("type") for event in events]

    assert event_types == ["RUN_STARTED", "RUN_ERROR", "RUN_FINISHED"]
    assert events[1]["message"] == "state merge failed"
    assert events[1]["code"] == "A2A_ERROR"
