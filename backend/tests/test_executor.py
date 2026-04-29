# pyright: reportMissingImports=false
from unittest.mock import AsyncMock, MagicMock

import pytest

from a2a.types import TaskArtifactUpdateEvent  # type: ignore[reportMissingImports]
from google.adk.agents.run_config import StreamingMode  # type: ignore[reportMissingImports]

from executor import ADKAgentExecutor


async def _empty_runner_events():
    if False:
        yield None


def _make_text_adk_event(text: str, *, is_final: bool) -> MagicMock:
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


@pytest.mark.asyncio
async def test_execute_uses_runner_app_name_for_session_service() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(return_value=_empty_runner_events())

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=None)
    session_service.create_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    session_service.get_session.assert_awaited_once_with(
        app_name="runtime.plugin.app",
        user_id="web_user",
        session_id="ctx-1",
    )
    session_service.create_session.assert_awaited_once_with(
        app_name="runtime.plugin.app",
        user_id="web_user",
        session_id="ctx-1",
    )


@pytest.mark.asyncio
async def test_execute_passes_sse_run_config_to_runner() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(return_value=_empty_runner_events())

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    run_config = runner.run_async.call_args.kwargs["run_config"]
    assert run_config.streaming_mode == StreamingMode.SSE


@pytest.mark.asyncio
async def test_execute_suppresses_duplicate_final_text_chunk() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events(
            _make_text_adk_event("안", is_final=False),
            _make_text_adk_event("녕", is_final=False),
            _make_text_adk_event("안녕", is_final=True),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    text_artifacts = []
    for call in event_queue.enqueue_event.call_args_list:
        event = call.args[0]
        if not isinstance(event, TaskArtifactUpdateEvent):
            continue
        part = event.artifact.parts[0].root
        if getattr(part, "text", None):
            text_artifacts.append(event)

    assert [event.artifact.parts[0].root.text for event in text_artifacts] == ["안", "녕"]
    assert [event.append for event in text_artifacts] == [False, True]
    assert [event.last_chunk for event in text_artifacts] == [False, False]


@pytest.mark.asyncio
async def test_execute_emits_non_final_cumulative_text_before_suppressing_duplicate_final() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events(
            _make_text_adk_event("안", is_final=False),
            _make_text_adk_event("안녕", is_final=False),
            _make_text_adk_event("안녕", is_final=True),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    text_artifacts = []
    for call in event_queue.enqueue_event.call_args_list:
        event = call.args[0]
        if not isinstance(event, TaskArtifactUpdateEvent):
            continue
        part = event.artifact.parts[0].root
        if getattr(part, "text", None):
            text_artifacts.append(event)

    assert [event.artifact.parts[0].root.text for event in text_artifacts] == ["안", "녕"]
    assert [event.append for event in text_artifacts] == [False, True]
    assert [event.last_chunk for event in text_artifacts] == [False, False]


@pytest.mark.asyncio
async def test_execute_normalizes_cumulative_text_and_emits_terminal_boundary_for_suppressed_final() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events(
            _make_text_adk_event("안", is_final=False),
            _make_text_adk_event("안녕", is_final=False),
            _make_text_adk_event("안녕", is_final=True),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    text_artifacts = []
    for call in event_queue.enqueue_event.call_args_list:
        event = call.args[0]
        if not isinstance(event, TaskArtifactUpdateEvent):
            continue
        part = event.artifact.parts[0].root
        if hasattr(part, "text"):
            text_artifacts.append(event)

    assert [event.artifact.parts[0].root.text for event in text_artifacts] == ["안", "녕", ""]
    assert [event.append for event in text_artifacts] == [False, True, True]
    assert [event.last_chunk for event in text_artifacts] == [False, False, True]


async def _async_text_events(*events):
    for event in events:
        yield event


async def _async_text_events_then_error(*events):
    for event in events:
        yield event
    raise RuntimeError("runner exploded")


@pytest.mark.asyncio
async def test_execute_does_not_suppress_distinct_final_text_streams() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events(
            _make_text_adk_event("안녕", is_final=True),
            _make_text_adk_event("안녕", is_final=True),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    text_artifacts = []
    for call in event_queue.enqueue_event.call_args_list:
        event = call.args[0]
        if not isinstance(event, TaskArtifactUpdateEvent):
            continue
        part = event.artifact.parts[0].root
        if getattr(part, "text", None):
            text_artifacts.append(event)

    assert [event.artifact.parts[0].root.text for event in text_artifacts] == ["안녕", "안녕"]
    assert [event.append for event in text_artifacts] == [False, False]
    assert text_artifacts[0].artifact.artifact_id != text_artifacts[1].artifact.artifact_id


@pytest.mark.asyncio
async def test_execute_cleans_up_text_stream_state_after_success() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events(
            _make_text_adk_event("안", is_final=False),
            _make_text_adk_event("안", is_final=True),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    assert executor._text_stream_states == {}


@pytest.mark.asyncio
async def test_execute_cleans_up_text_stream_state_after_failure() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(
        return_value=_async_text_events_then_error(
            _make_text_adk_event("안", is_final=False),
        )
    )

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    assert executor._text_stream_states == {}
