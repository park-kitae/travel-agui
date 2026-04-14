"""
test_snapshot_emission.py — executor.py가 StateManager를 통해
agent_state snapshot을 TOOL_CALL_START 전에 발행하는지 검증
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from executor import ADKAgentExecutor


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


@pytest.mark.asyncio
async def test_agent_state_snapshot_enqueued_before_tool_call_start():
    """apply_tool_call이 반환한 snapshot이 TOOL_CALL_START DataPart보다 먼저 enqueue된다."""
    from ag_ui.core.events import StateSnapshotEvent, EventType

    mock_snapshot_event = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "agent_state", "travel_context": {}, "agent_status": {}},
    )

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_function_call_event("search_hotels", {"city": "도쿄"})
    )
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    mock_state_manager = MagicMock()

    async def mock_apply_tool_call(*args, **kwargs):
        yield mock_snapshot_event

    mock_state_manager.apply_tool_call = mock_apply_tool_call
    mock_state_manager.get_tc_id.return_value = "test-tc-id"

    async def mock_apply_tool_result(*args, **kwargs):
        return
        yield  # async generator

    mock_state_manager.apply_tool_result = mock_apply_tool_result

    with patch("executor.state_manager", mock_state_manager):
        executor = ADKAgentExecutor(mock_runner, mock_session_service)
        mock_queue = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.task_id = "t1"
        mock_ctx.context_id = "c1"
        mock_ctx.get_user_input.return_value = "도쿄 호텔"

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

    keys = [d.get("snapshot_type") or d.get("_agui_event") for d in data_list]
    assert "agent_state" in keys
    assert "TOOL_CALL_START" in keys
    assert keys.index("agent_state") < keys.index("TOOL_CALL_START")


@pytest.mark.asyncio
async def test_tool_result_snapshot_enqueued_after_tool_call_end():
    """apply_tool_result이 반환한 snapshot이 TOOL_CALL_END DataPart 이후에 enqueue된다."""
    from ag_ui.core.events import StateSnapshotEvent, EventType

    mock_snapshot_event = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "tool_result", "tool": "search_hotels", "result": {}},
    )

    fr = MagicMock()
    fr.name = "search_hotels"
    fr.response = {"status": "success", "hotels": []}

    part = MagicMock()
    part.text = None
    part.function_call = None
    part.function_response = fr

    content = MagicMock()
    content.parts = [part]

    adk_event = MagicMock()
    adk_event.content = content
    adk_event.is_final_response.return_value = False

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(adk_event)
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    mock_state_manager = MagicMock()

    async def mock_apply_tool_call(*args, **kwargs):
        return
        yield

    mock_state_manager.apply_tool_call = mock_apply_tool_call

    async def mock_apply_tool_result(*args, **kwargs):
        yield mock_snapshot_event

    mock_state_manager.apply_tool_result = mock_apply_tool_result
    mock_state_manager.get_tc_id.return_value = "tc-id-999"

    with patch("executor.state_manager", mock_state_manager):
        executor = ADKAgentExecutor(mock_runner, mock_session_service)
        mock_queue = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.task_id = "t2"
        mock_ctx.context_id = "c2"
        mock_ctx.get_user_input.return_value = "test"

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

    keys = [d.get("snapshot_type") or d.get("_agui_event") for d in data_list]
    assert "TOOL_CALL_END" in keys
    assert "tool_result" in keys
    assert keys.index("TOOL_CALL_END") < keys.index("tool_result")
