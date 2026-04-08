import pytest
from unittest.mock import AsyncMock, MagicMock
from a2a_server import ADKAgentExecutor


def _make_adk_function_call_event(tool_name: str, args: dict):
    """a2a_server.py가 기대하는 ADK function_call 이벤트 mock 생성."""
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
async def test_agent_state_snapshot_emitted_before_tool_call():
    """function_call 감지 시 agent_state STATE_SNAPSHOT이 TOOL_CALL_START보다 먼저 발행되어야 한다."""
    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_adk_function_call_event("search_hotels", {"city": "도쿄", "check_in": "2026-06-10", "check_out": "2026-06-13", "guests": 2})
    )

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    executor = ADKAgentExecutor(mock_runner, mock_session_service)

    mock_event_queue = AsyncMock()
    mock_context = MagicMock()
    mock_context.task_id = "test-task"
    mock_context.context_id = "test-ctx"
    mock_context.get_user_input.return_value = "도쿄 호텔 찾아줘"

    await executor.execute(mock_context, mock_event_queue)

    calls = mock_event_queue.enqueue_event.call_args_list

    # 발행된 DataPart 이벤트들 추출
    data_parts = []
    for call in calls:
        event = call[0][0]
        if hasattr(event, 'artifact') and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, 'root') else p
                if hasattr(root, 'data') and root.data:
                    data_parts.append(root.data)

    snap_types = [d.get("snapshot_type") or d.get("_agui_event") for d in data_parts]

    # agent_state가 TOOL_CALL_START보다 앞에 있어야 함
    assert "agent_state" in snap_types, f"agent_state snapshot 미발행. 발행 순서: {snap_types}"
    assert "TOOL_CALL_START" in snap_types, f"TOOL_CALL_START 미발행. 발행 순서: {snap_types}"

    agent_idx = snap_types.index("agent_state")
    tool_call_idx = snap_types.index("TOOL_CALL_START")
    assert agent_idx < tool_call_idx, \
        f"agent_state({agent_idx})가 TOOL_CALL_START({tool_call_idx})보다 먼저여야 함"


@pytest.mark.asyncio
async def test_agent_state_snapshot_contains_travel_context():
    """agent_state snapshot의 travel_context에 올바른 값이 포함되어야 한다."""
    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_adk_function_call_event("search_hotels", {"city": "오사카", "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 3})
    )

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    executor = ADKAgentExecutor(mock_runner, mock_session_service)
    mock_event_queue = AsyncMock()
    mock_context = MagicMock()
    mock_context.task_id = "t1"
    mock_context.context_id = "c1"
    mock_context.get_user_input.return_value = "오사카 호텔"

    await executor.execute(mock_context, mock_event_queue)

    agent_state_data = None
    for call in mock_event_queue.enqueue_event.call_args_list:
        event = call[0][0]
        if hasattr(event, 'artifact') and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, 'root') else p
                if hasattr(root, 'data') and isinstance(root.data, dict):
                    if root.data.get("snapshot_type") == "agent_state":
                        agent_state_data = root.data
                        break

    assert agent_state_data is not None, "agent_state snapshot이 발행되지 않음"
    tc = agent_state_data["travel_context"]
    assert tc["destination"] == "오사카"
    assert tc["check_in"] == "2026-07-01"
    assert tc["nights"] == 3
    assert tc["guests"] == 3


@pytest.mark.asyncio
async def test_tool_result_snapshot_has_snapshot_type_field():
    """tool result STATE_SNAPSHOT에 snapshot_type: 'tool_result' 필드가 포함되어야 한다."""
    from unittest.mock import MagicMock, AsyncMock

    # function_response 이벤트 mock
    fr = MagicMock()
    fr.name = "search_hotels"
    fr.response = {"status": "success", "hotels": []}

    part = MagicMock()
    part.text = None
    part.function_call = None
    part.function_response = fr

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.is_final_response.return_value = False

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(event)

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    executor = ADKAgentExecutor(mock_runner, mock_session_service)
    mock_event_queue = AsyncMock()
    mock_context = MagicMock()
    mock_context.task_id = "t2"
    mock_context.context_id = "c2"
    mock_context.get_user_input.return_value = "test"

    await executor.execute(mock_context, mock_event_queue)

    tool_result_found = False
    for call in mock_event_queue.enqueue_event.call_args_list:
        event_arg = call[0][0]
        if hasattr(event_arg, 'artifact') and event_arg.artifact and event_arg.artifact.parts:
            for p in event_arg.artifact.parts:
                root = p.root if hasattr(p, 'root') else p
                if hasattr(root, 'data') and isinstance(root.data, dict):
                    if root.data.get("snapshot_type") == "tool_result":
                        tool_result_found = True
                        assert root.data.get("tool") == "search_hotels"
                        break

    assert tool_result_found, "snapshot_type: 'tool_result' 필드가 포함된 이벤트가 발행되지 않음"
