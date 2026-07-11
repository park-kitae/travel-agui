## DeepEval Introduction Design

### Goal

travel-agui 백엔드에 deepeval을 단계적으로 도입해, ADK 기반 travel 에이전트의 응답 품질을 LLM-as-judge(GEval + Gemini)로 측정할 수 있는 평가 인프라를 만든다. 첫 단계는 독립 실행 스크립트로 시작하고, 이후 pytest 통합 → 데이터셋 확장 → 지표 확장 + CI 게이트 → tracing/대시보드 순으로 확장한다.

### Current State

- 백엔드는 `backend/main.py`(AG-UI Gateway), `backend/a2a_server.py`, `backend/executor.py`, `backend/converter.py`, `backend/domain_runtime.py` 같은 **공통 엔진**과 `backend/domains/travel/*` 같은 **도메인 플러그인**으로 분리되어 있다.
- 테스트는 `backend/tests/` 아래 pytest + httpx ASGITransport 기반이며, `test_compatibility_cleanup.py`로 wrapper 회귀를 막고 있다.
- 평가/관측 도구는 현재 없으며, 에이전트 응답 품질을 정량적으로 측정할 수단이 없다.
- `pyproject.toml`에는 `google-adk`, `a2a-sdk`, `ag-ui-protocol`, `fastapi`, `uvicorn`, `httpx`, `pydantic`만 등록되어 있다.
- `GOOGLE_API_KEY`는 이미 `backend/.env`에 존재(Gemini 에이전트 실행용).

### Scope

포함:

- `backend/evals/` 신규 디렉터리와 그 안의 judge / datasets / metrics / runners / runner / tests 모듈
- `backend/pyproject.toml`에 deepeval 의존성 추가
- `backend/.env.example`에 judge 관련 env 추가(선택)
- 단계 1(독립 스크립트) ~ 단계 5(tracing)까지의 순차적 도입
- 각 단계마다 기존 백엔드/프론트 회귀 테스트가 깨지지 않는지 확인

제외:

- 공통 엔진(`backend/main.py`, `executor.py`, `converter.py`, `domain_runtime.py`, `a2a_server.py`) 코드 수정
- 도메인 플러그인(`backend/domains/travel/*`, `backend/domains/fake/*`) 코드 수정
- 다턴 대화 평가, 자동 골드 생성(synthesizer), Confident AI 대시보드 강제 연동
- A2A/HTTP 경로를 거치는 평가(평가는 ADK 직접 호출로 결정성 확보)

### Approach

가장 단순한 형태의 디렉터리를 만들고, 단계마다 그 위에 살을 붙인다. 평가는 A2A/HTTP를 우회해 ADK `LlmAgent`를 직접 호출하는 어댑터로 수행한다. 이렇게 하면:

- 평가 실행이 빠르고 결정적
- 공통 엔진 경계가 다시 새는 일을 막을 수 있음(fake plugin 스모크 테스트가 깨지지 않는다는 기존 원칙과 동일)
- 도메인 plugin을 스왑해 동일 평가 러너로 다른 도메인도 평가할 여지를 남김

평가에 LLM judge가 필요한 만큼 `GOOGLE_API_KEY`는 judge에서도 재사용한다. 새 API 키는 도입하지 않는다.

### Directory Layout

```
backend/evals/
  __init__.py
  judge.py                         # GeminiModel 팩토리 (lazy import)
  runner.py                        # 메인 러너: dataset → agent → metric → 결과
  datasets/
    __init__.py
    travel_goldens.jsonl           # 1줄 = 1 golden (id/input/expected_output/tags)
    README.md                      # 골드 추가 규칙/예시
  metrics/
    __init__.py
    travel_metrics.py              # GEval 정의 모음 (단계 1은 travel_correctness 1개)
  runners/
    __init__.py
    travel_agent_runner.py         # ADK LlmAgent 직접 호출 → 최종 텍스트 추출
  tests/
    __init__.py
    test_evals.py                  # runner.run_all()을 pytest로 검증
  README.md                        # 사용법/단계별 가이드
```

`backend/pyproject.toml`에 `deepeval>=3.0.0` 추가. 기존 `pytest`/`pytest-asyncio`/`pytest-mock`는 그대로.

### Layer Responsibilities

| 레이어 | 책임 | 의존성 |
|---|---|---|
| `judge.py` | `GOOGLE_API_KEY`로 `deepeval.models.GeminiModel` 생성, lazy import | deepeval |
| `datasets/` | 평가 입력/기대 출력 골드(JSONL) | 없음 |
| `metrics/` | GEval 정의(criteria, threshold, evaluation_params) | judge, deepeval |
| `runners/travel_agent_runner.py` | `domains.travel.plugin.get_plugin()` → `build_agent()` → ADK stream 소비 → 최종 텍스트 1개 반환 | ADK |
| `runner.py` | JSONL 로드 → 각 golden마다 runner 호출 → `LLMTestCase` 구성 → `deepeval.evaluate` → 콘솔 + JSON 리포트 | deepeval, judge, metrics, runners |
| `tests/test_evals.py` | `runner.run_all()`을 1회 호출하고 결과 dict에 통과/실패 플래그가 있는지 확인 | pytest, runner |

