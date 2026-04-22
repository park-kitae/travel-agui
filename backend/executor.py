"""
executor.py — ADK Runner를 A2A AgentExecutor로 래핑
"""
from __future__ import annotations

import uuid
import logging
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext  # type: ignore[reportMissingImports]
from a2a.server.events import EventQueue  # type: ignore[reportMissingImports]
from a2a.types import (  # type: ignore[reportMissingImports]
    TaskArtifactUpdateEvent, TaskStatusUpdateEvent,
    TaskState, TaskStatus, Artifact, Part, TextPart, DataPart,
)
from google.adk.runners import Runner  # type: ignore[reportMissingImports]
from google.adk.sessions import InMemorySessionService  # type: ignore[reportMissingImports]
from google.genai import types as adk_types  # type: ignore[reportMissingImports]

from domain_runtime import (
    DomainRuntime,
    get_runtime,
    get_runtime_app_name,
    initialize_runtime_or_die,
    map_runtime_emission_to_payload,
)

logger = logging.getLogger(__name__)

USER_ID = "web_user"


def _normalize_tool_result(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    return {"raw": str(response)}


class ADKAgentExecutor(AgentExecutor):
    """ADK Runner를 A2A AgentExecutor로 래핑합니다."""

    def __init__(
        self,
        adk_runner: Runner,
        adk_session_service: InMemorySessionService,
        runtime: DomainRuntime | None = None,
    ):
        self._runner = adk_runner
        self._session_service = adk_session_service
        if runtime is None:
            initialize_runtime_or_die()
            runtime = get_runtime()
        self._runtime = runtime
        self._app_name = get_runtime_app_name(adk_runner)
        self._tool_call_ids: dict[str, dict[str, str]] = {}

    async def _enqueue_data_artifact(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        data: dict[str, Any],
    ) -> None:
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id=str(uuid.uuid4()),
                    parts=[Part(root=DataPart(data=data))],
                ),
                append=False,
                last_chunk=False,
            )
        )

    async def _enqueue_runtime_emissions(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        emissions: list[Any],
    ) -> None:
        for emission in emissions:
            await self._enqueue_data_artifact(
                event_queue=event_queue,
                task_id=task_id,
                context_id=context_id,
                data=map_runtime_emission_to_payload(emission),
            )

    def _remember_tool_call_id(self, context_id: str, tool_name: str) -> str:
        tc_id = str(uuid.uuid4())
        self._tool_call_ids.setdefault(context_id, {})[tool_name] = tc_id
        return tc_id

    def _get_tool_call_id(self, context_id: str, tool_name: str) -> str:
        tool_calls = self._tool_call_ids.get(context_id, {})
        tc_id = tool_calls.pop(tool_name, None)
        if not tool_calls:
            self._tool_call_ids.pop(context_id, None)
        if tc_id is None:
            logger.warning(
                "[%s] missing tool call id for '%s'; emitting fallback id",
                context_id,
                tool_name,
            )
            return str(uuid.uuid4())
        return tc_id

    def _merge_client_state(self, context_id: str, client_state: dict[str, Any]) -> None:
        if not client_state:
            return
        current_state = self._runtime.get_state(context_id)
        merged_state = self._runtime.plugin.merge_client_state(current_state, client_state)
        self._runtime.set_state(context_id, merged_state)

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
            app_name=self._app_name,
            user_id=USER_ID,
            session_id=context_id,
        )
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=USER_ID,
                session_id=context_id,
            )

        # 게이트웨이에서 전달한 client_state를 runtime state store에 동기화한다.
        self._merge_client_state(context_id, client_state)

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

                        current_state = self._runtime.get_state(context_id)
                        next_state, emissions = self._runtime.plugin.apply_tool_call(
                            current_state,
                            fc.name,
                            args_dict,
                        )
                        self._runtime.set_state(context_id, next_state)
                        await self._enqueue_runtime_emissions(
                            event_queue=event_queue,
                            task_id=task_id,
                            context_id=context_id,
                            emissions=emissions,
                        )

                        tc_id = self._remember_tool_call_id(context_id, fc.name)
                        await self._enqueue_data_artifact(
                            event_queue=event_queue,
                            task_id=task_id,
                            context_id=context_id,
                            data={
                                "_agui_event": "TOOL_CALL_START",
                                "id": tc_id,
                                "name": fc.name,
                                "args": args_dict,
                            },
                        )

                    # 함수 응답 (Tool Call 종료 + 결과)
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        tc_id = self._get_tool_call_id(context_id, fr.name)

                        # TOOL_CALL_END 신호
                        await self._enqueue_data_artifact(
                            event_queue=event_queue,
                            task_id=task_id,
                            context_id=context_id,
                            data={
                                "_agui_event": "TOOL_CALL_END",
                                "id": tc_id,
                            },
                        )

                        if fr.response is not None:
                            logger.info(f"[DEBUG] {fr.name} response type={type(fr.response).__name__}")
                            response_data = _normalize_tool_result(fr.response)
                            current_state = self._runtime.get_state(context_id)
                            next_state, emissions = self._runtime.plugin.apply_tool_result(
                                current_state,
                                fr.name,
                                response_data,
                            )
                            self._runtime.set_state(context_id, next_state)
                            await self._enqueue_runtime_emissions(
                                event_queue=event_queue,
                                task_id=task_id,
                                context_id=context_id,
                                emissions=emissions,
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
