# DeepEval Introduction — Step 1 (Standalone Script) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** travel-agui 백엔드에 deepeval을 도입해, travel ADK 에이전트의 응답 품질을 `python -m evals.runner` 한 줄로 평가할 수 있는 독립 스크립트를 만든다.

**Architecture:**
- `backend/evals/` 디렉터리를 신설하고, 공통 엔진/도메인 plugin은 0줄 수정
- 평가는 A2A/HTTP를 우회해 ADK `LlmAgent`를 직접 호출하는 어댑터(`runners/travel_agent_runner.py`)로 수행
- judge는 기존 `GOOGLE_API_KEY`를 재사용하는 `GeminiModel`, 지표는 `travel_correctness` GEval 1개
- 단계 1은 pytest 통합 없이 **독립 스크립트**만 제공 (pytest 통합은 단계 2)

**Tech Stack:** deepeval 3.x, Google ADK (`LlmAgent`, `Runner`, `InMemorySessionService`), pydantic-free dataclass, Python 3.11+, uv

---

## Spec Reference

- 스펙: `docs/superpowers/specs/2026-07-11-deepeval-introduction-design.md`
- 이 플랜은 스펙의 **단계 1 — 간단 스크립트**만 다룬다. 단계 2~5는 별도 플랜.

---

## Out of Scope (이번 플랜)

- pytest 통합 (`backend/evals/tests/test_evals.py`) — 단계 2
- 데이터셋 8~12개 확장 — 단계 3
- `--fail-under` CI 게이트, 추가 metric — 단계 4
- tracing / 대시보드 — 단계 5
- 공통 엔진(`main.py`/`executor.py`/`converter.py`/`domain_runtime.py`/`a2a_server.py`) 수정
- 도메인 plugin (`backend/domains/travel/*`, `backend/domains/fake/*`) 수정

---

## 사전 준비 (engineer가 플랜 시작 전 확인)

1. `backend/.env`에 `GOOGLE_API_KEY`가 설정돼 있어야 한다 (이 플랜 말미에 실제 LLM 호출이 들어간다).
2. `cd backend && uv sync`가 깨끗이 통과한다.
3. 현재 작업 디렉터리는 `G:\dev\project\agent\ag_ui\travel-agui` 이고, 모든 `cd backend` 명령은 이 저장소 루트 기준이다.

---

## Task 1: 의존성 + 디렉터리 골격

**Files:**
- Modify: `backend/pyproject.toml:6-15` (dependencies 블록)
- Modify: `backend/.env.example` (JUDGE_MODEL_NAME 줄 추가)
- Create: `backend/evals/__init__.py`
- Create: `backend/evals/datasets/__init__.py`
- Create: `backend/evals/metrics/__init__.py`
- Create: `backend/evals/runners/__init__.py`

- [ ] **Step 1: `pyproject.toml`에 deepeval 추가**

`backend/pyproject.toml` 15번째 줄 `    "pydantic>=2.0.0",` 바로 뒤에 다음 한 줄을 추가한다.

```toml
    "pydantic>=2.0.0",
    "deepeval>=3.0.0,<4.0.0",
    "httpx>=0.27.0",
```

(즉, dependencies 리스트에 `deepeval>=3.0.0,<4.0.0`를 한 줄 삽입.)

- [ ] **Step 2: `uv sync`로 deepeval 설치**

Run:
```bash
cd backend && uv sync
```

Expected: `Resolved ... Installed ...` 로그 후 종료. deepeval이 `.venv`에 들어갔다는 메시지가 보여야 한다.

확인:
```bash
cd backend && uv run python -c "import deepeval; print(deepeval.__version__)"
```

Expected: `3.x.y` 형태의 버전 문자열 출력 (3.0 이상 4.0 미만).

- [ ] **Step 3: `.env.example`에 `JUDGE_MODEL_NAME` 추가**

`backend/.env.example` 파일 끝에 다음 한 줄을 추가한다 (이미 `# ...` 같은 주석이 있다면 그 뒤에):

