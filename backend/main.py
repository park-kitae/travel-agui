"""
main.py — AG-UI ↔ A2A 클라이언트 미들웨어 서버 (포트 8000)

흐름:
  React Client
    → POST /agui/run  (RunAgentInput)
    ← SSE stream      (AG-UI Events)
        → A2A Client → A2A Server (포트 8001)
            → ADK Runner → Gemini + FunctionTools
"""
import uuid
import logging
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    SendStreamingMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    TaskState,
)

from ag_ui.core.events import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    StepStartedEvent,
    StepFinishedEvent,
    TextMessageStartEvent,
    TextMessageChunkEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    StateSnapshotEvent,
    EventType,
)
from pydantic import BaseModel, Field
from typing import Literal

# USER_INPUT_REQUEST 이벤트 정의
class UserInputRequestEvent(BaseModel):
    type: Literal["USER_INPUT_REQUEST"] = "USER_INPUT_REQUEST"
    request_id: str = Field(..., description="요청 ID")
    input_type: str = Field(..., description="입력 타입")
    fields: list[dict] = Field(..., description="폼 필드 정의")
from ag_ui.encoder.encoder import EventEncoder

# ──────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# ──────────────────────────────────────────────

A2A_SERVER_URL = "http://localhost:8001"

app = FastAPI(title="Travel AG-UI / A2A Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

encoder = EventEncoder()


# ──────────────────────────────────────────────
# Helper: A2A Event → AG-UI Event 변환
# ──────────────────────────────────────────────

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

    async for response in a2a_stream:
        # result 꺼내기 (root → result)
        root = getattr(response, "root", response)
        result = getattr(root, "result", root)

        # ── 텍스트 아티팩트 청크 ─────────────────────
        if isinstance(result, TaskArtifactUpdateEvent):
            for part in result.artifact.parts:
                p = part.root if hasattr(part, "root") else part

                # 텍스트 파트
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
                    if result.last_chunk:
                        yield encoder.encode(TextMessageEndEvent(
                            type=EventType.TEXT_MESSAGE_END,
                            message_id=current_msg_id,
                        ))
                        current_msg_id = None

                # 데이터 파트 → _agui_event 필드로 분기
                elif hasattr(p, "data") and p.data:
                    data = p.data
                    agui_event = data.get("_agui_event") if isinstance(data, dict) else None

                    if agui_event == "TOOL_CALL_START":
                        import json as _json
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

                    else:
                        # tool result → STATE_SNAPSHOT
                        try:
                            yield encoder.encode(StateSnapshotEvent(
                                type=EventType.STATE_SNAPSHOT,
                                snapshot=data if isinstance(data, dict) else {"raw": str(data)},
                            ))
                        except Exception as e:
                            logger.warning(f"StateSnapshot 직렬화 실패: {e}")

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
                    current_msg_id = None
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
                current_msg_id = None

    # 스트림 종료 후 열린 메시지 정리
    if current_msg_id:
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=current_msg_id,
        ))


# ──────────────────────────────────────────────
# AG-UI 엔드포인트
# ──────────────────────────────────────────────

@app.post("/agui/run")
async def run_agent(request: Request):
    """
    AG-UI 표준 엔드포인트.
    RunAgentInput을 수신하고 A2A 서버로 전달한 뒤 AG-UI SSE 스트림으로 반환합니다.
    """
    body = await request.json()
    # id 없는 메시지에 uuid 자동 부여 (AG-UI BaseMessage 필수 필드)
    if "messages" in body and isinstance(body["messages"], list):
        for msg in body["messages"]:
            if isinstance(msg, dict) and "id" not in msg:
                msg["id"] = str(uuid.uuid4())
    agent_input = RunAgentInput(**body)

    thread_id = agent_input.thread_id or str(uuid.uuid4())
    run_id = agent_input.run_id or str(uuid.uuid4())

    # 마지막 사용자 메시지 추출
    user_message = ""
    for msg in reversed(agent_input.messages):
        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
        if role == "user":
            content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
            if isinstance(content, str):
                user_message = content
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        user_message = c.get("text", "")
                        break
            break

    if not user_message:
        user_message = "안녕하세요"

    # client_state 추출 (RunAgentInput.state 필드, 없으면 빈 dict)
    client_state: dict = {}
    raw_state = body.get("state")
    if isinstance(raw_state, dict) and raw_state:
        client_state = raw_state

    logger.info(f"[{thread_id}] 사용자 입력: {user_message[:80]}")

    async def event_stream() -> AsyncGenerator[str, None]:
        # 1. RUN_STARTED
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            run_id=run_id,
            thread_id=thread_id,
        ))

        try:
            async with httpx.AsyncClient(timeout=120.0) as http_client:
                # 2. A2A 에이전트 카드 조회 후 클라이언트 생성
                card_resp = await http_client.get(
                    f"{A2A_SERVER_URL}/.well-known/agent.json"
                )
                card_resp.raise_for_status()
                agent_card = AgentCard.model_validate(card_resp.json())
                a2a_client = A2AClient(httpx_client=http_client, agent_card=agent_card)

                # 3. A2A 스트리밍 요청 (client_state를 metadata로 전달)
                msg_kwargs: dict = {
                    "role": Role.user,
                    "parts": [Part(root=TextPart(text=user_message))],
                    "message_id": str(uuid.uuid4()),
                    "context_id": thread_id,
                }
                if client_state:
                    msg_kwargs["metadata"] = {"client_state": client_state}

                a2a_request = SendStreamingMessageRequest(
                    id=str(uuid.uuid4()),
                    params=MessageSendParams(
                        message=Message(**msg_kwargs),
                    ),
                )

                a2a_stream = a2a_client.send_message_streaming(a2a_request)

                # 4. A2A → AG-UI 변환 스트림
                async for ag_ui_event_str in a2a_to_agui_stream(a2a_stream, run_id, thread_id):
                    yield ag_ui_event_str

        except Exception as e:
            logger.error(f"A2A 통신 오류: {e}", exc_info=True)
            yield encoder.encode(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                code="A2A_ERROR",
            ))

        # 5. RUN_FINISHED
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            run_id=run_id,
            thread_id=thread_id,
        ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "a2a-client",
        "a2a_server": A2A_SERVER_URL,
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("AG-UI 게이트웨이 서버 시작 (포트 8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
