"""Summarize the latest eval result JSON file."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def summarize_latest(results_dir: str | Path | None = None) -> dict[str, Any]:
    results_dir = Path(results_dir or Path(__file__).resolve().parent / "results")
    json_files = sorted(results_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No eval result files found in {results_dir}")

    latest_path = json_files[-1]
    payload = json.loads(latest_path.read_text(encoding="utf-8"))
    return {
        "file": str(latest_path),
        "average_score": payload.get("average_score"),
        "passed": payload.get("passed"),
        "results": payload.get("results", []),
    }


if __name__ == "__main__":
    from pprint import pprint

    pprint(summarize_latest())