```
# DeepEval LLM judge (deepeval 평가용). 기본값: gemini-2.0-flash
JUDGE_MODEL_NAME=gemini-2.0-flash
```

- [ ] **Step 4: evals 디렉터리 골격 + 빈 `__init__.py` 생성**

```bash
mkdir -p backend/evals/datasets backend/evals/metrics backend/evals/runners
```

그리고 아래 4개 파일을 만든다 (각각 빈 파일이면 된다):

`backend/evals/__init__.py`:
```python
"""DeepEval 기반 travel 에이전트 평가 러너."""
```

`backend/evals/datasets/__init__.py`:
```python
"""평가 골드셋 모음."""
```

`backend/evals/metrics/__init__.py`:
```python
"""평가 지표 모음."""
```

`backend/evals/runners/__init__.py`:
```python
"""에이전트 호출 어댑터 모음."""
```

- [ ] **Step 5: 디렉터리 구조 검증**

Run:
```bash
cd backend && find evals -type f -name '*.py' | sort
```

Expected:
```
evals/__init__.py
evals/datasets/__init__.py
evals/metrics/__init__.py
evals/runners/__init__.py
```

- [ ] **Step 6: 기존 회귀 확인**

Run:
```bash
cd backend && uv run pytest -q
```

Expected: 기존 모든 테스트가 그대로 통과. `evals/` 디렉터리는 비어 있어 어떤 테스트도 추가되지 않으므로 결과 수는 변하지 않는다.

- [ ] **Step 7: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.env.example backend/evals/
git commit -m "chore(evals): add deepeval dependency and evals/ skeleton"
```

참고: `.gitignore` 36번째 줄의 `docs` 패턴 때문에 `evals/` 추가는 영향 없음. `uv.lock`은 의존성 변경을 추적하기 위해 함께 커밋한다.

---

## Task 2: judge 모듈 (GOOGLE_API_KEY 기반 Gemini judge)

**Files:**
- Create: `backend/evals/judge.py`

- [ ] **Step 1: `judge.py` 작성**

`backend/evals/judge.py`:

```python
"""deepeval LLM judge 팩토리.

`GOOGLE_API_KEY`가 없으면 명확한 RuntimeError로 fail-fast 한다.
deepeval 자체는 lazy import — deepeval 미설치 환경에서도 import 자체는 성공한다.
"""
from __future__ import annotations

import os


def get_judge():
    """Gemini judge 인스턴스를 반환.

    환경 변수:
        GOOGLE_API_KEY: 필수. 없으면 RuntimeError.
        JUDGE_MODEL_NAME: 선택. 기본값 `gemini-2.0-flash`.
    """
    from deepeval.models import GeminiModel  # lazy import

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "deepeval judge requires GOOGLE_API_KEY. "
            "backend/.env에 GOOGLE_API_KEY를 설정하세요."
        )
    model_name = os.environ.get("JUDGE_MODEL_NAME", "gemini-2.0-flash")
    return GeminiModel(model=model_name, api_key=api_key)
```

- [ ] **Step 2: GOOGLE_API_KEY 없을 때 fail-fast 검증**

`backend` 디렉터리에서 실행:

```bash
cd backend && GOOGLE_API_KEY= uv run python -c "from evals.judge import get_judge; get_judge()"
```

Expected: `RuntimeError: deepeval judge requires GOOGLE_API_KEY...` 메시지로 종료 (exit code 1).

- [ ] **Step 3: 정상 import 스모크 (mock으로 deepeval 검증)**

`cd backend` 상태에서:

```bash
cd backend && uv run python -c "
import os
os.environ['GOOGLE_API_KEY'] = 'fake-key-for-import-test'
os.environ['JUDGE_MODEL_NAME'] = 'gemini-test-model'

import deepeval.models
captured = {}
class FakeGeminiModel:
    def __init__(self, model, api_key):
        captured['model'] = model
        captured['api_key'] = api_key

