"""
converter.py — A2A 스트리밍 이벤트를 AG-UI SSE 이벤트로 변환
"""
import uuid
import json as _json
import logging
from typing import AsyncGenerator

from a2a.types import TaskStatusUpdateEvent, TaskArtifactUpdateEvent, TaskState, TextPart
from ag_ui.core.events import (
    EventType,
    TextMessageStartEvent, TextMessageChunkEvent, TextMessageEndEvent,
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent,
    StepStartedEvent, StepFinishedEvent,
    StateSnapshotEvent, StateDeltaEvent,
)
from ag_ui.encoder.encoder import EventEncoder

from models import UserInputRequestEvent, UserFavoriteRequestEvent

logger = logging.getLogger(__name__)

# main.py의 encoder 인스턴스를 이전 — main.py에서 import해서 재사용
encoder = EventEncoder()


async def a2a_to_agui_stream(
    a2a_stream: AsyncGenerator,
    run_id: str,
    thread_id: str,
) -> AsyncGenerator[str, None]:
    """
    A2A 서버의 스트리밍 응답을 AG-UI SSE 이벤트로 변환합니다.

    SendStreamingMessageResponse.root 는
      SendStreamingMessageSuccessResponse 이고,
      그 .result 가 Task | Message | TaskStatusUpdateEvent | TaskArtifactUpdateEvent 입니다.
    """
    current_msg_id: str | None = None
    current_artifact_id: str | None = None
    current_artifact_text = ""

    def reset_text_stream() -> None:
        nonlocal current_msg_id, current_artifact_id, current_artifact_text
        current_msg_id = None
        current_artifact_id = None
        current_artifact_text = ""

    def update_text_delta(text: str, *, append: bool, artifact_id: str | None) -> str:
        nonlocal current_artifact_id, current_artifact_text
        if not append or artifact_id != current_artifact_id:
            current_artifact_id = artifact_id
            current_artifact_text = text
            return text
        if current_artifact_text and text.startswith(current_artifact_text):
            delta = text[len(current_artifact_text):]
            current_artifact_text = text
            return delta
        current_artifact_text += text
        return text

    async for response in a2a_stream:
        # result 꺼내기 (root → result)
        root = getattr(response, "root", response)
        result = getattr(root, "result", root)

        # ── 텍스트 아티팩트 청크 ─────────────────────
        if isinstance(result, TaskArtifactUpdateEvent):
            artifact_id = getattr(result.artifact, "artifact_id", None)
            append = getattr(result, "append", False)
            for part in result.artifact.parts:
                p = part.root if hasattr(part, "root") else part

                # 텍스트 파트
                if isinstance(p, TextPart):
                    if p.text:
                        if current_msg_id is not None and artifact_id != current_artifact_id and not append:
                            yield encoder.encode(TextMessageEndEvent(
                                type=EventType.TEXT_MESSAGE_END,
                                message_id=current_msg_id,
                            ))
                            reset_text_stream()
                        if current_msg_id is None:
                            current_msg_id = str(uuid.uuid4())
                            current_artifact_id = artifact_id
                            current_artifact_text = ""
                            yield encoder.encode(TextMessageStartEvent(
                                type=EventType.TEXT_MESSAGE_START,
                                message_id=current_msg_id,
                                role="assistant",
                            ))
                        delta = update_text_delta(p.text, append=append, artifact_id=artifact_id)
                        if delta:
                            yield encoder.encode(TextMessageChunkEvent(
                                type=EventType.TEXT_MESSAGE_CHUNK,
                                message_id=current_msg_id,
                                delta=delta,
                            ))

                # 데이터 파트 → _agui_event 필드로 분기
                elif hasattr(p, "data") and p.data:
                    data = p.data
                    agui_event = data.get("_agui_event") if isinstance(data, dict) else None

                    if agui_event == "TOOL_CALL_START":
                        tc_id = data["id"]
                        tc_name = data["name"]
                        args_str = _json.dumps(data.get("args", {}), ensure_ascii=False)
                        yield encoder.encode(ToolCallStartEvent(
                            type=EventType.TOOL_CALL_START,
                            tool_call_id=tc_id,
                            tool_call_name=tc_name,
                            parent_message_id=current_msg_id,
                        ))
                        yield encoder.encode(ToolCallArgsEvent(
                            type=EventType.TOOL_CALL_ARGS,
                            tool_call_id=tc_id,
                            delta=args_str,
                        ))

                    elif agui_event == "TOOL_CALL_END":
                        tc_id = data["id"]
                        yield encoder.encode(ToolCallEndEvent(
                            type=EventType.TOOL_CALL_END,
                            tool_call_id=tc_id,
                        ))

                    elif agui_event == "USER_INPUT_REQUEST":
                        # 사용자 입력 요청 이벤트
                        try:
                            yield encoder.encode(UserInputRequestEvent(
                                type="USER_INPUT_REQUEST",
                                request_id=data.get("request_id", ""),
                                input_type=data.get("input_type", ""),
                                fields=data.get("fields", []),
                            ))
                        except Exception as e:
                            logger.warning(f"UserInputRequest 직렬화 실패: {e}")

                    elif agui_event == "USER_FAVORITE_REQUEST":
                        # 사용자 취향 요청 이벤트
                        try:
                            event_data = UserFavoriteRequestEvent(
                                request_id=data.get("request_id", str(uuid.uuid4())),
                                favorite_type=data.get("favorite_type", ""),
                                options=data.get("options", {}),
                            )
                            yield encoder.encode(event_data)
                        except Exception as e:
                            logger.warning(f"UserFavoriteRequest 직렬화 실패: {e}")

                    elif agui_event == "STATE_DELTA":
                        try:
                            yield encoder.encode(StateDeltaEvent(
                                type=EventType.STATE_DELTA,
                                delta=data.get("delta", []),
                            ))
                        except Exception as e:
                            logger.warning(f"StateDelta 직렬화 실패: {e}")

                    else:
                        # tool result → STATE_SNAPSHOT
                        try:
                            yield encoder.encode(StateSnapshotEvent(
                                type=EventType.STATE_SNAPSHOT,
                                snapshot=data if isinstance(data, dict) else {"raw": str(data)},
                            ))
                        except Exception as e:
                            logger.warning(f"StateSnapshot 직렬화 실패: {e}")

            if result.last_chunk and current_msg_id is not None:
                yield encoder.encode(TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=current_msg_id,
                ))
                reset_text_stream()

        # ── 태스크 상태 업데이트 ─────────────────────
        elif isinstance(result, TaskStatusUpdateEvent):
            state = result.status.state

            if state == TaskState.working:
                yield encoder.encode(StepStartedEvent(
                    type=EventType.STEP_STARTED,
                    step_name="에이전트 처리 중",
                ))
            elif state in (TaskState.completed, TaskState.failed, TaskState.canceled):
                if current_msg_id:
                    yield encoder.encode(TextMessageEndEvent(
                        type=EventType.TEXT_MESSAGE_END,
                        message_id=current_msg_id,
                    ))
                    reset_text_stream()
                yield encoder.encode(StepFinishedEvent(
                    type=EventType.STEP_FINISHED,
                    step_name="에이전트 완료",
                ))

        # ── Message 객체 (non-streaming fallback) ────
        elif hasattr(result, "parts"):
            for part in result.parts:
                p = part.root if hasattr(part, "root") else part
                if isinstance(p, TextPart) and p.text:
                    if current_msg_id is None:
                        current_msg_id = str(uuid.uuid4())
                        yield encoder.encode(TextMessageStartEvent(
                            type=EventType.TEXT_MESSAGE_START,
                            message_id=current_msg_id,
                            role="assistant",
                        ))
                    yield encoder.encode(TextMessageChunkEvent(
                        type=EventType.TEXT_MESSAGE_CHUNK,
                        message_id=current_msg_id,
                        delta=p.text,
                    ))
            if current_msg_id:
                yield encoder.encode(TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=current_msg_id,
                ))
                reset_text_stream()

    # 스트림 종료 후 열린 메시지 정리
    if current_msg_id:
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=current_msg_id,
        ))
