"""
a2a_server.py — ADK 에이전트를 A2A 프로토콜 서버로 래핑 (포트 8001)

흐름:
  A2A Client (main.py)
    → POST /           (message/stream)
    ← SSE stream       (A2A Events)
        → ADK Runner → Gemini + FunctionTools
"""
import uuid
import json
import logging
import uvicorn
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskState,
    TaskStatus,
    Artifact,
    Part,
    TextPart,
    DataPart,
)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as adk_types

from agent import create_travel_agent

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_NAME = "travel"
USER_ID = "web_user"


# ──────────────────────────────────────────────
# TravelContext 추출 헬퍼
# ──────────────────────────────────────────────

def _extract_travel_context(tool_name: str, args: dict) -> dict:
    """function_call args에서 TravelContext를 추출합니다."""
    ctx: dict = {
        "destination": None,
        "origin": None,
        "check_in": None,
        "check_out": None,
        "nights": None,
        "guests": None,
        "trip_type": None,
    }

    if tool_name == "search_hotels":
        ctx["destination"] = args.get("city")
        ctx["check_in"] = args.get("check_in")
        ctx["check_out"] = args.get("check_out")
        ctx["guests"] = args.get("guests")
        if ctx["check_in"] and ctx["check_out"]:
            try:
                from datetime import date
                ci = date.fromisoformat(ctx["check_in"])
                co = date.fromisoformat(ctx["check_out"])
                ctx["nights"] = (co - ci).days
            except Exception:
                pass

    elif tool_name == "search_flights":
        ctx["origin"] = args.get("origin")
        ctx["destination"] = args.get("destination")
        ctx["check_in"] = args.get("departure_date")
        ctx["guests"] = args.get("passengers")
        ctx["trip_type"] = "round_trip" if args.get("return_date") else "one_way"

    elif tool_name == "get_hotel_detail":
        pass  # hotel_code만 있음, travel context 없음

    elif tool_name == "get_travel_tips":
        ctx["destination"] = args.get("destination")

    elif tool_name == "request_user_input":
        input_type = args.get("input_type", "")
        context_val = args.get("context", "")
        if input_type == "hotel_booking_details" and context_val:
            ctx["destination"] = context_val
        elif input_type == "flight_booking_details" and context_val:
            parts = context_val.split("|")
            if len(parts) >= 2:
                ctx["origin"] = parts[0].strip()
                ctx["destination"] = parts[1].strip()

    return ctx


def _extract_agent_status(tool_name: str, args: dict) -> dict:
    """tool_name으로부터 agent_status를 추출합니다."""
    intent_map = {
        "search_hotels": "searching",
        "search_flights": "searching",
        "get_hotel_detail": "presenting_results",
        "get_travel_tips": "presenting_results",
        "request_user_input": None,  # input_type으로 결정
    }

    missing_fields_map = {
        "hotel_booking_details": ["check_in", "check_out", "guests"],
        "flight_booking_details": ["origin", "destination", "departure_date", "passengers"],
    }

    intent = intent_map.get(tool_name, "idle")
    missing: list = []

    if tool_name == "request_user_input":
        input_type = args.get("input_type", "")
        if "hotel" in input_type:
            intent = "collecting_hotel_params"
        else:
            intent = "collecting_flight_params"
        missing = missing_fields_map.get(input_type, [])

    return {
        "current_intent": intent or "idle",
        "missing_fields": missing,
        "active_tool": tool_name,
    }

# ──────────────────────────────────────────────
# ADK 에이전트 & 런너 초기화
# ──────────────────────────────────────────────

session_service = InMemorySessionService()
travel_agent = create_travel_agent()
runner = Runner(
    app_name=APP_NAME,
    agent=travel_agent,
    session_service=session_service,
)

# ──────────────────────────────────────────────
# A2A Agent Card
# ──────────────────────────────────────────────

agent_card = AgentCard(
    name="travel_agent",
    description="여행 AI 여행 상담 에이전트 — 호텔, 항공, 관광 정보 안내",
    url="http://localhost:8001/",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="hotel_search",
            name="호텔 검색",
            description="도시와 날짜로 호텔을 검색합니다",
            tags=["hotel", "search"],
        ),
        AgentSkill(
            id="flight_search",
            name="항공편 검색",
            description="출발지/목적지 항공편을 검색합니다",
            tags=["flight", "search"],
        ),
        AgentSkill(
            id="travel_tips",
            name="여행 팁",
            description="목적지 관광 정보 및 팁을 제공합니다",
            tags=["travel", "tips"],
        ),
    ],
)


