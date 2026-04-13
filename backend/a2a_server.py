"""
a2a_server.py — ADK 에이전트를 A2A 프로토콜 서버로 래핑 (포트 8001)

흐름:
  A2A Client (main.py)
    → POST /           (message/stream)
    ← SSE stream       (A2A Events)
        → ADK Runner → Gemini + FunctionTools
"""
import logging
import uvicorn
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agent import create_travel_agent
from executor import ADKAgentExecutor, APP_NAME, USER_ID

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
