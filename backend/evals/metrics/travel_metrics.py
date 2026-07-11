"""Travel evaluation metrics."""
from __future__ import annotations

from typing import Any


def build_metrics(metric_name: str = "travel_correctness") -> list[Any]:
    if metric_name != "travel_correctness":
        raise ValueError(f"unsupported metric: {metric_name}")

    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCaseParams

    from evals.judge import get_judge

    judge = get_judge()
    return [
        GEval(
            name="TravelResponseCorrectness",
            criteria=(
                "주어진 사용자 입력에 대해 에이전트 응답이 (1) 도메인에 맞는 행동을 보이고, "
                "(2) 필수 정보가 부족하면 그 정보를 명확히 되묻고, "
                "(3) hallucination 없이 사실 기반으로 답하는지를 평가한다."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=judge,
            threshold=0.7,
        )
    ]
