# 여행 AG-UI 채팅 — A2A + AG-UI 프로토콜

React + Vite 프론트엔드와 Google ADK 에이전트를 **A2A → AG-UI** 이중 프로토콜로 연결하는 여행 상담 채팅 웹입니다.

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
├── backend/
│   ├── agent.py          # ADK LlmAgent + FunctionTool 정의 (search_hotels 등)
│   ├── a2a_server.py     # A2A 에이전트 서버 (포트 8001)
│   │                     #   ADKAgentExecutor: ADK 이벤트 → A2A 이벤트 변환
│   ├── main.py           # AG-UI 게이트웨이 (포트 8000)
│   │                     #   A2AClient: A2A 이벤트 → AG-UI 이벤트 변환
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── hooks/
    │   │   └── useAGUIChat.ts        # AG-UI SSE 스트림 처리 훅
    │   ├── components/
    │   │   ├── ChatMessageBubble.tsx
    │   │   ├── ToolCallIndicator.tsx  # 실시간 툴 실행 상태 표시
    │   │   └── ToolResultCard.tsx     # 호텔/항공/여행팁 카드 렌더링
    │   ├── types/index.ts
    │   ├── App.tsx
    │   └── index.css
    ├── vite.config.ts    # /agui → :8000 프록시
    └── package.json
```

---

## 실행 방법

### 1. 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# GOOGLE_API_KEY 입력
```

### 3. 백엔드 실행 (터미널 2개)

```bash
# 터미널 1 — A2A 에이전트 서버 (포트 8001)
python a2a_server.py

# 터미널 2 — AG-UI 게이트웨이 (포트 8000)
python main.py
```

### 4. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. 테스트 질문 예시

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
