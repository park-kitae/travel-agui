# DeepEval 평가 시스템

이 문서는 travel-agui 백엔드에 추가한 DeepEval 기반 평가 체계를 설명합니다. 목표는 ADK 기반 travel 에이전트의 응답 품질을 독립 실행 가능한 평가 스크립트와 pytest 통합 테스트로 검증하는 것입니다.

## 1. 구성 개요

평가 시스템은 다음 구조로 구성되어 있습니다.

```text
backend/evals/
├── __init__.py
├── judge.py
├── runner.py
├── summary.py
├── datasets/
│   ├── __init__.py
│   └── travel_goldens.jsonl
├── metrics/
│   ├── __init__.py
│   └── travel_metrics.py
├── runners/
│   ├── __init__.py
│   └── travel_agent_runner.py
├── tests/
│   ├── __init__.py
│   └── test_evals.py
└── results/
    └── README.md
```

### 역할별 설명

- `runner.py`: 평가 실행 진입점입니다. JSONL 골든 데이터셋을 읽고, 에이전트 응답을 수집한 뒤 DeepEval로 점수를 측정합니다.
- `judge.py`: `GOOGLE_API_KEY`와 `JUDGE_MODEL_NAME`을 바탕으로 Gemini 기반 judge 객체를 생성합니다.
- `runners/travel_agent_runner.py`: A2A/HTTP 경로를 우회하고, ADK `Runner`를 직접 호출해 최종 텍스트 응답을 가져옵니다.
- `metrics/travel_metrics.py`: `travel_correctness` GEval 지표를 정의합니다.
- `datasets/travel_goldens.jsonl`: 평가용 입력/기대값 샘플을 담은 JSONL 데이터셋입니다.
- `tests/test_evals.py`: pytest 환경에서 평가를 실행하는 통합 테스트입니다.
- `summary.py`: 최신 평가 결과 JSON 파일을 요약해서 보여줍니다.

## 2. 사용한 DeepEval 기능

이번 단계에서는 DeepEval의 핵심 기능만 최소한으로 사용했습니다.

### 2.1 GEval

`travel_correctness` 지표는 DeepEval의 `GEval`을 사용해 정의했습니다.

- 평가 기준:
  - 사용자 입력에 대해 도메인에 맞는 행동을 하는가
  - 필수 정보가 부족하면 명확히 되묻는가
  - hallucination 없이 사실 기반으로 응답하는가
- 사용 방식:
  - `LLMTestCase`에 `input`과 `actual_output`을 전달
  - `GeminiModel` 기반 judge가 해당 기준을 평가

### 2.2 LLMTestCase

각 골든에 대해 `LLMTestCase`를 생성해 DeepEval 평가 파이프라인에 넣었습니다.

### 2.3 evaluate()

`deepeval.evaluate()`를 호출해 평가 결과를 수집하고, 점수와 통과 여부를 확인합니다.

## 3. 테스트 방식

### 3.1 독립 스크립트 실행

다음 명령으로 standalone 평가를 실행할 수 있습니다.

```bash
cd backend
uv run python -m evals.runner --dataset evals/datasets/travel_goldens.jsonl --fail-under 0.8
```

이 명령은 다음 흐름으로 동작합니다.

1. JSONL 데이터셋 로드
2. 각 입력에 대해 travel agent 실행
3. 응답 텍스트 수집
4. DeepEval GEval로 점수화
5. 결과 JSON 저장
6. `--fail-under` 기준을 통과하지 못하면 실패 처리

### 3.2 pytest 통합 테스트

pytest 환경에서도 동일한 평가 흐름을 실행할 수 있습니다.

```bash
cd backend
uv run pytest evals/tests -m eval
```

현재 구현은 `GOOGLE_API_KEY`가 없으면 테스트를 skip하도록 되어 있습니다.

## 4. 환경 설정

평가를 실행하려면 다음 환경이 필요합니다.

- `GOOGLE_API_KEY`
- 선택값: `JUDGE_MODEL_NAME` (기본값 `gemini-2.5-flash`)

예시:

```bash
cp backend/.env.example backend/.env
```

그리고 `backend/.env`에 다음과 같이 입력합니다.

```env
GOOGLE_API_KEY=your_gemini_api_key_here
JUDGE_MODEL_NAME=gemini-2.5-flash
```

## 5. 결과 저장 방식

평가가 끝나면 결과는 `backend/evals/results/` 아래 JSON 파일로 저장됩니다.

또한 최신 결과 요약은 다음 명령으로 확인할 수 있습니다.

```bash
cd backend
uv run python -m evals.summary
```

## 6. 현재 구현 범위

이번 단계에서 구현한 범위는 다음과 같습니다.

- DeepEval 의존성 추가
- Gemini 기반 judge 생성
- ADK 직접 호출 기반 agent runner 구현
- travel correctness GEval 평가 지표 추가
- 샘플 데이터셋과 standalone 실행 경로 구현
- pytest 통합 테스트 구성
- `--fail-under` 기반 실패 처리 지원

## 7. 다음 단계로 확장 가능 항목

향후 다음 단계로 확장할 수 있습니다.

- 데이터셋 개수 확대
- 추가 metric 도입
- tool-call 경로 평가
- CI/PR에서 자동 평가 실행
- 결과 대시보드/트레이싱 연동

