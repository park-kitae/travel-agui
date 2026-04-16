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
)

from ag_ui.core.events import (
    RunAgentInput,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    EventType,
)
from converter import a2a_to_agui_stream, encoder
from state import state_manager

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

        # 2. 클라이언트 state 반영
        raw_state = body.get("state") or {}
        async for snap_event in state_manager.apply_client_state(thread_id, raw_state):
            yield encoder.encode(snap_event)

        # 3. 컨텍스트 주입 (최신 state 조회)
        state = state_manager.get(thread_id)
        tc = state.travel_context
        ui = state.ui_context
        pref = state.user_preferences

        ctx_lines = []
        if ui.selected_hotel_code:
            ctx_lines.append(f"- 선택된 호텔 코드: {ui.selected_hotel_code}")
        if ui.selected_flight_id:
            ctx_lines.append(f"- 선택된 항공편 ID: {ui.selected_flight_id}")
        if tc.destination:
            ctx_lines.append(f"- 목적지: {tc.destination}")
        if tc.origin:
            ctx_lines.append(f"- 출발지: {tc.origin}")
        if tc.check_in:
            ctx_lines.append(f"- 체크인/출발일: {tc.check_in}")
        if tc.check_out:
            ctx_lines.append(f"- 체크아웃/귀국일: {tc.check_out}")
        if tc.nights:
            ctx_lines.append(f"- 숙박: {tc.nights}박")
        if tc.guests:
            ctx_lines.append(f"- 인원: {tc.guests}명")
        if tc.rooms:
            ctx_lines.append(f"- 객실 수: {tc.rooms}실")
        if tc.trip_type:
            ctx_lines.append(f"- 여행 유형: {tc.trip_type}")
        if tc.budget_range:
            ctx_lines.append(f"- 예산 수준: {tc.budget_range}")
        if tc.travel_purpose:
            purpose_label = {
                "leisure": "여가/관광",
                "business": "비즈니스",
                "honeymoon": "허니문",
                "family": "가족 여행",
            }.get(tc.travel_purpose, tc.travel_purpose)
            ctx_lines.append(f"- 여행 목적: {purpose_label}")

        # 취향 수집 완료 마커 — 채팅 히스토리 대신 state에서 직접 판단
        pref_lines = []
        hotel_pref_collected = any([pref.hotel_grade, pref.hotel_type, pref.amenities])
        flight_pref_collected = any([pref.seat_class, pref.seat_position, pref.meal_preference, pref.airline_preference])

        if hotel_pref_collected:
            hotel_pref_parts = []
            if pref.hotel_grade:
                hotel_pref_parts.append(f"등급: {pref.hotel_grade}")
            if pref.hotel_type:
                hotel_pref_parts.append(f"유형: {pref.hotel_type}")
            if pref.amenities:
                hotel_pref_parts.append(f"편의시설: {', '.join(pref.amenities)}")
            pref_lines.append(f"- 호텔 취향: {' / '.join(hotel_pref_parts)} [호텔 취향 수집 완료]")

        if flight_pref_collected:
            flight_pref_parts = []
            if pref.seat_class:
                flight_pref_parts.append(f"좌석 등급: {pref.seat_class}")
            if pref.seat_position:
                flight_pref_parts.append(f"좌석 위치: {pref.seat_position}")
            if pref.meal_preference:
                flight_pref_parts.append(f"기내식: {pref.meal_preference}")
            if pref.airline_preference:
                flight_pref_parts.append(f"선호 항공사: {', '.join(pref.airline_preference)}")
            pref_lines.append(f"- 항공 취향: {' / '.join(flight_pref_parts)} [항공 취향 수집 완료]")

        if ctx_lines or pref_lines:
            sections = []
            if ctx_lines:
                sections.append("[현재 여행 컨텍스트 - 이미 확인된 정보]\n" + "\n".join(ctx_lines))
            if pref_lines:
                sections.append("[사용자 취향 - 이미 수집 완료]\n" + "\n".join(pref_lines))
            context_block = "\n\n".join(sections)
            user_message = f"{context_block}\n\n사용자 요청: {user_message}"
            logger.info(f"[{thread_id}] 컨텍스트 주입: travel={ctx_lines}, prefs={pref_lines}")

        try:
            async with httpx.AsyncClient(timeout=120.0) as http_client:
                # 2. A2A 에이전트 카드 조회 후 클라이언트 생성
                card_resp = await http_client.get(
                    f"{A2A_SERVER_URL}/.well-known/agent.json"
                )
                card_resp.raise_for_status()
                agent_card = AgentCard.model_validate(card_resp.json())
                a2a_client = A2AClient(httpx_client=http_client, agent_card=agent_card)

                # 3. A2A 스트리밍 요청
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
