"""
models.py — 커스텀 AG-UI 이벤트 모델 정의
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class UserInputRequestEvent(BaseModel):
    """사용자 입력 요청 이벤트 (AG-UI 확장)."""
    type: Literal["USER_INPUT_REQUEST"] = "USER_INPUT_REQUEST"
    request_id: str = Field(..., description="요청 ID")
    input_type: str = Field(..., description="입력 타입")
    fields: list[dict] = Field(..., description="폼 필드 정의")


class UserFavoriteRequestEvent(BaseModel):
    """사용자 취향 요청 이벤트 (AG-UI 확장)."""
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["USER_FAVORITE_REQUEST"] = "USER_FAVORITE_REQUEST"
    request_id: str = Field(..., alias="requestId", description="요청 ID")
    favorite_type: str = Field(..., alias="favoriteType", description="취향 타입: hotel_preference | flight_preference")
    options: dict = Field(..., description="취향 옵션 정의 {field_name: {type, label, choices}}")
