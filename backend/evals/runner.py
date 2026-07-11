"""Standalone DeepEval runner for the travel agent."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics.travel_metrics import build_metrics


@dataclass(slots=True)
class Golden:
    id: str
    input: str
    expected_output: str | None = None
    tags: tuple[str, ...] = ()


def load_goldens(dataset_path: str | Path) -> list[Golden]:
    path = Path(dataset_path)
    goldens: list[Golden] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            goldens.append(
                Golden(
                    id=str(payload.get("id") or f"row-{line_number}"),
                    input=str(payload["input"]),
                    expected_output=payload.get("expected_output"),
                    tags=tuple(payload.get("tags", [])),
                )
            )
    return goldens


def _extract_average_score(deepeval_result: Any) -> float | None:
    test_results = getattr(deepeval_result, "test_results", None)
    if not test_results:
        return None

    scores: list[float] = []
    for test_result in test_results:
        metrics_data = getattr(test_result, "metrics_data", None) or []
        for metric_data in metrics_data:
            score = getattr(metric_data, "score", None)
            if isinstance(score, (int, float)):
                scores.append(float(score))
    if not scores:
        return None
    return sum(scores) / len(scores)


def run_all(
    dataset_path: str | Path = "datasets/travel_goldens.jsonl",
    metric_name: str = "travel_correctness",
    fail_under: float | None = None,
) -> dict[str, Any]:
    dataset = Path(dataset_path)
    goldens = load_goldens(dataset)
    metrics = build_metrics(metric_name=metric_name)

    from deepeval.test_case import LLMTestCase

    try:
        from deepeval.evaluate import evaluate as deepeval_evaluate
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError("deepeval is not installed; run 'uv sync' first") from exc

    from .runners.travel_agent_runner import run_travel_agent

    test_cases: list[LLMTestCase] = []
    results: list[dict[str, Any]] = []
    for golden in goldens:
        actual_output = run_travel_agent(golden.input)
        testcase = LLMTestCase(
            input=golden.input,
            actual_output=actual_output,
            expected_output=golden.expected_output,
        )
        test_cases.append(testcase)
        results.append({
            "id": golden.id,
            "input": golden.input,
            "actual_output": actual_output,
            "expected_output": golden.expected_output,
            "status": "queued",
        })

    deepeval_result = deepeval_evaluate(test_cases=test_cases, metrics=metrics)
    average_score = _extract_average_score(deepeval_result)

    for index, test_result in enumerate(getattr(deepeval_result, "test_results", []) or []):
        if index >= len(results):
            break
        metrics_data = getattr(test_result, "metrics_data", None) or []
        scores = [float(getattr(metric_data, "score", 0.0) or 0.0) for metric_data in metrics_data]
        results[index]["status"] = "passed" if getattr(test_result, "success", False) else "failed"
        results[index]["score"] = scores[0] if scores else None

    payload = {
        "dataset": str(dataset),
        "metric": metric_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "average_score": average_score,
        "passed": average_score is not None and fail_under is not None and average_score >= fail_under,
        "deepeval_result": str(deepeval_result),
        "results": results,
    }

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Completed {len(goldens)} goldens against {metric_name}")
    print(f"Result written to {output_path}")
    print(deepeval_result)

    if fail_under is not None and average_score is not None and average_score < fail_under:
        raise RuntimeError(
            f"evaluation average score {average_score:.3f} is below fail_under {fail_under:.3f}"
        )

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DeepEval travel-agent evaluation")
    parser.add_argument("--dataset", default="datasets/travel_goldens.jsonl")
    parser.add_argument("--metric", default="travel_correctness")
    parser.add_argument("--fail-under", type=float, default=None)
    args = parser.parse_args()

    try:
        run_all(dataset_path=args.dataset, metric_name=args.metric, fail_under=args.fail_under)
    except Exception as exc:  # pragma: no cover - CLI hook
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
