"""
a2a_server.py — ADK 에이전트를 A2A 프로토콜 서버로 래핑 (포트 8001)

흐름:
  A2A Client (main.py)
    → POST /           (message/stream)
    ← SSE stream       (A2A Events)
        → ADK Runner → Gemini + FunctionTools
"""
import logging
import uvicorn  # type: ignore[reportMissingImports]
from dotenv import load_dotenv  # type: ignore[reportMissingImports]

from a2a.server.apps import A2AStarletteApplication  # type: ignore[reportMissingImports]
from a2a.server.request_handlers import DefaultRequestHandler  # type: ignore[reportMissingImports]
from a2a.server.tasks import InMemoryTaskStore  # type: ignore[reportMissingImports]
from google.adk.runners import Runner  # type: ignore[reportMissingImports]
from google.adk.sessions import InMemorySessionService  # type: ignore[reportMissingImports]

from domain_runtime import get_runtime, get_runtime_app_name, initialize_runtime_or_die
from executor import ADKAgentExecutor, USER_ID

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# ADK 에이전트 & 런너 초기화
# ──────────────────────────────────────────────

session_service = InMemorySessionService()
initialize_runtime_or_die()
runtime = get_runtime()
runner = Runner(
    app_name=get_runtime_app_name(runtime),
    agent=runtime.build_agent(),
    session_service=session_service,
)
agent_card = runtime.agent_card()


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
