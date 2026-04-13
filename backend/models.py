"""
models.py — 커스텀 AG-UI 이벤트 모델 정의
"""
from typing import Literal
from pydantic import BaseModel, Field


class UserInputRequestEvent(BaseModel):
    """사용자 입력 요청 이벤트 (AG-UI 확장)."""
    type: Literal["USER_INPUT_REQUEST"] = "USER_INPUT_REQUEST"
    request_id: str = Field(..., description="요청 ID")
    input_type: str = Field(..., description="입력 타입")
    fields: list[dict] = Field(..., description="폼 필드 정의")
