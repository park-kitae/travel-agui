# 여행 AG-UI 채팅 — A2A + AG-UI 프로토콜

React + Vite 프론트엔드와 Google ADK 에이전트를 **A2A → AG-UI** 이중 프로토콜로 연결하는 여행 상담 채팅 웹입니다.

## 주요 기능

- **호텔 검색**: 도시, 날짜, 인원수를 기반으로 호텔 추천
- **항공편 검색**: 출발지, 목적지, 날짜, 인원수로 왕복 항공편 검색
- **여행 정보**: 목적지별 여행 팁 및 관광 정보 제공
- **사용자 입력 폼**: 정보가 부족할 때 대화형 폼으로 필요한 정보 수집
- **실시간 스트리밍**: SSE를 통한 에이전트 응답 실시간 렌더링
- **툴 실행 표시**: 호텔/항공편 검색 진행 상태 실시간 표시

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
```

### 레이어별 역할

| 레이어 | 파일 | 역할 |
|---|---|---|
| **React Client** | `frontend/src/` | AG-UI SSE 수신 → 실시간 UI 렌더링 |
| **AG-UI Gateway** | `backend/main.py` | RunAgentInput 수신 → A2A 요청 → AG-UI 이벤트 변환 |
| **A2A Server** | `backend/a2a_server.py` | ADK 에이전트를 A2A 프로토콜로 노출 |
| **ADK Agent** | `backend/agent.py` | LlmAgent + FunctionTool 정의 |

---

## 프로젝트 구조

```
travel-agui/
├── start.sh              # 서버 일괄 시작 스크립트
├── stop.sh               # 서버 종료 스크립트
├── README.md             # 프로젝트 문서
├── AGENT.md              # 에이전트 개발 가이드
├── logs/                 # 서버 로그 파일 (gitignore)
├── backend/
│   ├── agent.py          # ADK LlmAgent + FunctionTool 정의
│   │                     #   - search_hotels / search_flights
│   │                     #   - get_travel_tips / request_user_input
│   ├── a2a_server.py     # A2A 에이전트 서버 (포트 8001)
│   │                     #   ADKAgentExecutor: ADK 이벤트 → A2A 이벤트 변환
│   ├── main.py           # AG-UI 게이트웨이 (포트 8000)
│   │                     #   A2AClient: A2A 이벤트 → AG-UI 이벤트 변환
│   ├── requirements.txt
│   ├── .env.example
│   └── .venv/            # Python 가상환경
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   └── useAGUIChat.ts        # AG-UI SSE 스트림 처리 훅
│   │   ├── components/
│   │   │   ├── ChatMessageBubble.tsx
│   │   │   ├── ToolCallIndicator.tsx  # 실시간 툴 실행 상태 표시
│   │   │   └── ToolResultCard.tsx     # 호텔/항공/여행팁 카드 렌더링
│   │   ├── types/index.ts
│   │   ├── App.tsx
│   │   └── index.css
│   ├── vite.config.ts    # /agui → :8000 프록시
│   ├── package.json
│   └── node_modules/
└── tests/
    ├── e2e/              # Playwright E2E 테스트 스크립트
    ├── screenshots/      # 테스트 스크린샷 (gitignore)
    └── README.md         # 테스트 문서
```

---

## 실행 방법

### 빠른 시작 (권장)

프로젝트 루트에서 한 번에 실행:

```bash
# 1. 환경 변수 설정 (최초 1회)
cd backend
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 입력

# 2. 백엔드 가상환경 생성 및 패키지 설치 (최초 1회)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. 프론트엔드 패키지 설치 (최초 1회)
cd frontend
npm install
cd ..

# 4. 서버 시작 (백엔드 + 프론트엔드 동시 실행)
./start.sh
# → A2A 서버: http://localhost:8001
# → AG-UI 게이트웨이: http://localhost:8000
# → 프론트엔드: http://localhost:5173

# 5. 서버 종료
# Ctrl+C 또는 별도 터미널에서:
./stop.sh
```

**start.sh 기능:**
- 기존 프로세스 자동 종료 (포트 충돌 방지)
- 백엔드 A2A 서버 시작 및 헬스체크
- 프론트엔드 개발 서버 시작 및 헬스체크
- 실시간 로그 출력 (`logs/` 디렉토리)
- Ctrl+C로 모든 서버 graceful shutdown

**stop.sh 옵션:**
```bash
./stop.sh              # 서버 종료
./stop.sh --clean-logs # 서버 종료 + 로그 파일 삭제
```

### 수동 실행 (개발 시 디버깅용)

터미널 3개를 사용하여 개별 실행:

```bash
# 터미널 1 — A2A 에이전트 서버 (포트 8001)
cd backend
source .venv/bin/activate
python a2a_server.py

# 터미널 2 — AG-UI 게이트웨이 (포트 8000)
cd backend
source .venv/bin/activate
python main.py

# 터미널 3 — 프론트엔드 개발 서버 (포트 5173)
cd frontend
npm run dev
```

### 테스트 질문 예시

- `도쿄 호텔 추천해줘 (6월 10일~14일, 2명)`
- `서울에서 오사카 항공편 검색해줘 (7월 1일, 2명)`
- `방콕 여행 정보 알려줘`

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

#### main.py 변환 규칙

```
TextPart          → TEXT_MESSAGE_START / CHUNK / END
DataPart._agui_event == "TOOL_CALL_START" → TOOL_CALL_START + TOOL_CALL_ARGS
DataPart._agui_event == "TOOL_CALL_END"   → TOOL_CALL_END
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

