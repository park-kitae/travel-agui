import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_load_goldens_parses_jsonl(tmp_path: Path) -> None:
    dataset_path = tmp_path / "goldens.jsonl"
    dataset_path.write_text(
        '{"id": "g1", "input": "hello", "expected_output": "hi", "tags": ["sample"]}\n',
        encoding="utf-8",
    )

    from evals.runner import load_goldens

    goldens = load_goldens(dataset_path)

    assert len(goldens) == 1
    assert goldens[0].id == "g1"
    assert goldens[0].input == "hello"


def test_run_all_enforces_fail_under(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_path = tmp_path / "goldens.jsonl"
    dataset_path.write_text('{"id": "g1", "input": "hello"}\n', encoding="utf-8")

    monkeypatch.setattr("evals.runner.build_metrics", lambda metric_name="travel_correctness": [])
    monkeypatch.setattr("evals.runners.travel_agent_runner.run_travel_agent", lambda user_input: "ok")

    class FakeMetricData:
        def __init__(self, score: float) -> None:
            self.score = score

    class FakeTestResult:
        def __init__(self, score: float) -> None:
            self.success = True
            self.metrics_data = [FakeMetricData(score)]

    class FakeEvaluationResult:
        def __init__(self, score: float) -> None:
            self.test_results = [FakeTestResult(score)]

    monkeypatch.setitem(
        sys.modules,
        "deepeval.evaluate",
        SimpleNamespace(evaluate=lambda **_: FakeEvaluationResult(0.4)),
    )

    from evals.runner import run_all

    with pytest.raises(RuntimeError, match="below fail_under"):
        run_all(dataset_path=dataset_path, fail_under=0.5)
