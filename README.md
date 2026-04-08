# 여행 AG-UI 채팅 — A2A + AG-UI 프로토콜

React + Vite 프론트엔드와 Google ADK 에이전트를 **A2A → AG-UI** 이중 프로토콜로 연결하는 여행 상담 채팅 웹입니다.

## 주요 기능

- **호텔 검색**: 도시, 날짜, 인원수를 기반으로 호텔 추천
- **호텔 상세 조회**: 호텔 카드 클릭 시 객실 정보, 편의시설, 위치 등 상세 정보 표시
- **항공편 검색**: 출발지, 목적지, 날짜, 인원수로 왕복 항공편 검색
- **여행 정보**: 목적지별 여행 팁 및 관광 정보 제공
- **사용자 입력 폼**: 정보가 부족할 때 대화형 폼으로 필요한 정보 수집 (기존 날짜·인원 자동 pre-fill)
- **여행 컨텍스트 재사용**: 호텔 조회 후 항공편 문의 시(또는 반대) 기존 날짜·인원을 자동으로 폼에 적용
- **핵심 상태 보호**: 목적지·날짜·인원 등 핵심 여행 정보는 호텔 상세 조회 등 부분 업데이트에 의해 초기화되지 않음
- **실시간 스트리밍**: SSE를 통한 에이전트 응답 실시간 렌더링
- **툴 실행 표시**: 호텔/항공편 검색 진행 상태 실시간 표시
- **스트림 인터럽트**: 응답 중에도 호텔 클릭 시 현재 스트림을 중단하고 즉시 새 요청 전송
- **State Flow 패널**: 핵심 여행 정보(고정) → 클라이언트 상태 → 에이전트 상태 순으로 한눈에 확인

---

## 아키텍처

```
React (Vite :5173)
    │  POST /agui/run  (RunAgentInput)
    │  ◄── SSE stream  (AG-UI Events)
    ▼
AG-UI Gateway  (FastAPI :8000)  ← main.py
    │  A2AClient.send_message_streaming()
    │  ◄── SSE stream  (A2A Events)
    ▼
A2A Agent Server  (Starlette :8001)  ← a2a_server.py
    │  ADKAgentExecutor.execute()
    ▼
ADK Runner → Gemini LLM + FunctionTools
    search_hotels / search_flights / get_travel_tips
    get_hotel_detail / request_user_input
```

### 레이어별 역할

| 레이어 | 파일 | 역할 |
|---|---|---|
| **React Client** | `frontend/src/` | AG-UI SSE 수신 → 실시간 UI 렌더링, travel_context 포함 전송 |
| **AG-UI Gateway** | `backend/main.py` | RunAgentInput 수신 → travel_context 주입 → A2A 요청 → AG-UI 이벤트 변환 |
| **A2A Server** | `backend/a2a_server.py` | ADK 에이전트를 A2A 프로토콜로 노출, agent_state STATE_SNAPSHOT 발행 |
| **ADK Agent** | `backend/agent.py` | LlmAgent + FunctionTool 정의, 여행 컨텍스트 재사용 프롬프트 |

---

## 프로젝트 구조

```
travel-agui/
├── start.py              # 서버 일괄 시작 스크립트 (macOS/Windows 공통)
├── README.md
├── AGENT.md              # 에이전트 개발 가이드
├── logs/                 # 서버 로그 파일 (gitignore)
├── backend/
│   ├── agent.py          # ADK LlmAgent + FunctionTool 정의
│   ├── a2a_server.py     # A2A 에이전트 서버 (포트 8001)
│   ├── main.py           # AG-UI 게이트웨이 (포트 8000)
│   ├── tests/            # 백엔드 Pytest 테스트 스위트
│   │   ├── test_a2a_stream.py # A2A 스트리밍 검증
│   │   └── test_agui_run.py   # AG-UI /agui/run 엔드포인트 검증
│   ├── pyproject.toml    # uv 프로젝트 설정 및 의존성
│   └── .env.example      # 환경 변수 템플릿
├── frontend/
│   ├── src/              # 프론트엔드 소스 코드
│   ├── tests/            # Playwright Test 기반 E2E 스위트 (이동됨)
│   │   ├── e2e/          # 서비스별 E2E 시나리오
│   │   └── README.md
│   ├── vite.config.ts    # /agui → :8000 프록시
│   └── package.json
└── openspec/             # OpenSpec 변경 관리 및 스키마
    ├── changes/          # 변경 이력 관리
    └── schemas/          # spec-driven-with-tests 커스텀 스키마
```