import deepeval.models as dm
dm.GeminiModel = FakeGeminiModel

# Re-import to refresh the lazy reference
import importlib, evals.judge
importlib.reload(evals.judge)
result = evals.judge.get_judge()

assert captured == {'model': 'gemini-test-model', 'api_key': 'fake-key-for-import-test'}, captured
assert isinstance(result, FakeGeminiModel)
print('OK:', captured)
"
```

Expected: `OK: {'model': 'gemini-test-model', 'api_key': 'fake-key-for-import-test'}` 출력.

> 참고: 이 단계는 `GeminiModel` 생성자만 검증하지 실제 API 호출은 하지 않는다. `get_judge()`가 `RuntimeError` 없이 객체를 반환하는지만 본다.

- [ ] **Step 4: 커밋**

```bash
git add backend/evals/judge.py
git commit -m "feat(evals): add Gemini judge factory with lazy deepeval import"
```

---

## Task 3: travel agent 러너 (ADK 직접 호출 어댑터)

**Files:**
- Create: `backend/evals/runners/travel_agent_runner.py`

- [ ] **Step 1: `travel_agent_runner.py` 작성**

`backend/evals/runners/travel_agent_runner.py`:

```python
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
    """travel 도메인 ADK 에이전트를 호출해 누적된 텍스트를 단일 문자열로 반환.

    Raises:
        RuntimeError: ADK 호출 실패 또는 텍스트가 비어있을 때. 메시지에 입력을 포함.
    """
    try:
        return asyncio.run(_run_async(user_input, session_id or _new_session_id()))
    except Exception as e:  # noqa: BLE001 - 의도적으로 모든 예외를 wrap
        raise RuntimeError(
            f"travel agent failed for input={user_input!r}: {e}"
        ) from e


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
```

- [ ] **Step 2: stub agent로 import + 호출 가능 검증**

`cd backend` 상태에서:

```bash
cd backend && uv run python -c "
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# build_agent가 만들어내는 LlmAgent를 가짜로 대체
fake_agent = MagicMock(name='fake_agent')

# run_async가 비동기 제너레이터를 반환하도록 설정
async def fake_stream(*args, **kwargs):
    # ADK Event와 비슷한 객체 흉내
    class FakePart:
        def __init__(self, text): self.text = text
    class FakeContent:
        def __init__(self, parts): self.parts = parts
    class FakeEvent:
        def __init__(self, parts): self.content = FakeContent(parts)
    yield FakeEvent([FakePart('서울 '), FakePart('호텔 '), FakePart('3개 추천드릴게요.')])

with patch('evals.runners.travel_agent_runner.get_plugin') as get_plugin_mock:
    plugin = MagicMock()
    plugin.build_agent.return_value = fake_agent
    get_plugin_mock.return_value = plugin

    with patch('evals.runners.travel_agent_runner.Runner') as RunnerMock:
        runner_instance = MagicMock()
        runner_instance.run_async = fake_stream
        RunnerMock.return_value = runner_instance

        from evals.runners.travel_agent_runner import run_travel_agent
        out = run_travel_agent('서울 호텔 추천해줘')
        assert out == '서울 호텔 3개 추천드릴게요.', out
        print('OK:', out)
"
```

Expected: `OK: 서울 호텔 3개 추천드릴게요.` 출력.

- [ ] **Step 3: 실제 ADK 호출 1회 (실제 GOOGLE_API_KEY 필요)**

`backend/.env`에 `GOOGLE_API_KEY`가 설정된 상태에서:

```bash
cd backend && uv run python -c "
from evals.runners.travel_agent_runner import run_travel_agent
out = run_travel_agent('안녕하세요')
print('--- agent output ---')
print(out)
print('--- end ---')
"
```

Expected: 실제 Gemini 응답 텍스트가 출력. 빈 문자열이 아니어야 함.

만약 출력 길이가 0이면:
- `backend/.env`가 제대로 로드되는지 확인 (`uv run python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.environ.get('GOOGLE_API_KEY')[:8])"`)
- 에러 메시지가 `RuntimeError`로 wrap 되어 있는지 확인