---

## 환경 요구사항

- Python 3.11+
- Node.js 18+
- Google Gemini API Key

## 의존성 (requirements.txt)

```
google-adk>=1.0.0
a2a-sdk>=0.2.0
ag-ui-protocol>=0.1.14
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
python-dotenv>=1.0.0
pydantic>=2.0.0
httpx>=0.27.0
```

---

## E2E 테스트

Playwright를 사용한 E2E 테스트 스위트가 포함되어 있습니다.

### 테스트 실행

```bash
# 서버가 실행 중이어야 함 (./start.sh)
node tests/e2e/test-full-flow.js
node tests/e2e/test-hotel-direct.js
node tests/e2e/test-flight-form.js
# ... 기타 테스트
```

### 주요 테스트 시나리오

| 테스트 파일 | 목적 |
|---|---|
| `test-full-flow.js` | 호텔 + 항공편 검색 전체 플로우 |
| `test-hotel-direct.js` | 모든 정보가 포함된 직접 검색 |
| `test-default-values.js` | 폼 기본값 자동 설정 확인 |
| `test-natural-language.js` | 폼 제출 시 자연어 메시지 변환 |
| `test-flight-form.js` | 항공편 폼 및 왕복 옵션 |
| `test-form-submit.js` | 폼 제출 후 상태 변화 |
| `test-form-values.js` | 폼 입력값 확인 |

**상세 문서**: `tests/README.md` 참조

### 스크린샷

테스트 실행 시 스크린샷이 `tests/screenshots/` 디렉토리에 저장됩니다.

---

## 트러블슈팅

### 포트 충돌

**문제**: `Address already in use` 에러 발생

**해결**:
```bash
# 특정 포트 사용 프로세스 확인
lsof -ti :8001  # A2A 서버
lsof -ti :8000  # AG-UI 게이트웨이
lsof -ti :5173  # 프론트엔드

# 모든 서버 종료
./stop.sh
```

### 서버 시작 실패

**문제**: 백엔드 또는 프론트엔드 서버가 시작되지 않음

**해결**:
```bash
# 로그 확인
cat logs/backend.log
cat logs/frontend.log

# 수동으로 개별 실행하여 에러 확인
cd backend
source .venv/bin/activate
python a2a_server.py  # 또는 python main.py
```

### 환경 변수 누락

**문제**: `GOOGLE_API_KEY not found` 에러

**해결**:
```bash
cd backend
cp .env.example .env
# .env 파일을 열어 GOOGLE_API_KEY 입력
```

### LLM 응답 없음 또는 타임아웃

**문제**: 메시지 전송 후 응답이 오지 않음

**확인 사항**:
1. A2A 서버와 AG-UI 게이트웨이가 모두 실행 중인지 확인
2. `logs/backend.log`에서 Gemini API 호출 에러 확인
3. API 키 유효성 확인
4. 네트워크 연결 확인

### 테스트 실패

**문제**: E2E 테스트가 실패하거나 타임아웃

**해결**:
```bash
# 서버가 실행 중인지 확인
curl http://localhost:8001/.well-known/agent-card.json
curl http://localhost:5173

# 서버 재시작
./stop.sh
./start.sh

# 테스트 재실행
node tests/e2e/test-full-flow.js
```

### 사용자 입력 폼이 표시되지 않음

**문제**: 호텔이나 항공편 검색 시 폼이 나타나지 않음

**현재 상태**:
- 직접 검색 (모든 정보 포함): 정상 작동
  - 예: "도쿄 호텔 추천해줘 (6월 10일~14일, 2명)"
- 부분 정보 검색: 폼이 나타나지 않는 이슈 있음
  - 예: "서울 호텔 알려줘"

**임시 해결**: 모든 정보를 포함하여 질문
- 호텔: "도시명 + 날짜 + 인원수"
- 항공편: "출발지 + 목적지 + 날짜 + 인원수"

---

## 개발 가이드

### 에이전트 수정

에이전트의 동작을 수정하려면 `backend/agent.py`를 편집하세요. 자세한 내용은 **AGENT.md**를 참조하세요.

### 새로운 FunctionTool 추가

1. `backend/agent.py`에 새 함수 정의
2. `FunctionTool`로 래핑하여 `tools` 리스트에 추가
3. LlmAgent `instruction`에 사용법 추가
4. 프론트엔드에서 결과 렌더링 (필요 시 `ToolResultCard.tsx` 수정)

### AG-UI 이벤트 커스터마이징

프론트엔드에서 새로운 이벤트 타입을 처리하려면:
1. `frontend/src/types/index.ts`에 타입 정의 추가
2. `frontend/src/hooks/useAGUIChat.ts`에서 이벤트 처리 로직 추가
3. 필요한 컴포넌트 생성 또는 수정

---

## 라이선스

MIT

## 문의

문제가 발생하거나 질문이 있으면 이슈를 등록해주세요.
