import os

import pytest

from evals.runner import run_all


@pytest.mark.eval
def test_run_all_smoke() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        pytest.skip("GOOGLE_API_KEY is required for deepeval evaluation")

    result = run_all(
        dataset_path="evals/datasets/travel_goldens.jsonl",
        metric_name="travel_correctness",
    )

    assert result["results"]
    assert all(item["status"] in {"queued", "passed", "failed", "error"} for item in result["results"])