- [ ] **Step 4: 커밋**

```bash
git add backend/evals/runners/travel_agent_runner.py
git commit -m "feat(evals): add travel ADK agent runner adapter"
```

---

## Task 4: travel metric 정의 (GEval travel_correctness)

**Files:**
- Create: `backend/evals/metrics/travel_metrics.py`

- [ ] **Step 1: `travel_metrics.py` 작성**

`backend/evals/metrics/travel_metrics.py`:

```python
"""travel 도메인 응답 품질을 평가하는 GEval 정의 모음."""
from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from evals.judge import get_judge


travel_correctness = GEval(
    name="TravelResponseCorrectness",
    criteria=(
        "주어진 사용자 입력에 대해 에이전트 응답이 "
        "(1) travel 도메인(호텔/항공/팁/취향)에 맞는 행동을 보이고, "
        "(2) 필수 정보(날짜/인원/출발지/도착지 등)가 부족하면 그 정보를 명확히 되묻고, "
        "(3) hallucination 없이 travel context에 기반해 사실 기반으로 답하는지를 평가한다."
    ),
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    model=get_judge(),
    threshold=0.7,
)


DEFAULT_METRICS = [travel_correctness]
```

> 참고: 모듈 import 시점에 `get_judge()`가 호출되므로, `GOOGLE_API_KEY`가 없으면 즉시 `RuntimeError`가 난다. 이는 의도된 fail-fast.

- [ ] **Step 2: metric import + 형태 검증 (실제 judge 호출은 안 함)**

`cd backend` 상태에서:

```bash
cd backend && uv run python -c "
import os
assert os.environ.get('GOOGLE_API_KEY'), 'GOOGLE_API_KEY 필요'

from deepeval.metrics import GEval
from evals.metrics.travel_metrics import travel_correctness, DEFAULT_METRICS

assert isinstance(travel_correctness, GEval), type(travel_correctness)
assert travel_correctness.name == 'TravelResponseCorrectness', travel_correctness.name
assert travel_correctness.threshold == 0.7, travel_correctness.threshold
assert 'travel' in travel_correctness.criteria.lower(), travel_correctness.criteria
assert DEFAULT_METRICS == [travel_correctness]
print('OK:', travel_correctness.name, 'threshold=', travel_correctness.threshold)
"
```

Expected: `OK: TravelResponseCorrectness threshold= 0.7`

- [ ] **Step 3: 커밋**

```bash
git add backend/evals/metrics/travel_metrics.py
git commit -m "feat(evals): add travel_correctness GEval metric"
```

---

## Task 5: 골드 데이터셋 (2~3 케이스 + README)

**Files:**
- Create: `backend/evals/datasets/travel_goldens.jsonl`
- Create: `backend/evals/datasets/README.md`

- [ ] **Step 1: 골드 JSONL 작성**

`backend/evals/datasets/travel_goldens.jsonl`:

```jsonl
{"id":"hotel_missing_dates","input":"서울에서 도쿄로 호텔 찾아줘","expected_output":"체크인 날짜, 체크아웃 날짜, 인원 수를 명확히 되물어야 한다","tags":["hotel","missing_info"]}
{"id":"hotel_complete","input":"다음주 금요일부터 2박 3일로 도쿄에 2명이서 갈 건데 호텔 추천해줘","expected_output":"호텔 옵션이나 추가 취향 질문, 또는 구체적 호텔 추천을 제시해야 한다","tags":["hotel","complete"]}
{"id":"flight_basic","input":"내일 김포에서 제주도 가는 항공편 1명","expected_output":"항공편 옵션을 제시하거나 출발 시간/항공사에 대한 질문이 포함되어야 한다","tags":["flight"]}
```

