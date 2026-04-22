"""
test_snapshot_emission.py — executor.py가 runtime typed emission을 통해
상태/스냅샷 이벤트를 올바른 순서로 발행하는지 검증
"""
import pytest  # type: ignore[reportMissingImports]
from unittest.mock import AsyncMock, MagicMock

from domain_runtime import DomainRuntime
from domains.travel.plugin import get_plugin
from executor import ADKAgentExecutor
from state.store import SerializedStateStore


def _make_function_call_event(tool_name: str, args: dict):
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
    event.is_final_response.return_value = False
    return event


async def _async_gen(*items):
    for item in items:
        yield item


def _make_function_response_event(tool_name: str, response: dict):
    fr = MagicMock()
    fr.name = tool_name
    fr.response = response

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


def _make_runtime() -> DomainRuntime:
    return DomainRuntime(plugin=get_plugin(), state_store=SerializedStateStore())


@pytest.mark.asyncio
async def test_runtime_state_delta_enqueued_before_tool_call_start():
    """runtime apply_tool_call emission이 TOOL_CALL_START DataPart보다 먼저 enqueue된다."""
    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_function_call_event("search_hotels", {"city": "도쿄"})
    )
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()
    runtime = _make_runtime()

    executor = ADKAgentExecutor(mock_runner, mock_session_service, runtime=runtime)
    mock_queue = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.task_id = "t1"
    mock_ctx.context_id = "c1"
    mock_ctx.get_user_input.return_value = "도쿄 호텔"
    mock_ctx.metadata = {}

    await executor.execute(mock_ctx, mock_queue)

    calls = mock_queue.enqueue_event.call_args_list
    data_list = []
    for call in calls:
        event = call[0][0]
        if hasattr(event, "artifact") and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, "root") else p
                if hasattr(root, "data") and isinstance(root.data, dict):
                    data_list.append(root.data)

    keys = [d.get("_agui_event") or d.get("snapshot_type") for d in data_list]
    assert "STATE_DELTA" in keys
    assert "TOOL_CALL_START" in keys
    assert keys.index("STATE_DELTA") < keys.index("TOOL_CALL_START")


@pytest.mark.asyncio
async def test_tool_result_snapshot_enqueued_after_tool_call_end():
    """runtime apply_tool_result emission이 TOOL_CALL_END DataPart 이후에 enqueue된다."""

    adk_call_event = _make_function_call_event("search_hotels", {"city": "도쿄"})
    adk_response_event = _make_function_response_event(
        "search_hotels", {"status": "success", "hotels": []}
    )

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(adk_call_event, adk_response_event)
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()
    runtime = _make_runtime()

    executor = ADKAgentExecutor(mock_runner, mock_session_service, runtime=runtime)
    mock_queue = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.task_id = "t2"
    mock_ctx.context_id = "c2"
    mock_ctx.get_user_input.return_value = "test"
    mock_ctx.metadata = {}

    await executor.execute(mock_ctx, mock_queue)

    calls = mock_queue.enqueue_event.call_args_list
    data_list = []
    for call in calls:
        event = call[0][0]
        if hasattr(event, "artifact") and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, "root") else p
                if hasattr(root, "data") and isinstance(root.data, dict):
                    data_list.append(root.data)

    keys = [d.get("_agui_event") or d.get("snapshot_type") for d in data_list]
    assert "TOOL_CALL_END" in keys
    assert "tool_result" in keys
    assert keys.index("TOOL_CALL_END") < keys.index("tool_result")


@pytest.mark.asyncio
async def test_agent_state_snapshot_preserves_user_preferences_from_client_metadata():
    """executor는 runtime state에 client_state를 반영한 뒤 관련 STATE_DELTA를 발행해야 한다."""
    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_function_call_event("request_user_input", {"input_type": "hotel_booking_details", "context": "도쿄"})
    )
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()
    runtime = _make_runtime()

    executor = ADKAgentExecutor(mock_runner, mock_session_service, runtime=runtime)
    mock_queue = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.task_id = "t3"
    mock_ctx.context_id = "thread-pref"
    mock_ctx.get_user_input.return_value = "도쿄 호텔 추천해줘"
    mock_ctx.metadata = {
        "client_state": {
            "user_preferences": {
                "hotel_grade": "4성",
                "hotel_type": "비즈니스",
                "amenities": ["수영장"],
            }
        }
    }

    await executor.execute(mock_ctx, mock_queue)

    data_list = []
    for call in mock_queue.enqueue_event.call_args_list:
        event = call[0][0]
        if hasattr(event, "artifact") and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, "root") else p
                if hasattr(root, "data") and isinstance(root.data, dict):
                    data_list.append(root.data)

    state_delta = next(d for d in data_list if d.get("_agui_event") == "STATE_DELTA")
    delta_by_path = {op["path"]: op for op in state_delta["delta"]}
    assert delta_by_path["/agent_status/current_intent"]["value"] == "collecting_hotel_params"
    assert "/user_preferences/hotel_grade" not in delta_by_path

    stored_state = runtime.get_state("thread-pref")
    assert stored_state.user_preferences.hotel_grade == "4성"
    assert stored_state.user_preferences.hotel_type == "비즈니스"
    assert stored_state.user_preferences.amenities == ("수영장",)
