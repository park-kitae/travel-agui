# Travel AGUI E2E 테스트 가이드

## 개요

이 디렉토리의 E2E 테스트는 모두 Playwright Test Framework 기준으로 관리합니다.

- 테스트 위치: `tests/e2e/`
- 공통 헬퍼: `tests/e2e/utils/testHelpers.ts`
- 설정 파일: `playwright.config.ts`

## 사전 준비

테스트 실행 전 아래 서버가 모두 실행 중이어야 합니다.

```bash
./start.sh
```

기본 포트:

- A2A 서버: `http://localhost:8001`
- AG-UI 게이트웨이: `http://localhost:8000`
- 프론트엔드: `http://localhost:5173`

또는 수동 실행도 가능합니다.

```bash
# terminal 1
cd backend
source .venv/bin/activate
python a2a_server.py

# terminal 2
cd backend
source .venv/bin/activate
python main.py

# terminal 3
cd frontend
npm run dev
```

## 실행 방법

프로젝트 루트에서 실행합니다.

```bash
# 전체 테스트
npm test

# 동일한 E2E 별칭
npm run test:e2e

# 브라우저를 띄워서 실행
npm run test:e2e:headed

# Playwright UI 모드
npm run test:ui

# 디버그 모드
npm run test:debug

# 특정 파일만 실행
npx playwright test tests/e2e/full-flow.spec.ts
```

## 테스트 목록

### `tests/e2e/full-flow.spec.ts`
- 호텔 검색 폼 표시 → 제출 → 결과 확인
- 항공편 검색 폼 표시 → 제출 → 왕복 결과 확인

### `tests/e2e/hotel-form-full.spec.ts`
- 호텔 예약 요청 후 폼 필드 표시 확인
- 날짜/인원 입력 후 호텔 결과 렌더링 확인

### `tests/e2e/hotel-direct-search.spec.ts`
- 자연어에 모든 정보가 포함된 경우 폼 없이 바로 호텔 결과 확인

### `tests/e2e/default-values.spec.ts`
- 도시 없음: 도시 필드 빈값 확인
- 도시 포함: 도시 기본값 자동 입력 확인
- 체크인/체크아웃/인원 기본값 확인

### `tests/e2e/natural-language.spec.ts`
- 폼 제출 후 사용자 메시지가 자연어 문장으로 다시 생성되는지 확인

### `tests/e2e/flight-form.spec.ts`
- 항공편 폼 기본값 확인
- 출발지/목적지 자동 입력 확인
- 제출 후 자연어 메시지 확인

### `tests/e2e/form-submit.spec.ts`
- 호텔 폼 제출 후 결과 카드와 메시지 수 변화 확인

### `tests/e2e/form-values.spec.ts`
- 호텔 폼 필드 값 변경과 제출 버튼 상태 확인

### `tests/e2e/assistant-response-check.spec.ts`
- 사용자/어시스턴트 메시지 수
- `request_user_input` 툴 호출 표시
- 사용자 입력 폼 렌더링 확인

### `tests/e2e/response-capture.spec.ts`
- `/agui/run` SSE 응답 캡처
- `USER_INPUT_REQUEST` 또는 `request_user_input` 이벤트 확인

### `tests/e2e/debug-flow.spec.ts`
- `/agui/` 네트워크 흐름 감지
- 폼/결과/에러 상태를 회귀 관점에서 빠르게 점검

## 최근 검증 결과

현재 Playwright 마이그레이션 이후 전체 스위트 검증 결과:

```bash
npx playwright test
# 11 passed
```

## 아티팩트

- 실패 시 스크린샷, 비디오, trace가 Playwright 기본 결과물로 저장됩니다.
- HTML 리포트는 `playwright-report/`에 생성됩니다.

## 트러블슈팅

### 테스트가 시작되지 않을 때

```bash
curl http://localhost:5173
curl http://localhost:8001/.well-known/agent-card.json
```

### 포트 충돌이 있을 때

```bash
lsof -ti :8001
lsof -ti :8000
lsof -ti :5173
./stop.sh
```

### 특정 테스트만 다시 확인하고 싶을 때

```bash
npx playwright test tests/e2e/flight-form.spec.ts
npx playwright test tests/e2e/default-values.spec.ts
```

### 에이전트 변경 후 꼭 봐야 하는 회귀 포인트

- `request_user_input` 호출 시 폼이 표시되는지
- `context` 값이 도시/출발지/목적지 기본값에 반영되는지
- 폼 제출 후 자연어 사용자 메시지가 생성되는지
- 호텔/항공편 결과가 `.tool-card`로 렌더링되는지

## 유지 원칙

- 새 E2E 테스트는 `tests/e2e/*.spec.ts`로 추가합니다.
- 레거시 `node test-*.js` 방식은 사용하지 않습니다.
- 공통 셀렉터/헬퍼는 `tests/e2e/utils/testHelpers.ts`에 모읍니다.
