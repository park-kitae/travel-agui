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

import httpx  # type: ignore[reportMissingImports]
from fastapi import FastAPI, Request  # type: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware  # type: ignore[reportMissingImports]
from fastapi.responses import StreamingResponse  # type: ignore[reportMissingImports]
from dotenv import load_dotenv  # type: ignore[reportMissingImports]

from a2a.client import A2AClient  # type: ignore[reportMissingImports]
from a2a.types import (  # type: ignore[reportMissingImports]
    AgentCard,
    SendStreamingMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
)

from ag_ui.core.events import (  # type: ignore[reportMissingImports]
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    EventType,
)
from converter import a2a_to_agui_stream, encoder
from domain_runtime import get_runtime, initialize_runtime_or_die

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

    logger.info(f"[{thread_id}] 사용자 입력: {user_message[:80]}")

    async def event_stream() -> AsyncGenerator[str, None]:
        nonlocal user_message  # 외부 스코프의 user_message 사용
        # 1. RUN_STARTED
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            run_id=run_id,
            thread_id=thread_id,
        ))

        raw_state = body.get("state") or {}

        try:
            # 2. 클라이언트 state 반영 + 컨텍스트 주입
            initialize_runtime_or_die()
            runtime = get_runtime()
            prepared_request = runtime.prepare_request(thread_id, raw_state, user_message)
            user_message = prepared_request.user_message

            async with httpx.AsyncClient(timeout=120.0) as http_client:
                # 3. A2A 에이전트 카드 조회 후 클라이언트 생성
                card_resp = await http_client.get(
                    f"{A2A_SERVER_URL}/.well-known/agent.json"
                )
                card_resp.raise_for_status()
                agent_card = AgentCard.model_validate(card_resp.json())
                a2a_client = A2AClient(httpx_client=http_client, agent_card=agent_card)

                # 4. A2A 스트리밍 요청
                msg_kwargs: dict = {
                    "role": Role.user,
                    "parts": [Part(root=TextPart(text=user_message))],
                    "message_id": str(uuid.uuid4()),
                    "context_id": thread_id,
                }

                a2a_request = SendStreamingMessageRequest(
                    id=str(uuid.uuid4()),
                    params=MessageSendParams(
                        message=Message(**msg_kwargs),
                        metadata={"client_state": raw_state} if raw_state else None,
                    ),
                )

                a2a_stream = a2a_client.send_message_streaming(a2a_request)

                # 5. A2A → AG-UI 변환 스트림
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
    import uvicorn  # type: ignore[reportMissingImports]
    logger.info("AG-UI 게이트웨이 서버 시작 (포트 8000)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