### Golden Schema

`datasets/travel_goldens.jsonl` 한 줄 예:

```json
{
  "id": "hotel_missing_dates",
  "input": "서울에서 도쿄로 호텔 찾아줘",
  "expected_output": "체크인/체크아웃 날짜와 인원 수를 되물어야 한다",
  "tags": ["hotel", "missing_info"]
}
```

필드는 `id`(고유), `input`(필수), `expected_output`(선택, metric이 참조할 때만), `tags`(필터링/리포트용) 4개로 한정한다. 추가 필드가 생기면 `runner.py`에서 명시적으로 매핑하고 silent ignore 한다.

### Metric Definition

`metrics/travel_metrics.py` 초기 항목:

```python
travel_correctness = GEval(
    name="TravelResponseCorrectness",
    criteria=(
        "주어진 사용자 입력에 대해 에이전트 응답이 (1) 도메인에 맞는 행동을 보이고, "
        "(2) 필수 정보가 부족하면 그 정보를 명확히 되묻고, "
        "(3) hallucination 없이 사실 기반으로 답하는지를 평가한다."
    ),
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
    model=get_judge(),
    threshold=0.7,
)
```

단계 4에서 같은 파일에 `travel_faithfulness`, `travel_tool_selection` 등을 누적한다. metric 추가 시 `runner.py`의 `DEFAULT_METRICS` 리스트에 등록한다.

### Agent Runner

`runners/travel_agent_runner.py`:

```python
def run_travel_agent(user_input: str, session_id: str = "eval") -> str:
    """domains.travel.plugin.get_plugin() → build_agent() → ADK stream 소비 → 최종 텍스트."""
```

- A2A/HTTP 우회 → 빠르고 결정적
- 1차 버전은 텍스트 응답 1개만 반환, tool_call 경로 평가는 후속 스펙
- 에러 시 호출자가 식별할 수 있도록 `RuntimeError`로 wrap, 메시지에 golden `id` 포함

### Main Runner

`runner.py` 흐름:

1. `argparse`로 `--dataset`(기본 `datasets/travel_goldens.jsonl`), `--metric`(기본 `travel_correctness`), `--fail-under`(선택) 받기
2. JSONL 로드, 각 row를 `Golden` dataclass로 파싱
3. `run_travel_agent(row.input)` 호출 → `actual_output`
4. `LLMTestCase(input=row.input, actual_output=actual_output, expected_output=row.expected_output)` 구성
5. 등록된 metric으로 `deepeval.evaluate(test_cases, metrics)` 호출
6. 결과를 `evals/results/<UTC-timestamp>.json`에 저장
7. `--fail-under` 지정 시 평균 점수가 임계 미만이면 `sys.exit(1)`

`evals/results/`는 `.gitignore`에 추가한다(단계 4에서 명시).

### Data Flow

```
travel_goldens.jsonl
       │
       ▼
   runner.py
       │
       ├──► runners/travel_agent_runner ──► ADK LlmAgent ──► actual_output
       │
       ├──► metrics (GEval) ◄── judge.py (Gemini)
       │
       ▼
  deepeval.evaluate → 콘솔 리포트 + JSON
```

### Environment / Configuration

- `pyproject.toml`: `deepeval>=3.0.0,<4.0.0` 추가 (major upgrade는 별도 PR)
- `backend/.env.example`: `JUDGE_MODEL_NAME=gemini-2.0-flash` (선택, 기본값 있음) 추가
- 기존 `GOOGLE_API_KEY` 재사용 — 새 키 도입 없음
- `uv sync`로 설치

### Error Handling

| 상황 | 동작 |
|---|---|
| `GOOGLE_API_KEY` 없음 | `judge.get_judge()`가 `RuntimeError`로 fail-fast, 메시지에 "deepeval judge requires GOOGLE_API_KEY" 명시 |
| judge LLM 호출 실패 (rate limit 등) | deepeval 기본 재시도, 그래도 실패 시 해당 golden은 `status: error`로 기록하고 계속 진행 |
| agent 호출 실패 (ADK 예외) | 동일하게 해당 golden만 `status: error`, 다른 golden은 계속 평가 |
| `expected_output` 누락 | metric이 참조하지 않으면 허용, 참조 metric은 해당 golden을 `status: skipped`로 표시 |
| `deepeval` 미설치 | `evals/` 내부 lazy import → 미설치 환경에서도 `uv run pytest`의 다른 테스트는 영향 없음 |

### Testing

TDD 원칙에 따라 각 단계 말미에 아래 5개가 모두 통과해야 다음 단계로 진행한다.

1. `cd backend && uv sync` — 의존성 설치 확인
2. `cd backend && uv run python -m evals.runner` — 스탠드얼론 실행 (단계 1+)
3. `cd backend && uv run pytest evals/tests/ -m eval` — pytest 통합 (단계 2+)
4. `cd backend && uv run pytest` — 기존 백엔드 회귀
5. `cd frontend && npm run build && npm test` — 프론트 회귀

추가:

