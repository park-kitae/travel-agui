"""
executor.py — ADK Runner를 A2A AgentExecutor로 래핑
"""
import uuid
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent, TaskStatusUpdateEvent,
    TaskState, TaskStatus, Artifact, Part, TextPart, DataPart,
)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as adk_types
from ag_ui.core.events import StateDeltaEvent, StateSnapshotEvent

from state import state_manager

logger = logging.getLogger(__name__)

APP_NAME = "travel"
USER_ID = "web_user"


def _state_event_to_data(event: StateSnapshotEvent | StateDeltaEvent) -> dict:
    if isinstance(event, StateDeltaEvent):
        return {
            "_agui_event": "STATE_DELTA",
            "delta": event.delta,
        }
    return event.snapshot


class ADKAgentExecutor(AgentExecutor):
    """ADK Runner를 A2A AgentExecutor로 래핑합니다."""

    def __init__(self, adk_runner: Runner, adk_session_service: InMemorySessionService):
        self._runner = adk_runner
        self._session_service = adk_session_service

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        user_input = context.get_user_input()
        client_state = getattr(context, "metadata", {}).get("client_state", {})

        logger.info(f"[{task_id}] ADK 실행 시작: {user_input[:80]}")

        # ── working 상태 알림 ──────────────────────
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=False,
                status=TaskStatus(state=TaskState.working),
            )
        )

        # ── ADK 세션 확보 ──────────────────────────
        session = await self._session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=context_id,
        )
        if session is None:
            session = await self._session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=context_id,
            )

        # 게이트웨이에서 전달한 client_state를 A2A 서버 프로세스의 state store에 동기화한다.
        async for _ in state_manager.apply_client_state(context_id, client_state):
            pass

        # ── ADK 실행 & 이벤트 변환 ─────────────────
        artifact_id = str(uuid.uuid4())
        has_text = False

        try:
            async for adk_event in self._runner.run_async(
                user_id=USER_ID,
                session_id=context_id,
                new_message=adk_types.Content(
                    role="user",
                    parts=[adk_types.Part(text=user_input)],
                ),
            ):
                if not (adk_event.content and adk_event.content.parts):
                    continue

                for part in adk_event.content.parts:
                    # 텍스트 청크
                    if hasattr(part, "text") and part.text:
                        has_text = True
                        is_last = adk_event.is_final_response()
                        await event_queue.enqueue_event(
                            TaskArtifactUpdateEvent(
                                task_id=task_id,
                                context_id=context_id,
                                artifact=Artifact(
                                    artifact_id=artifact_id,
                                    parts=[Part(root=TextPart(text=part.text))],
                                ),
                                append=True,
                                last_chunk=is_last,
                            )
                        )

                    # 함수 호출 (Tool Call 시작) → agent_state STATE_SNAPSHOT 먼저 발행 후 TOOL_CALL_START
                    elif hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        args_dict = dict(fc.args) if fc.args else {}

                        # agent_state STATE_SNAPSHOT 먼저 발행 (TOOL_CALL_START 전)
                        async for snap_event in state_manager.apply_tool_call(context_id, fc.name, args_dict):
                            await event_queue.enqueue_event(
                                TaskArtifactUpdateEvent(
                                    task_id=task_id,
                                    context_id=context_id,
                                    artifact=Artifact(
                                        artifact_id=str(uuid.uuid4()),
                                        parts=[Part(root=DataPart(data=_state_event_to_data(snap_event)))],
                                    ),
                                    append=False,
                                    last_chunk=False,
                                )
                            )

                        tc_id = state_manager.get_tc_id(context_id, fc.name)
                        await event_queue.enqueue_event(
                            TaskArtifactUpdateEvent(
                                task_id=task_id,
                                context_id=context_id,
                                artifact=Artifact(
                                    artifact_id=str(uuid.uuid4()),
                                    parts=[Part(root=DataPart(data={
                                        "_agui_event": "TOOL_CALL_START",
                                        "id": tc_id,
                                        "name": fc.name,
                                        "args": args_dict,
                                    }))],
                                ),
                                append=False,
                                last_chunk=False,
                            )
                        )

                    # 함수 응답 (Tool Call 종료 + 결과)
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        tc_id = state_manager.get_tc_id(context_id, fr.name)

                        # TOOL_CALL_END 신호
                        await event_queue.enqueue_event(
                            TaskArtifactUpdateEvent(
                                task_id=task_id,
                                context_id=context_id,
                                artifact=Artifact(
                                    artifact_id=str(uuid.uuid4()),
                                    parts=[Part(root=DataPart(data={
                                        "_agui_event": "TOOL_CALL_END",
                                        "id": tc_id,
                                    }))],
                                ),
                                append=False,
                                last_chunk=False,
                            )
                        )

                        if fr.response:
                            logger.info(f"[DEBUG] {fr.name} response type={type(fr.response).__name__}")
                            response_data = fr.response if isinstance(fr.response, dict) else {"raw": str(fr.response)}
                            async for snap_event in state_manager.apply_tool_result(context_id, fr.name, response_data):
                                await event_queue.enqueue_event(
                                    TaskArtifactUpdateEvent(
                                        task_id=task_id,
                                        context_id=context_id,
                                        artifact=Artifact(
                                            artifact_id=str(uuid.uuid4()),
                                            parts=[Part(root=DataPart(data=_state_event_to_data(snap_event)))],
                                        ),
                                        append=False,
                                        last_chunk=False,
                                    )
                                )

        except Exception as e:
            logger.error(f"ADK 실행 오류: {e}", exc_info=True)
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    final=True,
                    status=TaskStatus(state=TaskState.failed),
                )
            )
            return

        # ── completed 상태 알림 ────────────────────
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.completed),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        context_id = context.context_id or ""
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.canceled),
            )
        )
