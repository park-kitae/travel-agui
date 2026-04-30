"""
a2a_to_agui_stream 변환 로직 단위 테스트
A2A 이벤트를 직접 생성하여 AG-UI 이벤트로 올바르게 변환되는지 검증
"""
import json
import pytest  # type: ignore[reportMissingImports]
from unittest.mock import AsyncMock, MagicMock

from converter import a2a_to_agui_stream
from domain_runtime import DomainRuntime
from domains.travel.plugin import get_plugin
from executor import ADKAgentExecutor
from state.store import SerializedStateStore


def make_text_artifact(
    text: str,
    *,
    last_chunk: bool = True,
    append: bool = False,
    artifact_id: str = "artifact-text-001",
):
    """TextPart를 담은 TaskArtifactUpdateEvent mock 생성."""
    from a2a.types import TaskArtifactUpdateEvent, Artifact, Part, TextPart  # type: ignore[reportMissingImports]

    part = MagicMock()
    part.root = TextPart(text=text)

    artifact = MagicMock()
    artifact.artifact_id = artifact_id
    artifact.parts = [part]

    event = MagicMock(spec=TaskArtifactUpdateEvent)
    event.artifact = artifact
    event.last_chunk = last_chunk
    event.append = append

    response = MagicMock()
    response.root.result = event
    return response


def make_multi_text_artifact(
    texts: list[str],
    *,
    last_chunk: bool = True,
    append: bool = False,
    artifact_id: str = "artifact-text-001",
):
    """여러 TextPart를 담은 TaskArtifactUpdateEvent mock 생성."""
    from a2a.types import TaskArtifactUpdateEvent, Artifact, Part, TextPart  # type: ignore[reportMissingImports]

    artifact = MagicMock()
    artifact.artifact_id = artifact_id
    artifact.parts = []
    for text in texts:
        part = MagicMock()
        part.root = TextPart(text=text)
        artifact.parts.append(part)

    event = MagicMock(spec=TaskArtifactUpdateEvent)
    event.artifact = artifact
    event.last_chunk = last_chunk
    event.append = append

    response = MagicMock()
    response.root.result = event
    return response


def make_task_status(state_value: str):
    """TaskStatusUpdateEvent mock 생성."""
    from a2a.types import TaskStatusUpdateEvent, TaskState  # type: ignore[reportMissingImports]

    state_map = {
        "working": TaskState.working,
        "completed": TaskState.completed,
    }

    status = MagicMock()
    status.state = state_map.get(state_value, TaskState.completed)

    event = MagicMock(spec=TaskStatusUpdateEvent)
    event.status = status

    response = MagicMock()
    response.root.result = event
    return response


def make_data_artifact(data: dict):
    """DataPart를 담은 TaskArtifactUpdateEvent mock 생성."""
    from a2a.types import TaskArtifactUpdateEvent, Artifact, DataPart, Part  # type: ignore[reportMissingImports]

    part = MagicMock()
    part.root = DataPart(data=data)

    artifact = MagicMock()
    artifact.parts = [part]

    event = MagicMock(spec=TaskArtifactUpdateEvent)
    event.artifact = artifact
    event.last_chunk = False

    response = MagicMock()
    response.root.result = event
    return response


def make_event_response(event):
    response = MagicMock()
    response.root.result = event
    return response


def make_function_call_adk_event(tool_name: str, args: dict, *, partial: bool = False):
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args

    part = MagicMock()
    part.text = None
    part.function_call = fc
    part.function_response = None

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.partial = partial
    event.is_final_response.return_value = False
    return event


def make_text_adk_event(text: str, *, is_final: bool) -> MagicMock:
    part = MagicMock()
    part.text = text
    part.function_call = None
    part.function_response = None

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.is_final_response.return_value = is_final
    return event


def make_multi_text_adk_event(texts: list[str], *, is_final: bool) -> MagicMock:
    content = MagicMock()
    content.parts = []

    for text in texts:
        part = MagicMock()
        part.text = text
        part.function_call = None
        part.function_response = None
        content.parts.append(part)

    event = MagicMock()
    event.content = content
    event.is_final_response.return_value = is_final
    return event


def make_function_response_adk_event(tool_name: str, response_data: dict):
    fr = MagicMock()
    fr.name = tool_name
    fr.response = response_data

    part = MagicMock()
    part.text = None
    part.function_call = None
    part.function_response = fr

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.is_final_response.return_value = False
    return event


async def _async_gen(*items):
    for item in items:
        yield item