> 주의: 각 줄 끝에 LF (`\n`) 한 개. 마지막 줄도 `\n`으로 끝나야 한다.

- [ ] **Step 2: JSONL 파싱 검증**

Run:
```bash
cd backend && uv run python -c "
import json
from pathlib import Path
path = Path('evals/datasets/travel_goldens.jsonl')
rows = []
with path.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        assert 'id' in row and 'input' in row, row
        rows.append(row)
print(f'OK: {len(rows)} goldens')
for r in rows:
    print(' -', r['id'], '|', r['input'][:30])
"
```

Expected:
```
OK: 3 goldens
 - hotel_missing_dates | 서울에서 도쿄로 호텔 찾아줘
 - hotel_complete | 다음주 금요일부터 2박 3일로 도키
 - flight_basic | 내일 김포에서 제주도 가는 항공편 1명
```

- [ ] **Step 3: 데이터셋 README 작성**

`backend/evals/datasets/README.md`:

```markdown
# 평가 골드셋

`travel_goldens.jsonl`은 1줄 = 1 평가 케이스(JSONL) 형식이다.

## 스키마

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | O | 케이스 고유 ID. 결과 리포트에서 사용 |
| `input` | string | O | 에이전트에 보낼 사용자 입력 |
| `expected_output` | string | X | 기댓값. metric이 참조할 때만 사용 |
| `tags` | string[] | X | 필터/리포트용 태그 |

## 골드 추가 규칙

1. `id`는 `kebab-case` + 도메인 prefix (예: `hotel_*`, `flight_*`, `tip_*`)
2. `expected_output`은 **자연어 1문장** 권장 (judge가 평가하기 쉬움)
3. `input`은 한국어, 실제 사용자가 입력할 법한 자연스러운 문장
4. 부적절/민감 정보 입력은 포함하지 않는다
5. 추가 시 `runner.py`가 추가 필드를 silent ignore 하므로, 신중하게 결정
```

- [ ] **Step 4: 커밋**

```bash
git add backend/evals/datasets/travel_goldens.jsonl backend/evals/datasets/README.md
git commit -m "feat(evals): add travel goldens dataset and authoring guide"
```

---

## Task 6: 메인 러너 (JSONL → agent → metric → 결과)

**Files:**
- Create: `backend/evals/runner.py`

- [ ] **Step 1: `runner.py` 작성**

`backend/evals/runner.py`:

