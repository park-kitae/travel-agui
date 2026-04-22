# pyright: reportMissingImports=false
from unittest.mock import AsyncMock, MagicMock

import pytest

from executor import ADKAgentExecutor


async def _empty_runner_events():
    if False:
        yield None


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
