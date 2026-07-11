"""travel ADK 에이전트를 직접 호출해 최종 텍스트를 반환.

A2A/HTTP를 우회한다. 평가는 결정성을 위해 ADK Runner를 직접 구동한다.
도구 호출 경로 평가는 후속 단계(툴 콜렉트) 플랜에서 다룬다.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Optional

from domains.travel.plugin import get_plugin


EVAL_APP_NAME = "travel_eval"
EVAL_USER_ID = "eval_user"


def _new_session_id() -> str:
    return f"eval-{uuid.uuid4().hex[:8]}"


def run_travel_agent(user_input: str, session_id: Optional[str] = None) -> str:
    """travel 도메인 ADK 에이전트를 호출해 누적된 텍스트를 단일 문자열로 반환."""
    try:
        return asyncio.run(_run_async(user_input, session_id or _new_session_id()))
    except Exception as e:  # noqa: BLE001 - 의도적으로 모든 예외를 wrap
        raise RuntimeError(f"travel agent failed for input={user_input!r}: {e}") from e


async def _run_async(user_input: str, session_id: str) -> str:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as adk_types

    plugin = get_plugin()
    agent = plugin.build_agent()
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=EVAL_APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    await session_service.create_session(
        app_name=EVAL_APP_NAME,
        user_id=EVAL_USER_ID,
        session_id=session_id,
    )

    text_parts: list[str] = []
    async for event in runner.run_async(
        user_id=EVAL_USER_ID,
        session_id=session_id,
        new_message=adk_types.Content(
            role="user",
            parts=[adk_types.Part(text=user_input)],
        ),
    ):
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)

    final_text = "".join(text_parts)
    if not final_text:
        raise RuntimeError(f"empty agent output for input={user_input!r}")
    return final_text