```python
"""deepeval 메인 러너: JSONL → agent 호출 → GEval → 콘솔/JSON 리포트."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepeval import evaluate
from deepeval.test_case import LLMTestCase

from evals.metrics.travel_metrics import DEFAULT_METRICS
from evals.runners.travel_agent_runner import run_travel_agent


@dataclass(frozen=True)
class Golden:
    id: str
    input: str
    expected_output: str | None
    tags: tuple[str, ...]


def load_goldens(path: Path) -> list[Golden]:
    """JSONL 파일을 Golden 리스트로 로드."""
    if not path.exists():
        raise FileNotFoundError(f"dataset not found: {path}")
    goldens: list[Golden] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSON at line {lineno}: {e}") from e
            if "id" not in row or "input" not in row:
                raise ValueError(f"missing required fields at line {lineno}: {row}")
            goldens.append(
                Golden(
                    id=row["id"],
                    input=row["input"],
                    expected_output=row.get("expected_output"),
                    tags=tuple(row.get("tags", [])),
                )
            )
    return goldens


def _make_test_case(g: Golden, actual: str) -> LLMTestCase:
    return LLMTestCase(
        input=g.input,
        actual_output=actual,
        expected_output=g.expected_output,
    )


def _summarize_result(eval_result: Any) -> dict[str, Any]:
    """deepeval evaluate 결과 객체에서 점수/통과 여부 추출."""
    return {
        "passed": bool(getattr(eval_result, "success", False)),
        "score": (
            float(getattr(eval_result, "score", 0.0))
            if getattr(eval_result, "score", None) is not None
            else None
        ),
        "reason": getattr(eval_result, "reason", None),
    }


def run_all(
    goldens: list[Golden],
    metrics: list | None = None,
) -> list[dict[str, Any]]:
    """각 golden에 대해 agent를 호출하고 metric으로 평가.

    Returns:
        각 golden에 대한 결과 dict 리스트. shape:
            {"id": str, "status": "ok"|"error", "passed"?, "score"?, "reason"?, "error"?}
    """
    metrics = metrics or DEFAULT_METRICS
    results: list[dict[str, Any]] = []
    test_cases: list[LLMTestCase] = []
    golden_ids: list[str] = []

    for g in goldens:
        try:
            actual = run_travel_agent(g.input)
        except Exception as e:  # noqa: BLE001 - 의도적으로 모든 예외 wrap
            results.append({"id": g.id, "status": "error", "error": str(e)})
            continue
        test_cases.append(_make_test_case(g, actual))
        golden_ids.append(g.id)

    if test_cases:
        eval_results = evaluate(test_cases, metrics)
        # deepeval은 입력 순서대로 결과 반환
        for golden_id, eval_result in zip(golden_ids, eval_results):
            results.append({"id": golden_id, "status": "ok", **_summarize_result(eval_result)})

    return results


def _print_console_report(results: list[dict[str, Any]], total: int) -> None:
    print(f"\n=== deepeval runner: {len(results)}/{total} goldens evaluated ===")
    passed = sum(1 for r in results if r.get("passed") is True)
    print(f"Passed: {passed}/{len(results)}")
    for r in results:
        status = r.get("status", "?")
        if status == "ok":
            score = r.get("score")
            ok = r.get("passed")
            print(f"  [{status:5s}] {r['id']:30s} score={score} passed={ok}")
        else:
            print(f"  [{status:5s}] {r['id']:30s} error={r.get('error')[:80]}")


def _save_results_json(results: list[dict[str, Any]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{ts}.json"
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="deepeval travel evaluation runner")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/datasets/travel_goldens.jsonl"),
        help="골드셋 JSONL 경로 (기본: evals/datasets/travel_goldens.jsonl)",
    )
    args = parser.parse_args(argv)

    goldens = load_goldens(args.dataset)
    if not goldens:
        print(f"no goldens in {args.dataset}", file=sys.stderr)
        return 1

    results = run_all(goldens)
    _print_console_report(results, total=len(goldens))

    out_path = _save_results_json(results, Path("evals/results"))
    print(f"\nresults saved to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: `load_goldens` 단위 검증 (agent/evaluate 호출 없음)**

`cd backend` 상태에서:

```bash
cd backend && uv run python -c "
from pathlib import Path
from evals.runner import load_goldens, Golden

gs = load_goldens(Path('evals/datasets/travel_goldens.jsonl'))
assert len(gs) == 3, len(gs)
assert all(isinstance(g, Golden) for g in gs)
assert gs[0].id == 'hotel_missing_dates'
assert gs[0].expected_output is not None
assert gs[0].tags == ('hotel', 'missing_info')
print('OK: load_goldens works,', len(gs), 'goldens')
"
```

Expected: `OK: load_goldens works, 3 goldens`

- [ ] **Step 3: 잘못된 JSONL에 대해 명확한 에러**

임시 파일로 검증:

```bash
cd backend && uv run python -c "
from pathlib import Path
import tempfile
from evals.runner import load_goldens

with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
    f.write('{\"id\":\"x\",\"input\":\"y\"}\n')
    f.write('this is not json\n')
    p = Path(f.name)
try:
    load_goldens(p)
except ValueError as e:
    print('OK ValueError:', str(e)[:80])
finally:
    p.unlink()
"
```

Expected: `OK ValueError: invalid JSON at line 2: ...`

- [ ] **Step 4: 누락 필드 검증**

```bash
cd backend && uv run python -c "
import tempfile
from pathlib import Path
from evals.runner import load_goldens

with tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
    f.write('{\"id\":\"x\"}\n')
    p = Path(f.name)
try:
    load_goldens(p)
except ValueError as e:
    print('OK ValueError:', str(e)[:80])
finally:
    p.unlink()
"
```

Expected: `OK ValueError: missing required fields at line 1: {'id': 'x'}`

- [ ] **Step 5: 커밋**

```bash
git add backend/evals/runner.py
git commit -m "feat(evals): add main deepeval runner (load_goldens + run_all + main)"
```

---

## Task 7: 사용자 README + End-to-end 스모크 + 회귀

**Files:**
- Create: `backend/evals/README.md`
- Create: `backend/.gitignore` (modify, evals/results/ 추가)

- [ ] **Step 1: `evals/README.md` 작성**

`backend/evals/README.md`:

```markdown
# DeepEval 평가 러너

travel ADK 에이전트의 응답 품질을 deepeval로 평가하는 독립 스크립트.

## 사전 요구사항

- `backend/.env`에 `GOOGLE_API_KEY`가 설정돼 있어야 한다 (Gemini judge + 에이전트 실행 모두)
- `cd backend && uv sync`로 의존성 설치 완료 상태

## 빠른 시작

```bash
cd backend
uv run python -m evals.runner
```

기본 동작:
1. `evals/datasets/travel_goldens.jsonl` 로드
2. 각 golden마다 `run_travel_agent`로 실제 응답 생성
3. `travel_correctness` GEval로 평가
4. 콘솔에 통과/실패 + 점수 출력
5. `evals/results/<UTC timestamp>.json`에 결과 저장

## 다른 데이터셋 사용

```bash
uv run python -m evals.runner --dataset path/to/other_goldens.jsonl
```

## 환경 변수

| 변수 | 필수 | 기본값 | 용도 |
|---|---|---|---|
| `GOOGLE_API_KEY` | O | - | Gemini judge + 에이전트 실행 |
| `JUDGE_MODEL_NAME` | X | `gemini-2.0-flash` | judge로 사용할 Gemini 모델 |

## 현재 한계 (단계 1 범위)

- pytest 통합 없음 (단계 2에서 추가)
- 다턴 대화 평가 없음 (단턴만)
- tool_call 경로 평가는 후속 단계
- CI 게이트(`--fail-under`)는 단계 4에서 추가

자세한 설계는 `docs/superpowers/specs/2026-07-11-deepeval-introduction-design.md` 참고.
```

- [ ] **Step 2: `.gitignore`에 `evals/results/` 추가**

저장소 루트의 단일 `.gitignore`(`G:\dev\project\agent\ag_ui\travel-agui\.gitignore`) 끝에 한 줄을 추가한다:

```
evals/results/
```

확인 (디렉터리를 만들어 실제로 무시되는지 검증):

```bash
mkdir -p backend/evals/results
echo '{}' > backend/evals/results/.dummy.json
git check-ignore backend/evals/results/.dummy.json
```

Expected: `backend/evals/results/.dummy.json` 출력 (무시되고 있음).

그 후 더미 파일 삭제:
```bash
rm backend/evals/results/.dummy.json
```

- [ ] **Step 3: End-to-end 스모크 (실제 LLM 호출)**

`backend/.env`에 `GOOGLE_API_KEY`가 있는 상태에서:

```bash
cd backend && uv run python -m evals.runner
```

Expected: 대략 아래 형태의 출력

```
=== deepeval runner: 3/3 goldens evaluated ===
Passed: 2/3
  [ok   ] hotel_missing_dates        score=0.82 passed=True
  [ok   ] hotel_complete             score=0.75 passed=True
  [ok   ] flight_basic               score=0.40 passed=False