- 단계 1 PR에는 `test_compatibility_cleanup.py`를 한 번 더 실행해 wrapper 회귀가 안 생겼는지 확인
- 단계 4부터는 `uv run python -m evals.runner --fail-under 0.7`이 의도대로 exit code를 반환하는지 확인하는 테스트 1개 추가

### Step-by-Step Rollout

각 단계 끝마다 위 Testing 5개가 모두 통과해야 다음으로 간다.

**단계 1 — 간단 스크립트**

- `backend/evals/{__init__.py, judge.py, runner.py}`
- `backend/evals/metrics/travel_metrics.py` (GEval 1개: `travel_correctness`)
- `backend/evals/datasets/travel_goldens.jsonl` (2~3 golden)
- `backend/evals/datasets/README.md` (골드 추가 가이드)
- `backend/evals/runners/travel_agent_runner.py` (텍스트 1개 추출)
- `backend/evals/README.md` (사용법 1페이지)
- `backend/pyproject.toml`에 `deepeval` 추가
- `backend/.env.example`에 `JUDGE_MODEL_NAME` 항목 추가
- Done: `uv run python -m evals.runner`가 실제 점수와 통과/실패를 콘솔에 찍음

**단계 2 — pytest 통합**

- `backend/evals/tests/test_evals.py` 추가
- `pyproject.toml`의 `[tool.pytest.ini_options]`에 `markers = ["eval: deepeval-based evaluation tests"]` 추가
- `GOOGLE_API_KEY` 없으면 `pytest.skip`, 있으면 `runner.run_all()`을 단일 케이스로 검증
- Done: `uv run pytest evals/tests/ -m eval` 통과 + 기존 `uv run pytest` 회귀 없음

**단계 3 — 데이터셋 확장**

- `datasets/travel_goldens.jsonl`을 8~12개로 확장 (호텔/항공/팁/취향/폼 시나리오 커버)
- `runner.py`에 `--dataset path` CLI 옵션 추가
- Done: 새 데이터셋으로 1·2·3 검증 통과

**단계 4 — 지표 확장 + CI 게이트**

- `metrics/travel_metrics.py`에 `travel_faithfulness`, `travel_tool_selection` 추가
- `runner.py`에 `--fail-under <rate>` 추가, 평균 점수 미달 시 exit code != 0
- `evals/results/`를 `.gitignore`에 추가
- Done: `uv run python -m evals.runner --fail-under 0.7` 강제 가능

**단계 5 — Tracing / 대시보드**

- `judge.py`에 `deepeval.tracing` 통합 옵션
- `CONFIDENT_API_KEY`(선택) `.env.example`에 추가
- `runner.py`에 `--trace/--no-trace` 플래그(기본 `--no-trace`)
- Done: 대시보드 키 없이도 `runner.py` 실행은 영향 없음

### YAGNI

이번 스펙에서는 의도적으로 다음을 **범위 밖**으로 둔다.

- 다턴 대화 평가 (현재 골든은 단턴)
- 자동 골드 생성 (synthesizer)
- 에이전트 응답의 tool_call 경로 정밀 평가 (A2A 이벤트 → metric 매핑은 별도 스펙)
- 강제 CI 게이트 자동 활성화 (옵트인 형태로만 둠)

### Risks

- `deepeval` 패키지 API가 3.x에서 자주 바뀔 수 있어 import 위치/클래스명이 흔들릴 수 있다 → 단계 1 PR에서 import 경로를 최소화하고, version pin을 `>=3.0.0,<4.0.0`로 잡아 major upgrade를 명시적 PR로 분리
- LLM judge 응답이 비결정적이므로 동일 골드도 점수가 흔들릴 수 있다 → 단계 1에서 2~3회 재실행해 대략적인 분포를 확인하고 threshold를 보수적으로 잡는다
- `run_travel_agent`가 ADK stream을 모두 소비해야 하므로, 응답이 길거나 tool call을 동반할 때 종료 조건을 잘못 잡으면 hang 가능 → stream 소비는 `last_text_chunk`만 보존하는 단순 정책으로 시작
- judge가 응답을 한국어로 매번 평가하도록 prompts가 영어/한글 혼재될 수 있다 → 단계 1 criteria는 한국어로 통일, metric 추가 시 일관성 유지

### Success Criteria

- 단계 1 Done: `uv run python -m evals.runner`가 실제 점수 + 통과/실패를 콘솔에 출력하고, 결과 JSON이 `evals/results/`에 남는다
- 단계 2 Done: `uv run pytest -m eval`이 통과하고, 키가 없으면 skip되며 기존 pytest 회귀가 없다
- 단계 3 Done: 데이터셋이 8~12개 골드를 포함하고 CLI 옵션으로 다른 데이터셋을 받을 수 있다
- 단계 4 Done: `--fail-under`가 의도한 대로 exit code를 반환하고, 2개 이상의 metric을 동시에 돌릴 수 있다
- 단계 5 Done: `--trace` 옵션이 켜졌을 때만 외부 대시보드 호출이 발생한다
- 모든 단계 공통: 공통 엔진/도메인 plugin 코드는 0줄 수정, 기존 백엔드/프론트 회귀 테스트가 모두 통과한다