async def execute_and_collect_stream(adk_events: list, *, metadata: dict | None = None) -> list[dict]:
    runtime = DomainRuntime(plugin=get_plugin(), state_store=SerializedStateStore())
    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(*adk_events)
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    executor = ADKAgentExecutor(mock_runner, mock_session_service, runtime=runtime)
    event_queue = AsyncMock()
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "thread-1"
    context.get_user_input.return_value = "도쿄 호텔 추천해줘"
    context.metadata = metadata or {}

    await executor.execute(context, event_queue)

    responses = [make_event_response(call.args[0]) for call in event_queue.enqueue_event.call_args_list]
    return await collect_stream(responses)


async def collect_stream(responses: list) -> list[dict]:
    """a2a_to_agui_stream 결과를 이벤트 목록으로 수집."""
    async def mock_a2a_gen():
        for r in responses:
            yield r

    results = []
    async for raw in a2a_to_agui_stream(mock_a2a_gen(), "run-1", "thread-1"):
        # SSE 형식: "data: {...}\n\n"
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload:
                    results.append(json.loads(payload))
    return results


async def test_text_artifact_produces_message_events():
    """TextPart → TEXT_MESSAGE_START, CHUNK, END 순서 검증."""
    events = await collect_stream([make_text_artifact("안녕하세요", last_chunk=True)])
    types = [e["type"] for e in events]

    assert "TEXT_MESSAGE_START" in types
    assert "TEXT_MESSAGE_CHUNK" in types
    assert "TEXT_MESSAGE_END" in types
    assert types.index("TEXT_MESSAGE_START") < types.index("TEXT_MESSAGE_CHUNK")
    assert types.index("TEXT_MESSAGE_CHUNK") < types.index("TEXT_MESSAGE_END")


async def test_text_chunk_contains_correct_delta():
    """TEXT_MESSAGE_CHUNK의 delta 값이 원본 텍스트와 일치해야 한다."""
    events = await collect_stream([make_text_artifact("테스트 텍스트")])
    chunk = next(e for e in events if e["type"] == "TEXT_MESSAGE_CHUNK")
    assert chunk["delta"] == "테스트 텍스트"


async def test_text_chunks_share_one_message_boundary() -> None:
    """두 개의 텍스트 청크는 하나의 assistant turn으로 변환되어야 한다."""
    events = await collect_stream([
        make_text_artifact("안", last_chunk=False),
        make_text_artifact("녕", last_chunk=True),
    ])

    assert [event["type"] for event in events] == [
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_END",
    ]
    assert [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]


@pytest.mark.asyncio
async def test_multi_part_text_artifact_keeps_one_message_boundary() -> None:
    events = await collect_stream([
        make_multi_text_artifact(["안", "녕"], last_chunk=True),
    ])

    assert [event["type"] for event in events] == [
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_END",
    ]
    assert [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]
    assert [event["type"] for event in events].count("TEXT_MESSAGE_START") == 1
    assert [event["type"] for event in events].count("TEXT_MESSAGE_END") == 1


@pytest.mark.asyncio
async def test_converter_normalizes_cumulative_appended_text_chunks() -> None:
    events = await collect_stream([
        make_text_artifact("안", last_chunk=False, append=False, artifact_id="artifact-text-123"),
        make_text_artifact("안녕", last_chunk=False, append=True, artifact_id="artifact-text-123"),
        make_text_artifact("안녕", last_chunk=True, append=True, artifact_id="artifact-text-123"),
    ])

    assert [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]
    assert [event["type"] for event in events] == [
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_END",
    ]


@pytest.mark.asyncio
async def test_runtime_backed_executor_cumulative_text_stream_emits_delta_chunks_once() -> None:
    events = await execute_and_collect_stream(
        [
            make_text_adk_event("안", is_final=False),
            make_text_adk_event("안녕", is_final=False),
            make_text_adk_event("안녕", is_final=True),
        ]
    )

    assert [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]
    assert [event["type"] for event in events].count("TEXT_MESSAGE_END") == 1


