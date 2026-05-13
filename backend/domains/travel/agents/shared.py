"""Shared helpers for travel-domain agent assembly."""

from __future__ import annotations

from collections.abc import Sequence

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


COMMON_RESPONSE_POLICY = """공통 응답 원칙:
- 한국어로 간결하게 응답합니다.
- 가격은 원화(원) 기준으로 안내합니다.
- 실제 예약은 처리하지 않고 정보만 제공합니다.
"""


def build_agent_instruction(role_summary: str, rules: Sequence[str]) -> str:
    lines = [role_summary, "", "규칙:"]
    lines.extend(f"- {rule}" for rule in rules)
    lines.extend(["", COMMON_RESPONSE_POLICY])
    return "\n".join(lines)


def create_domain_agent(
    *,
    name: str,
    description: str,
    instruction: str,
    tools: Sequence[object],
) -> LlmAgent:
    return LlmAgent(
        name=name,
        model="gemini-3-flash-preview",
        description=description,
        instruction=instruction,
        tools=[FunctionTool(tool) for tool in tools],
        disallow_transfer_to_parent=False,
        disallow_transfer_to_peers=False,
    )
