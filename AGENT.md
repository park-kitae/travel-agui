# Travel AG-UI

Google ADK 기반 여행 AI 에이전트 + AG-UI 프론트엔드 프로젝트.

이 프로젝트의 현재 백엔드 구조는 **공통 채팅 엔진**과 **도메인 플러그인**을 분리한 형태입니다.

---

## 핵심 아키텍처

```text
사용자 → React Frontend (5173)
       → AG-UI Gateway / backend/main.py (8000)
       → Domain Runtime / backend/domain_runtime.py
       → A2A Server / backend/a2a_server.py (8001)
       → Executor / backend/executor.py
       → Active Domain Plugin / backend/domains/<domain>/...
       → LlmAgent (Gemini) + FunctionTools
```

### 공통 엔진

| 파일 | 역할 |
|---|---|
| `backend/main.py` | `/agui/run` 요청 수신, runtime으로 request 준비, A2A 호출, SSE 응답 반환 |
| `backend/a2a_server.py` | runtime에서 agent/card를 받아 A2A 서버 부팅 |
| `backend/executor.py` | ADK 실행, tool call / tool result lifecycle 처리 |
| `backend/converter.py` | A2A 이벤트를 AG-UI 이벤트로 변환 |
| `backend/domain_runtime.py` | active plugin 로딩, state 저장/복원, request 준비, runtime emission 매핑 |
| `backend/state/store.py` | plugin state를 opaque하게 저장 |

### 도메인 전용 구현

| 경로 | 역할 |
|---|---|
| `backend/domains/travel/plugin.py` | 현재 travel domain의 `DomainPlugin` 구현 |
| `backend/domains/travel/agent.py` | travel ADK agent 생성 |
| `backend/domains/travel/state.py` | travel state 모델 + 상태 전이 규칙 |
| `backend/domains/travel/context.py` | travel context block 생성 |
| `backend/domains/travel/data/*` | 여행 데이터 소스 |
| `backend/domains/travel/tools/*` | 여행 도구 구현 |
| `backend/domains/fake/plugin.py` | 도메인 스왑 검증용 fake plugin |

### import 원칙

이제 backend 호환성 wrapper는 제거되었습니다.

- travel agent는 `backend/domains/travel/agent.py`
- state 모델/상태 전이는 `backend/domains/travel/state.py`, `backend/domains/travel/state_manager.py`
- context builder는 `backend/domains/travel/context.py`
- data/tool 구현은 `backend/domains/travel/data/*`, `backend/domains/travel/tools/*`
- 공통 상태 저장소만 `backend/state/store.py` 에 남아 있습니다

새 코드는 compatibility 경로를 만들지 말고 실제 구현 경로를 직접 import 해야 합니다.

---

## 현재 활성 도메인

기본값은 travel 입니다.

```bash
DOMAIN_PLUGIN=travel
```

런타임은 short id(`travel`)와 full path(`domains.travel.plugin:get_plugin`) 둘 다 지원합니다.

---

## 개발 명령어

```bash
python start.py                         # 전체 서버 시작 (백엔드 + 프론트)

cd backend && uv run pytest            # 백엔드 전체 테스트
cd frontend && npm run build           # 프론트 빌드 검증
cd frontend && npm test                # Playwright E2E 테스트
```

도메인 스왑 검증 예시:

```bash
cd backend
DOMAIN_PLUGIN=travel uv run pytest -q
DOMAIN_PLUGIN=fake uv run pytest tests/test_domain_runtime.py tests/test_fake_plugin_smoke.py -v
```

---

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `backend/domain_runtime.py` | `DomainRuntime`, `PreparedRequest`, runtime emission mapping |
| `backend/domains/base.py` | `DomainPlugin` 계약, typed runtime emission 모델 |
| `backend/domains/travel/plugin.py` | travel plugin 진입점 |
| `backend/domains/travel/state.py` | `TravelState`, `TravelContext`, 상태 전이 helper |
| `backend/domains/travel/context.py` | `ContextBuilder` |
| `backend/domains/travel/agent.py` | travel 전용 `LlmAgent` 조립 |
| `backend/a2a_server.py` | runtime 기반 A2A 서버 엔트리 |
| `backend/executor.py` | runtime 기반 tool/state emission 처리 |
| `backend/main.py` | runtime 기반 AG-UI Gateway |
| `backend/tests/test_domain_runtime.py` | runtime/loader/typed emission 테스트 |
| `backend/tests/test_fake_plugin_smoke.py` | fake plugin 스왑 스모크 테스트 |
| `backend/tests/test_compatibility_cleanup.py` | 제거된 backend wrapper가 다시 생기지 않도록 검증 |
| `docs/domain_separate.md` | 분리 기준 설명 문서 |

---

## travel 도메인 도구 목록

- `search_hotels(city, check_in, check_out, guests)`
- `search_flights(origin, destination, departure_date, passengers, return_date)`
- `request_user_input(input_type, fields, context)`
- `request_user_favorite(favorite_type, context)`
- `get_travel_tips(destination)`
- `get_hotel_detail(hotel_code)`

이 도구들은 이제 `backend/domains/travel/tools/*` 가 authoritative source 입니다.

---

## 주요 규칙

- 공통 엔진은 travel field의 의미를 직접 해석하지 않는다.
- state 의미 / tool 결과 해석 / context 주입은 plugin에서 처리한다.
- 호텔/항공편 필수 정보 누락 시 → 텍스트 질문보다 `request_user_input` 우선.
- 취향 수집 우선 규칙은 travel plugin의 agent/state 로직에 존재한다.
- tool-call state 변경은 `STATE_DELTA`, tool result / UI request는 `STATE_SNAPSHOT` 또는 custom event 경로를 사용한다.
- fake plugin 스모크 테스트가 깨지면 "공통 엔진" 경계가 다시 새고 있다는 뜻으로 본다.

---

## 새 도메인 추가 방법

예: finance 도메인 추가

```text
backend/domains/finance/
  plugin.py
  agent.py
  state.py
  context.py
  data/
  tools/
```

필요한 구현:

1. `DomainPlugin` 계약 구현
2. state serialize/deserialize
3. client state merge 규칙
4. tool call / tool result 해석
5. context block 생성
6. `build_agent()` / `agent_card()` 제공

실행 시:

```bash
DOMAIN_PLUGIN=finance
```

---

## travel 도메인에 새 FunctionTool 추가 시

1. `backend/domains/travel/tools/`에 Python 함수 추가
2. 필요한 데이터가 있으면 `backend/domains/travel/data/`에 추가
3. `backend/domains/travel/agent.py`에서 `FunctionTool(func)` 연결
4. 필요 시 `backend/domains/travel/state.py`에 상태 전이 규칙 추가
5. UI 결과가 필요하면 프론트 컴포넌트/타입 업데이트
6. 아래 검증 실행

```bash
cd backend && uv run pytest
cd frontend && npm run build && npm test
```

---

## 참고 문서

- `README.md` — 프로젝트 개요 / 실행법
- `COMMUNICATION_FLOW.md` — 통신 흐름 상세
- `docs/domain_separate.md` — 공통 엔진 vs 도메인 플러그인 분리 설명