@pytest.mark.asyncio
async def test_runtime_backed_executor_multi_part_final_event_stays_one_assistant_turn() -> None:
    events = await execute_and_collect_stream(
        [
            make_multi_text_adk_event(["안", "녕"], is_final=True),
        ]
    )

    assert [event["type"] for event in events] == [
        "STEP_STARTED",
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_END",
        "STEP_FINISHED",
    ]
    assert [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"] == ["안", "녕"]
    assert [event["type"] for event in events].count("TEXT_MESSAGE_START") == 1
    assert [event["type"] for event in events].count("TEXT_MESSAGE_END") == 1


async def test_working_status_produces_step_started():
    """working 상태 → STEP_STARTED 이벤트."""
    events = await collect_stream([make_task_status("working")])
    types = [e["type"] for e in events]
    assert "STEP_STARTED" in types


async def test_completed_status_produces_step_finished():
    """completed 상태 → STEP_FINISHED 이벤트."""
    events = await collect_stream([make_task_status("completed")])
    types = [e["type"] for e in events]
    assert "STEP_FINISHED" in types


async def test_empty_stream_produces_no_events():
    """빈 A2A 스트림 → 이벤트 없음."""
    events = await collect_stream([])
    assert events == []


async def test_state_delta_artifact_produces_state_delta_event():
    """STATE_DELTA DataPart → STATE_DELTA SSE 이벤트 변환."""
    events = await collect_stream([
        make_data_artifact({
            "_agui_event": "STATE_DELTA",
            "delta": [
                {"op": "replace", "path": "/travel_context/destination", "value": "도쿄"},
                {"op": "replace", "path": "/agent_status/current_intent", "value": "searching"},
            ],
        })
    ])
    delta_event = next(e for e in events if e["type"] == "STATE_DELTA")
    assert delta_event["delta"][0]["path"] == "/travel_context/destination"
    assert delta_event["delta"][1]["value"] == "searching"


@pytest.mark.asyncio
async def test_runtime_backed_executor_stream_emits_state_delta_and_snapshot_events():
    events = await execute_and_collect_stream(
        [
            make_function_call_adk_event(
                "search_hotels",
                {
                    "city": "도쿄",
                    "check_in": "2026-06-10",
                    "check_out": "2026-06-14",
                    "guests": 2,
                },
            ),
            make_function_response_adk_event(
                "search_hotels",
                {"status": "success", "hotels": [{"code": "HTL001", "name": "신주쿠 호텔"}]},
            ),
        ]
    )

    types = [event["type"] for event in events]
    assert "STATE_DELTA" in types
    assert "STATE_SNAPSHOT" in types
    assert "TOOL_CALL_START" in types
    assert "TOOL_CALL_END" in types
    assert types.index("STATE_DELTA") < types.index("TOOL_CALL_START")
    assert types.index("TOOL_CALL_END") < types.index("STATE_SNAPSHOT")

    snapshot_event = next(event for event in events if event["type"] == "STATE_SNAPSHOT")
    assert snapshot_event["snapshot"]["snapshot_type"] == "tool_result"
    assert snapshot_event["snapshot"]["tool"] == "search_hotels"


@pytest.mark.asyncio
async def test_runtime_backed_executor_ignores_partial_function_call_events() -> None:
    events = await execute_and_collect_stream(
        [
            make_function_call_adk_event(
                "request_user_favorite",
                {"favorite_type": "hotel_preference"},
                partial=True,
            ),
            make_function_call_adk_event(
                "request_user_favorite",
                {"favorite_type": "hotel_preference"},
                partial=False,
            ),
        ]
    )

    tool_call_starts = [event for event in events if event["type"] == "TOOL_CALL_START"]
    tool_call_args = [event for event in events if event["type"] == "TOOL_CALL_ARGS"]

    assert len(tool_call_starts) == 1
    assert len(tool_call_args) == 1
    assert tool_call_starts[0]["toolCallName"] == "request_user_favorite"


@pytest.mark.asyncio
async def test_runtime_backed_executor_stream_emits_user_input_request_event():
    events = await execute_and_collect_stream(
        [
            make_function_response_adk_event(
                "request_user_input",
                {
                    "status": "user_input_required",
                    "input_type": "hotel_booking_details",
                    "fields": [{"name": "check_in", "type": "date"}],
                },
            )
        ]
    )

    request_event = next(event for event in events if event["type"] == "USER_INPUT_REQUEST")
    assert request_event["input_type"] == "hotel_booking_details"
    assert request_event["fields"] == [{"name": "check_in", "type": "date"}]


@pytest.mark.asyncio
async def test_runtime_backed_executor_stream_emits_user_favorite_request_event():
    events = await execute_and_collect_stream(
        [
            make_function_response_adk_event(
                "request_user_favorite",
                {
                    "status": "user_favorite_required",
                    "favorite_type": "hotel_preference",
                    "options": {"hotel_grade": {"choices": ["4성", "5성"]}},
                },
            )
        ]
    )

    favorite_event = next(event for event in events if event["type"] == "USER_FAVORITE_REQUEST")
    assert favorite_event["favoriteType"] == "hotel_preference"
    assert favorite_event["options"] == {"hotel_grade": {"choices": ["4성", "5성"]}}