# ──────────────────────────────────────────────
# ADK → A2A AgentExecutor 구현
# ──────────────────────────────────────────────

class ADKAgentExecutor(AgentExecutor):
    """
    ADK Runner를 A2A AgentExecutor로 래핑합니다.
    ADK 이벤트를 A2A TaskArtifactUpdateEvent / TaskStatusUpdateEvent 로 변환하여
    EventQueue에 적재합니다.
    """

    def __init__(self, adk_runner: Runner, adk_session_service: InMemorySessionService):
        self._runner = adk_runner
        self._session_service = adk_session_service

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        user_input = context.get_user_input()

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

        # ── ADK 실행 & 이벤트 변환 ─────────────────
        artifact_id = str(uuid.uuid4())
        has_text = False
        tool_call_map: dict[str, str] = {}  # function name → tool_call_id

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
                        tc_id = str(uuid.uuid4())
                        tool_call_map[fc.name] = tc_id
                        args_dict = dict(fc.args) if fc.args else {}

                        # agent_state STATE_SNAPSHOT 먼저 발행 (TOOL_CALL_START 전)
                        travel_ctx = _extract_travel_context(fc.name, args_dict)
                        agent_status = _extract_agent_status(fc.name, args_dict)
                        await event_queue.enqueue_event(
                            TaskArtifactUpdateEvent(
                                task_id=task_id,
                                context_id=context_id,
                                artifact=Artifact(
                                    artifact_id=str(uuid.uuid4()),
                                    parts=[Part(root=DataPart(data={
                                        "snapshot_type": "agent_state",
                                        "travel_context": travel_ctx,
                                        "agent_status": agent_status,
                                    }))],
                                ),
                                append=False,
                                last_chunk=False,
                            )
                        )

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
                    # 1) TOOL_CALL_END DataPart → main.py가 TOOL_CALL_END 이벤트 발행
                    # 2) tool result DataPart  → main.py가 STATE_SNAPSHOT 또는 USER_INPUT_REQUEST 이벤트 발행
                    elif hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        tc_id = tool_call_map.get(fr.name, str(uuid.uuid4()))

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

                        # 도구 결과 처리
                        if fr.response:
                            logger.info(f"[DEBUG] {fr.name} fr.response type={type(fr.response).__name__} keys={list(fr.response.keys()) if isinstance(fr.response, dict) else 'N/A'}")
                            if isinstance(fr.response, dict) and 'hotels' in fr.response:
                                logger.info(f"[DEBUG] first hotel keys={list(fr.response['hotels'][0].keys()) if fr.response['hotels'] else 'empty'}")
                            response_data = fr.response if isinstance(fr.response, dict) else {"raw": str(fr.response)}

                            # request_user_input 툴인 경우 USER_INPUT_REQUEST 이벤트 생성
                            if fr.name == "request_user_input" and response_data.get("status") == "user_input_required":
                                await event_queue.enqueue_event(
                                    TaskArtifactUpdateEvent(
                                        task_id=task_id,
                                        context_id=context_id,
                                        artifact=Artifact(
                                            artifact_id=str(uuid.uuid4()),
                                            parts=[Part(root=DataPart(data={
                                                "_agui_event": "USER_INPUT_REQUEST",
                                                "request_id": str(uuid.uuid4()),
                                                "input_type": response_data.get("input_type", ""),
                                                "fields": response_data.get("fields", []),
                                            }))],
                                        ),
                                        append=False,
                                        last_chunk=False,
                                    )
                                )
                            else:
                                # 일반 도구 결과 → STATE_SNAPSHOT (snapshot_type: "tool_result" 포함)
                                await event_queue.enqueue_event(
                                    TaskArtifactUpdateEvent(
                                        task_id=task_id,
                                        context_id=context_id,
                                        artifact=Artifact(
                                            artifact_id=str(uuid.uuid4()),
                                            parts=[Part(root=DataPart(data={
                                                "snapshot_type": "tool_result",
                                                "tool": fr.name,
                                                "result": response_data,
                                            }))],
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
                    status=TaskStatus(state=TaskState.failed, message={"error": str(e)}),
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


# ──────────────────────────────────────────────
# A2A Starlette 앱 조립
# ──────────────────────────────────────────────

executor = ADKAgentExecutor(
    adk_runner=runner,
    adk_session_service=session_service,
)

a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    ),
)

# .build() 로 실제 Starlette ASGI 앱 생성
app = a2a_app.build()

if __name__ == "__main__":
    logger.info("A2A 에이전트 서버 시작 (포트 8001)")
    uvicorn.run(app, host="0.0.0.0", port=8001)