results saved to: evals/results/<timestamp>.json
```

> 점수/통과는 LLM judge의 비결정적 응답에 따라 흔들릴 수 있다. 모든 케이스 통과보다는 (1) 출력이 나오고 (2) `evals/results/`에 JSON이 남고 (3) 통과/실패가 골드마다 기록되는 것이 핵심.

확인:
```bash
cd backend && ls evals/results/  # .json 파일이 하나 이상 있어야 함
cd backend && uv run python -c "
import json
from pathlib import Path
results = sorted(Path('evals/results').glob('*.json'))
assert results, 'no result files'
latest = results[-1]
data = json.loads(latest.read_text(encoding='utf-8'))
print('latest:', latest.name, '| entries:', len(data))
for r in data:
    print(' -', r['id'], r.get('status'))
"
```

Expected: 3개 골드 id가 모두 출력되고, 각각 `ok` 또는 `error` 상태.

- [ ] **Step 4: 기존 백엔드 회귀 테스트**

Run:
```bash
cd backend && uv run pytest -q
```

Expected: 기존 모든 테스트가 그대로 통과. 출력 수가 변하지 않음을 확인.

추가:
```bash
cd backend && uv run pytest tests/test_compatibility_cleanup.py -q
```

Expected: 통과 (wrapper 회귀 없음).

- [ ] **Step 5: 프론트엔드 회귀**

```bash
cd frontend && npm run build
```

Expected: 빌드 성공. (이 단계에서 코드 변경은 없으므로 npm test도 그대로 통과할 것.)

- [ ] **Step 6: 최종 커밋**

```bash
git add backend/evals/README.md backend/.gitignore
git commit -m "docs(evals): add README and gitignore evals/results/"
```

---

## Definition of Done (단계 1)

- [ ] Task 1~7의 모든 커밋이 `git log`에 남아있다
- [ ] `cd backend && uv sync`가 깨끗이 통과
- [ ] `cd backend && uv run python -m evals.runner`가 점수/통과/실패 + JSON 리포트를 남긴다
- [ ] `cd backend && uv run pytest -q`가 기존 그대로 통과
- [ ] `cd backend && uv run pytest tests/test_compatibility_cleanup.py -q`가 통과
- [ ] `cd frontend && npm run build`가 성공
- [ ] `evals/results/`가 `.gitignore`로 추적 제외
- [ ] 공통 엔진/도메인 plugin 코드는 0줄 수정

이 Done 기준이 모두 만족되면 단계 2(pytest 통합) 플랜을 작성한다.

---

## 예상 시간

- Task 1: 5분
- Task 2: 5분
- Task 3: 10분 (실제 LLM 호출 디버깅 포함)
- Task 4: 3분
- Task 5: 5분
- Task 6: 10분
- Task 7: 10분 (End-to-end + 회귀)

총 약 50분. 실제 LLM 호출 디버깅이 더 걸릴 수 있다.

---

## 트러블슈팅

### `ModuleNotFoundError: No module named 'deepeval'`
- `cd backend && uv sync` 재실행
- `which python`이 `.venv` 안의 python을 가리키는지 확인: `cd backend && uv run which python`

### `RuntimeError: deepeval judge requires GOOGLE_API_KEY`
- `backend/.env`에 `GOOGLE_API_KEY=...` 있는지 확인
- `uv run python -c "from dotenv import load_dotenv, find_dotenv; load_dotenv(find_dotenv()); import os; print(os.environ.get('GOOGLE_API_KEY', 'NOT SET')[:10])"`로 로드 확인

### End-to-end가 hang
- `runner.run_async`가 종료되지 않는 케이스: `google.adk.runners.Runner`에 `InMemorySessionService`를 잘 전달했는지 확인
- 네트워크 문제: `GOOGLE_API_KEY` 자체는 valid한지 curl 등으로 확인

### `evaluate` 결과의 `score`가 `None`
- deepeval 3.x의 `MetricResult.score` 필드가 `None`인 경우가 있다. Step 1은 informational — 단계 4에서 threshold gate를 추가할 때 더 엄격히 다룬다.
- 현재 코드(`_summarize_result`)는 이 경우 `None`을 그대로 출력한다.