---

## 실행 방법

### 사전 요구사항

| 항목 | 버전 | 설치 |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org) |
| uv | 최신 | 아래 참고 |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Google Gemini API Key | — | [aistudio.google.com](https://aistudio.google.com) |

#### uv 설치

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### 빠른 시작 (권장)

#### macOS / Linux

```bash
# 1. 환경 변수 설정 (최초 1회)
cp backend/.env.example backend/.env
# backend/.env 파일에 GOOGLE_API_KEY 입력

# 2. 백엔드 의존성 설치 (최초 1회)
cd backend && uv sync && cd ..

# 3. 프론트엔드 패키지 설치 (최초 1회)
cd frontend && npm install && cd ..

# 4. 서버 시작
python start.py
```

#### Windows

```powershell
# 1. 환경 변수 설정 (최초 1회)
copy backend\.env.example backend\.env
# backend\.env 파일에 GOOGLE_API_KEY 입력

# 2. 백엔드 의존성 설치 (최초 1회)
cd backend; uv sync; cd ..

# 3. 프론트엔드 패키지 설치 (최초 1회)
cd frontend; npm install; cd ..

# 4. 서버 시작
python start.py
```

**서버 주소:**
- A2A 에이전트 서버: http://localhost:8001
- AG-UI 게이트웨이: http://localhost:8000
- 프론트엔드 UI: http://localhost:5173

**종료:** `Ctrl+C`

**start.py 자동 처리 항목:**
- 기존 프로세스 자동 종료 (포트 충돌 방지)
- `uv sync`로 의존성 최신화
- 백엔드 A2A 서버 시작 및 헬스체크
- 프론트엔드 개발 서버 시작 및 헬스체크
- 실시간 로그 출력 (`logs/` 디렉토리)
- Ctrl+C로 모든 서버 graceful shutdown

---

### 수동 실행 (개발 시 디버깅용)

터미널 3개를 사용하여 개별 실행합니다.

```bash
# 터미널 1 — A2A 에이전트 서버 (포트 8001)
cd backend
uv run python a2a_server.py

# 터미널 2 — AG-UI 게이트웨이 (포트 8000)
cd backend
uv run python main.py

# 터미널 3 — 프론트엔드 개발 서버 (포트 5173)
cd frontend
npm run dev
```

---

### 테스트 질문 예시

- `도쿄 호텔 추천해줘 (6월 10일~14일, 2명)` → 호텔 목록 카드 표시, 클릭 시 상세 정보 조회
- `서울에서 오사카 항공편 검색해줘 (7월 1일, 2명)`
- `방콕 여행 정보 알려줘`
- `서울 호텔 알려줘` → 날짜/인원 입력 폼 자동 표시

---

## 이벤트 흐름 상세

### AG-UI 이벤트 (Client ↔ Gateway)

```
Client → POST /agui/run
  { threadId, runId, messages: [{role:"user", content:"..."}], ... }

Gateway → SSE stream:
  data: {"type":"RUN_STARTED", ...}
  data: {"type":"STEP_STARTED", "stepName":"에이전트 처리 중"}
  data: {"type":"TEXT_MESSAGE_START", "messageId":"...", "role":"assistant"}
  data: {"type":"TEXT_MESSAGE_CHUNK", "messageId":"...", "delta":"호텔을 검색합니다..."}
  data: {"type":"TOOL_CALL_START", "toolCallId":"...", "toolCallName":"search_hotels"}
  data: {"type":"TOOL_CALL_ARGS",  "toolCallId":"...", "delta":"{\"city\":\"도쿄\",...}"}
  data: {"type":"TOOL_CALL_END",   "toolCallId":"..."}
  data: {"type":"STATE_SNAPSHOT",  "snapshot":{"tool":"search_hotels","result":{...}}}
  data: {"type":"USER_INPUT_REQUEST", "requestId":"...", "inputType":"hotel_booking_details", "fields":[...]}
  data: {"type":"TEXT_MESSAGE_END", "messageId":"..."}
  data: {"type":"STEP_FINISHED", ...}
  data: {"type":"RUN_FINISHED", ...}
```

### A2A 이벤트 인코딩 (a2a_server → main.py)

ADK 이벤트를 A2A `TaskArtifactUpdateEvent` 의 파트로 인코딩해 전달합니다.

| ADK 이벤트 | A2A Part 타입 | 인코딩 구조 |
|---|---|---|
| `text` (스트리밍) | `TextPart` | `{ text: "..." }` |
| `function_call` | `DataPart` | `{ "_agui_event": "TOOL_CALL_START", "id": "...", "name": "search_hotels", "args": {...} }` |
| `function_response` (종료 신호) | `DataPart` | `{ "_agui_event": "TOOL_CALL_END", "id": "..." }` |
| `function_response` (결과) | `DataPart` | `{ "tool": "search_hotels", "result": {...} }` |
| `request_user_input` | `DataPart` | `{ "_agui_event": "USER_INPUT_REQUEST", "requestId": "...", "inputType": "...", "fields": [...] }` |
| `function_call` (agent_state) | `DataPart` | `{ "snapshot_type": "agent_state", "travel_context": {...}, "agent_status": {...} }` |

#### main.py 변환 규칙

```
TextPart          → TEXT_MESSAGE_START / CHUNK / END
DataPart._agui_event == "TOOL_CALL_START"      → TOOL_CALL_START + TOOL_CALL_ARGS
DataPart._agui_event == "TOOL_CALL_END"        → TOOL_CALL_END
DataPart._agui_event == "USER_INPUT_REQUEST"   → USER_INPUT_REQUEST (폼 렌더링)
DataPart (나머지)  → STATE_SNAPSHOT  (프론트 ToolResultCard 렌더링)
TaskStatusUpdateEvent (working)    → STEP_STARTED
TaskStatusUpdateEvent (completed)  → STEP_FINISHED
```

---

## 핵심 구현 포인트

### ADKAgentExecutor (a2a_server.py)

`google.adk.a2a.executor.ADKAgentExecutor`가 설치된 버전에 없으므로 `a2a.server.agent_execution.AgentExecutor`를 직접 상속해 구현합니다.

```python
class ADKAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        # ADK runner.run_async() 실행
        # → function_call  → DataPart(_agui_event=TOOL_CALL_START)
        # → text           → TextPart
        # → function_resp  → DataPart(_agui_event=TOOL_CALL_END) + DataPart(tool result)
        # → completed      → TaskStatusUpdateEvent(state=completed)
```

### A2AStarletteApplication 빌드

```python
a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),   # 필수
    ),
)
app = a2a_app.build()  # .build() 호출로 실제 Starlette ASGI 앱 생성
```

### AgentCard 필수 필드

```python
AgentCard(
    name="...",
    description="...",
    url="http://localhost:8001/",
    version="1.0.0",                       # 필수
    default_input_modes=["text/plain"],    # 필수
    default_output_modes=["text/plain"],   # 필수
    capabilities=AgentCapabilities(streaming=True),
    skills=[AgentSkill(id="..", name="..", description="..", tags=[..])],
)
```

### A2AClient 초기화

```python
# httpx_client 키워드 사용 (http_client 아님)
a2a_client = A2AClient(httpx_client=http_client, agent_card=agent_card)

# 스트리밍은 SendStreamingMessageRequest 사용
request = SendStreamingMessageRequest(id=..., params=MessageSendParams(...))
async for response in a2a_client.send_message_streaming(request):
    result = response.root.result  # Task | Message | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
```

### 메시지 id 자동 부여 (main.py)

AG-UI `BaseMessage`는 `id` 필드가 필수입니다. 클라이언트가 id 없이 보낼 경우 서버에서 자동 부여합니다.

```python
for msg in body["messages"]:
    if isinstance(msg, dict) and "id" not in msg:
        msg["id"] = str(uuid.uuid4())
```

### 양방향 상태 동기화 (travel_context)

프론트엔드는 매 요청마다 누적된 `agentState.travel_context`를 서버로 전송합니다. 서버는 이를 파싱해 사용자 메시지 앞에 컨텍스트 블록으로 주입합니다.

```
[현재 여행 컨텍스트 - 이미 확인된 정보]
- 목적지: 도쿄
- 체크인/출발일: 2026-06-10
- 체크아웃/귀국일: 2026-06-14
- 인원: 2명

사용자 요청: 항공편도 알려줘
```

에이전트는 이 컨텍스트를 읽고 날짜·인원을 재사용해 `search_flights` 또는 `request_user_input` 에 자동 반영합니다.

**핵심 상태 보호**: `STATE_SNAPSHOT` 이벤트 수신 시 `destination`, `check_in`, `check_out`, `nights`, `guests`, `origin`, `trip_type` 필드는 null로 덮어쓰지 않습니다. 호텔 상세 조회처럼 부분적인 상태 업데이트가 오더라도 기존 여행 정보가 유지됩니다.

---

### 호텔 클릭 → 상세 조회 흐름 (interruptAndSend)

응답 스트리밍 중에도 호텔 카드를 클릭하면 현재 스트림을 중단하고 즉시 상세 조회 요청을 전송합니다.

```typescript
// useAGUIChat.ts
const interruptAndSend = useCallback((userText: string) => {
  abortRef.current?.abort()       // 기존 SSE 스트림 중단
  isRunningRef.current = false    // ref 즉시 동기 업데이트
  setIsRunning(false)
  setTimeout(() => sendMessage(userText), 0)  // 다음 틱에 새 메시지 전송
}, [sendMessage])

// App.tsx
const handleHotelClick = (hotelCode: string, hotelName: string) => {
  interruptAndSend(`${hotelName}(${hotelCode}) 호텔의 상세 정보를 알려줘`)
}
```

> **isRunningRef**: `useState`의 `isRunning`은 비동기로 업데이트되어 stale closure 문제가 발생할 수 있습니다. `useRef`로 동기 상태를 별도 관리하여 해결합니다.

---

## 환경 요구사항

- Python 3.11+
- uv (패키지 매니저)
- Node.js 18+
- Google Gemini API Key

## 의존성 (backend/pyproject.toml)

```toml
dependencies = [
    "google-adk>=1.0.0",
    "a2a-sdk>=0.2.0",
    "ag-ui-protocol>=0.1.14",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
]
```

의존성 추가 시:
```bash
cd backend
uv add <패키지명>
```

---

## 테스트 실행

### 1. 백엔드 유닛/통합 테스트 (Pytest)

```bash
cd backend
uv run pytest
```

### 2. 프론트엔드 E2E 테스트 (Playwright)

현재 E2E 테스트는 `frontend/` 디렉토리 내에서 실행됩니다.

```bash
# 서버가 실행 중이어야 함 (python start.py)
cd frontend

# 전체 E2E 실행
npm test

# 브라우저를 보면서 실행
npm run test:e2e:headed

# Playwright UI 모드
npm run test:ui
```

### 주요 테스트 시나리오 (frontend/tests/e2e/)

| 테스트 파일 | 목적 |
|---|---|
| `frontend/tests/e2e/full-flow.spec.ts` | 호텔 + 항공편 검색 전체 플로우 |
| `frontend/tests/e2e/hotel-direct-search.spec.ts` | 모든 정보가 포함된 호텔 직접 검색 |
| `frontend/tests/e2e/hotel-detail-click.spec.ts` | 호텔 카드 클릭 → 상세 정보 조회 |
| `frontend/tests/e2e/default-values.spec.ts` | 호텔 폼 기본값 자동 설정 확인 |
| `frontend/tests/e2e/natural-language.spec.ts` | 폼 제출 시 자연어 메시지 변환 |
| `frontend/tests/e2e/flight-form.spec.ts` | 항공편 폼 기본값 및 자동 입력 |
| `frontend/tests/e2e/form-submit.spec.ts` | 호텔 폼 제출 후 결과 표시 |
| `frontend/tests/e2e/form-values.spec.ts` | 호텔 폼 입력값과 제출 상태 확인 |
| `frontend/tests/e2e/assistant-response-check.spec.ts` | 툴 호출/폼 렌더링 응답 검증 |
| `frontend/tests/e2e/response-capture.spec.ts` | `/agui/run` SSE 응답 캡처 검증 |

### 아티팩트

- 실패 시 Playwright 스크린샷/비디오/trace가 자동 저장됩니다.
- HTML 리포트는 `playwright-report/`에 생성됩니다.

---

## 트러블슈팅

### 포트 충돌

**문제**: `Address already in use` 에러 발생

**macOS / Linux**
```bash
lsof -ti :8001 | xargs kill -9
lsof -ti :8000 | xargs kill -9
lsof -ti :5173 | xargs kill -9
```

**Windows (PowerShell)**
```powershell
netstat -ano | findstr :8001
netstat -ano | findstr :8000
netstat -ano | findstr :5173
# PID로 프로세스 종료 (예: PID 1234)
taskkill /F /PID 1234
```

---

### 서버 시작 실패

**문제**: 백엔드 또는 프론트엔드 서버가 시작되지 않음

```bash
# 로그 확인
cat logs/backend.log
cat logs/gateway.log
cat logs/frontend.log

# 수동 실행으로 에러 확인
cd backend && uv run python a2a_server.py
```

---

### uv 명령어를 찾을 수 없음

**문제**: `uv: command not found` 또는 `'uv'은(는) 내부 또는 외부 명령...`

**macOS / Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # 또는 source ~/.zshrc
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# PowerShell 재시작 후 사용 가능
```

---

### 환경 변수 누락

**문제**: `GOOGLE_API_KEY not found` 에러

```bash
# macOS / Linux
cp backend/.env.example backend/.env

# Windows
copy backend\.env.example backend\.env
notepad backend\.env
```

---

### LLM 응답 없음 또는 타임아웃

**확인 사항**:
1. A2A 서버와 AG-UI 게이트웨이가 모두 실행 중인지 확인
2. `logs/backend.log`에서 Gemini API 호출 에러 확인
3. API 키 유효성 확인
4. 네트워크 연결 확인

---

### 테스트 실패

**문제**: E2E 테스트가 실패하거나 타임아웃

```bash
# 서버 상태 확인
curl http://localhost:8001/.well-known/agent-card.json
curl http://localhost:5173

# 서버 재시작
python start.py
npm test
```

---

## 개발 가이드

### 에이전트 수정

에이전트의 동작을 수정하려면 `backend/agent.py`를 편집하세요. 자세한 내용은 **AGENT.md**를 참조하세요.

### 새로운 FunctionTool 추가

1. `backend/agent.py`에 새 함수 정의 (각 호텔/결과에 고유 코드 포함 권장)
2. `FunctionTool`로 래핑하여 `tools` 리스트에 추가
3. LlmAgent `instruction`에 사용법 추가
4. 프론트엔드에서 결과 렌더링 (필요 시 `ToolResultCard.tsx` 수정)

### AG-UI 이벤트 커스터마이징

프론트엔드에서 새로운 이벤트 타입을 처리하려면:
1. `frontend/src/types/index.ts`에 타입 정의 추가
2. `frontend/src/hooks/useAGUIChat.ts`에서 이벤트 처리 로직 추가
3. 필요한 컴포넌트 생성 또는 수정

### 호텔 데이터 확장

`backend/agent.py`의 `hotel_db` 딕셔너리에 도시와 호텔을 추가합니다. 각 호텔에는 반드시 `hotel_code` 필드(형식: `HTL-XXX-000`)를 포함해야 상세 조회 기능이 동작합니다.

```python
hotel_db = {
    "새도시": [
        {"hotel_code": "HTL-NEW-001", "name": "호텔명", "area": "지역", ...},
    ]
}
```

---

## 라이선스

MIT

## 문의

문제가 발생하거나 질문이 있으면 이슈를 등록해주세요.
