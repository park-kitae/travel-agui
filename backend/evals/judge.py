"""deepeval LLM judge 팩토리.

`GOOGLE_API_KEY`가 없으면 명확한 RuntimeError로 fail-fast 한다.
deepeval 자체는 lazy import — deepeval 미설치 환경에서도 import 자체는 성공한다.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def get_judge():
    """Gemini judge 인스턴스를 반환.

    환경 변수:
        GOOGLE_API_KEY: 필수. 없으면 RuntimeError.
        JUDGE_MODEL_NAME: 선택. 기본값 `gemini-2.0-flash`.
    """
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    from deepeval.models import GeminiModel  # lazy import

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "deepeval judge requires GOOGLE_API_KEY. backend/.env에 GOOGLE_API_KEY를 설정하세요."
        )
    model_name = os.environ.get("JUDGE_MODEL_NAME", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    return GeminiModel(model=model_name, api_key=api_key)
