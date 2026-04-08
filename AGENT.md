# 여행 AI 에이전트 개발 가이드

이 문서는 `backend/agent.py`에 정의된 Google ADK 기반 여행 에이전트의 구조와 커스터마이징 방법을 설명합니다.

---

## 목차

1. [ADK Agent 개요](#adk-agent-개요)
2. [에이전트 구조](#에이전트-구조)
3. [FunctionTool 상세](#functiontool-상세)
4. [LLM Instruction 작성](#llm-instruction-작성)
5. [새로운 FunctionTool 추가](#새로운-functiontool-추가)
6. [디버깅 가이드](#디버깅-가이드)
7. [모범 사례](#모범-사례)

---

## ADK Agent 개요

Google Agent Development Kit (ADK)는 LLM 기반 에이전트를 구축하기 위한 프레임워크입니다.

### 핵심 개념

- **LlmAgent**: Gemini LLM을 사용하는 에이전트 인스턴스
- **FunctionTool**: Python 함수를 LLM이 호출할 수 있는 도구로 래핑
- **Instruction**: LLM에게 에이전트의 역할과 도구 사용법을 설명하는 프롬프트
- **Streaming**: 에이전트 응답을 실시간으로 스트리밍

### 아키텍처 위치

```
LLM (Gemini) → LlmAgent → FunctionTools → Python Functions
                  ↑
             Instruction (역할 및 도구 사용법)
```

---

## 에이전트 구조

`backend/agent.py`의 구조:

```python
# 1. FunctionTool로 사용될 Python 함수 정의
def search_hotels(city, check_in, check_out, guests):
    """호텔 검색 로직"""
    return {"hotels": [...]}

def search_flights(...):
    """항공편 검색 로직"""
    return {"flights": [...]}

def request_user_input(...):
    """사용자 입력 폼 요청"""
    return {"fields": [...]}

def get_travel_tips(...):
    """여행 정보 조회"""
    return {"spots": [...]}

# 2. LlmAgent 생성 함수
def create_travel_agent() -> LlmAgent:
    agent = LlmAgent(
        name="travel_agent",
        model="gemini-3-flash-preview",
        description="여행 상담 에이전트",
        instruction="...",  # LLM에게 역할 설명
        tools=[
            FunctionTool(search_hotels),
            FunctionTool(search_flights),
            FunctionTool(request_user_input),
            FunctionTool(get_travel_tips),
        ],
    )
    return agent
```

### 에이전트 생성 파라미터

| 파라미터 | 설명 | 예시 |
|---------|------|------|
| `name` | 에이전트 식별자 | `"travel_agent"` |
| `model` | 사용할 Gemini 모델 | `"gemini-3-flash-preview"` |
| `description` | 에이전트 설명 | `"여행 상담 에이전트"` |
| `instruction` | LLM에게 주는 역할 및 사용법 | 아래 참조 |
| `tools` | FunctionTool 리스트 | `[FunctionTool(func), ...]` |

---

## FunctionTool 상세

### 1. search_hotels

**목적**: 도시와 날짜로 호텔 검색

**시그니처**:
```python
def search_hotels(
    city: str,
    check_in: str,        # YYYY-MM-DD
    check_out: str,       # YYYY-MM-DD
    guests: int = 2
) -> dict
```

**반환 형식**:
```json
{
  "status": "success",
  "city": "도쿄",
  "check_in": "2026-06-10",
  "check_out": "2026-06-14",
  "guests": 2,
  "count": 3,
  "hotels": [
    {
      "name": "파크 하얏트 도쿄",
      "area": "신주쿠",
      "price": 420000,
      "rating": 4.8,
      "stars": 5,
      "city": "도쿄",
      "check_in": "2026-06-10",
      "check_out": "2026-06-14",
      "guests": 2
    },
    ...
  ]
}
```

**사용 시점**:
- 사용자가 도시, 체크인, 체크아웃, 인원수를 **모두** 제공한 경우
- 예: "도쿄 호텔 추천해줘 (6월 10일~14일, 2명)"

---

### 2. search_flights

**목적**: 출발지/목적지와 날짜로 항공편 검색 (편도 또는 왕복)

**시그니처**:
```python
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,    # YYYY-MM-DD
    passengers: int = 1,
    return_date: str = ""   # 빈 문자열이면 편도
) -> dict
```

**반환 형식 (왕복)**:
```json
{
  "status": "success",
  "origin": "서울",
  "destination": "도쿄",
  "departure_date": "2026-07-01",
  "return_date": "2026-07-08",
  "passengers": 2,
  "trip_type": "round_trip",
  "outbound_flights": [
    {
      "airline": "대한항공",
      "flight": "KE703",
      "depart": "09:00",
      "arrive": "11:25",
      "duration": "2h25m",
      "price": 380000,
      "class": "이코노미",
      "departure_date": "2026-07-01",
      "passengers": 2,
      "total_price": 760000,
      "direction": "outbound"
    },
    ...
  ],
  "inbound_flights": [...],
  "outbound_count": 3,
  "inbound_count": 3
}
```

**사용 시점**:
- 출발지, 목적지, 출발 날짜, 인원수를 **모두** 제공한 경우
- 왕복이면 귀국 날짜도 포함
- 예: "서울에서 도쿄 가는 항공편 (7월 1일 출발, 8일 귀국, 2명)"

---

### 3. request_user_input

**목적**: 호텔/항공편 검색에 필요한 정보가 부족할 때 사용자 입력 폼 요청. 기존 여행 컨텍스트(날짜·인원)를 `context`에 담아 전달하면 폼 필드에 자동 pre-fill됩니다.

**시그니처**:
```python
def request_user_input(
    input_type: str,      # "hotel_booking_details" | "flight_booking_details"
    fields: str = "",     # 사용하지 않음 (자동 생성)
    context: str = ""     # 기존 여행 컨텍스트를 JSON 문자열로 전달
) -> dict
```

**context 형식 (JSON 문자열)**:
```python
# 호텔 — 기존 항공 일정이 있는 경우
context = '{"city":"도쿄","check_in":"2026-06-10","check_out":"2026-06-14","guests":2}'

# 항공편 — 기존 호텔 일정이 있는 경우 (체크인→departure_date, 체크아웃→return_date)
context = '{"origin":"서울","destination":"도쿄","departure_date":"2026-06-10","return_date":"2026-06-14","passengers":2}'

# 아무 정보도 없는 경우
context = '{"city":"서울"}'   # 또는 "" 또는 '{}'
```

**반환 형식 (호텔)**:
```json
{
  "status": "user_input_required",
  "input_type": "hotel_booking_details",
  "fields": [
    { "name": "city",      "type": "text",   "label": "도시",    "required": true,  "default": "도쿄" },
    { "name": "check_in",  "type": "date",   "label": "체크인",  "required": true,  "default": "2026-06-10" },
    { "name": "check_out", "type": "date",   "label": "체크아웃","required": true,  "default": "2026-06-14" },
    { "name": "guests",    "type": "number", "label": "인원수",  "required": true,  "default": "2" }
  ]
}
```

**사용 시점**:
- 호텔 검색: 도시, 체크인, 체크아웃, 인원수 중 **하나라도 없을 때**
- 항공편 검색: 출발지, 목적지, 출발 날짜, 인원수 중 **하나라도 없을 때**
- 예: "서울 호텔 알려줘" (날짜와 인원수 없음)

**크로스 서비스 날짜 재사용**:
- 호텔 조회 이력 있음 + 항공편 문의 → `check_in`→`departure_date`, `check_out`→`return_date`, `guests`→`passengers`
- 항공편 조회 이력 있음 + 호텔 문의 → `departure_date`→`check_in`, `return_date`→`check_out`, `passengers`→`guests`

---

### 4. get_travel_tips

**목적**: 목적지의 여행 정보 및 관광지 조회

**시그니처**:
```python
def get_travel_tips(
    destination: str,
    travel_type: str = "일반"
) -> dict
```

**반환 형식**:
```json
{
  "status": "success",
  "destination": "도쿄",
  "travel_type": "일반",
  "overview": "일본의 수도로 최첨단 문화와 전통이 공존하는 도시",
  "best_season": "3-4월(벚꽃), 10-11월(단풍)",
  "currency": "JPY (엔화)",
  "language": "일본어",
  "spots": ["시부야 스크램블 교차로", "아사쿠사 센소지", ...],
  "food": ["스시", "라멘", "야키토리", ...],
  "tips": ["IC카드(스이카) 구매 필수", ...]
}
```

**사용 시점**:
- 사용자가 호텔/항공편이 아닌 **여행지 정보를 요청**할 때
- 예: "도쿄 여행 정보 알려줘", "방콕 관광지 추천해줘"

---

## LLM Instruction 작성

`instruction`은 LLM이 에이전트의 역할을 이해하고 도구를 올바르게 사용하도록 안내하는 프롬프트입니다.

### 현재 Instruction 구조

```python
instruction="""당신은 여행 AI의 AI 여행 상담 전문가입니다.

역할:
- 고객의 여행 계획을 돕고 최적의 호텔, 항공편, 관광 정보를 제공합니다
- 친절하고 전문적인 톤으로 한국어로 응답합니다
- 정확한 정보를 제공하기 위해 항상 도구를 활용합니다

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[현재 여행 컨텍스트] 활용 규칙 (최우선 적용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
메시지 앞에 "[현재 여행 컨텍스트 - 이미 확인된 정보]" 블록이 있으면:
- 해당 정보를 대화의 기준 값으로 사용합니다
- 사용자가 명시적으로 다른 값을 말하지 않는 한 기존 값을 그대로 유지합니다

날짜·인원 자동 재사용 (크로스 서비스 편의성):
- 호텔 조회 이력 있음 + 항공편 문의 → 체크인→departure_date, 체크아웃→return_date, 인원→passengers
- 항공편 조회 이력 있음 + 호텔 문의 → departure_date→check_in, return_date→check_out, passengers→guests
- 목적지가 이미 설정된 경우 도시 재확인 없이 바로 검색 진행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
도구 사용 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 호텔 문의 시:
  1) 기존 컨텍스트 없음
     → request_user_input("hotel_booking_details", "", '{"city":"도시명"}')
  2) 기존 컨텍스트에 날짜·인원 있음
     → request_user_input("hotel_booking_details", "", '{"city":"도시명","check_in":"YYYY-MM-DD","check_out":"YYYY-MM-DD","guests":N}')
  3) 모든 정보 있음 → search_hotels(city, check_in, check_out, guests)
- 항공편 문의 시:
  1) 기존 컨텍스트 없음
     → request_user_input("flight_booking_details", "", '{"origin":"출발지","destination":"목적지"}')
  2) 기존 컨텍스트에 날짜·인원 있음
     → request_user_input("flight_booking_details", "", '{"origin":"서울","destination":"도시","departure_date":"YYYY-MM-DD","return_date":"YYYY-MM-DD","passengers":N}')
  3) 모든 정보 있음 → search_flights(origin, destination, departure_date, passengers, return_date)
- 여행지 정보 → get_travel_tips(destination)
- 호텔 상세 정보 (HTL-XXX-000 형식) → get_hotel_detail(hotel_code)

시나리오 예시:
"서울 호텔 알려줘" → request_user_input("hotel_booking_details", "", '{"city":"서울"}')
"도쿄 6월 10일~14일 2명 호텔" → search_hotels("도쿄", "2026-06-10", "2026-06-14", 2)
(기존 호텔 컨텍스트 있음) + "항공편 알려줘"
  → search_flights("서울", "도쿄", "2026-06-10", 2, "2026-06-14")

응답 형식:
- 검색 결과는 간결하고 보기 좋게 정리해서 제공
- 가격은 항상 원화(원)로 표시
- 기존 컨텍스트 값을 재사용했을 때는 어떤 값을 적용했는지 한 줄로 안내
- 추가 문의가 있으면 편하게 질문하도록 안내
- 이모지를 적절히 활용하여 가독성 향상

제약사항:
- 실제 예약 처리는 불가능하며, 정보 제공만 가능합니다
"""
```

### Instruction 작성 가이드

#### 1. 역할 정의
- 에이전트가 **누구인지**, **무엇을 하는지** 명확히 설명
- 톤, 스타일, 언어 지정

#### 2. 도구 사용 규칙
- **언제** 각 도구를 호출해야 하는지 구체적으로 명시
- 조건문 형식 사용: `~일 때 → ~를 호출`
- **중요**: LLM은 instruction 없이는 언제 도구를 호출할지 모름

#### 3. 구체적인 예시
- 실제 사용자 메시지 예시와 함께 도구 호출 예시 제공
- 예시가 많을수록 LLM의 이해도 향상

#### 4. 응답 형식
- 결과를 어떻게 포맷팅할지 지정
- 단위, 스타일, 추가 안내 사항 명시

#### 5. 제약사항
- 에이전트가 **할 수 없는 것**을 명시
- 오해를 방지하고 사용자 기대치 관리

### Instruction 수정 시 주의사항

`request_user_input` 호출 규칙은 프런트 UX와 직접 연결되므로 가장 먼저 회귀 테스트해야 합니다.

**핵심 규칙**:
1. 호텔/항공편 검색 정보가 하나라도 부족하면 텍스트 질문보다 `request_user_input`을 우선 호출합니다.
2. 이미 문맥에서 알 수 있는 값은 `context` JSON에 담아 폼 기본값을 채웁니다.
3. `context`는 반드시 **유효한 JSON 문자열**이어야 합니다. 구형 문자열 형식(`"도시명"`, `"출발|목적"`)은 하위 호환 처리되지만 신규 개발에서는 JSON을 사용합니다.
4. instruction 수정 후에는 반드시 Playwright E2E로 폼 표시, 기본값, 제출 후 자연어 변환까지 확인합니다.

**권장 표현 예시**:
```
호텔 또는 항공편 검색에서 필수 정보가 하나라도 누락되면
텍스트로 추가 질문하지 말고 반드시 request_user_input을 호출하세요.

# 기존 컨텍스트 없음
- "서울 호텔 알려줘" → request_user_input("hotel_booking_details", "", '{"city":"서울"}')
- "서울에서 도쿄 가는 항공편" → request_user_input("flight_booking_details", "", '{"origin":"서울","destination":"도쿄"}')

# 기존 호텔 컨텍스트 있음 (체크인 2026-06-10, 체크아웃 2026-06-14, 2명) + 항공편 문의
→ request_user_input("flight_booking_details", "", '{"origin":"서울","destination":"도쿄","departure_date":"2026-06-10","return_date":"2026-06-14","passengers":2}')
```

---

## 새로운 FunctionTool 추가

### 예시: 레스토랑 검색 기능 추가

#### 1단계: Python 함수 정의

```python
def search_restaurants(city: str, cuisine: str = "전체", budget: str = "중") -> dict:
    """
    도시와 요리 종류로 레스토랑을 검색합니다.

    Args:
        city: 도시명
        cuisine: 요리 종류 (한식, 일식, 중식, 양식, 전체)
        budget: 예산 (저, 중, 고)

    Returns:
        레스토랑 검색 결과
    """
    restaurant_db = {
        "서울": [
            {"name": "미슐랭 스타 레스토랑", "cuisine": "한식", "rating": 4.9, "price": 150000},
            {"name": "동대문 떡볶이", "cuisine": "한식", "rating": 4.5, "price": 8000},
            # ...
        ],
    }

    # 검색 로직 구현
    results = []
    # ...

    return {
        "status": "success",
        "city": city,
        "cuisine": cuisine,
        "budget": budget,
        "restaurants": results
    }
```

#### 2단계: FunctionTool로 래핑

```python
def create_travel_agent() -> LlmAgent:
    agent = LlmAgent(
        name="travel_agent",
        model="gemini-3-flash-preview",
        description="여행 상담 에이전트",
        instruction="""...""",  # instruction도 업데이트 필요
        tools=[
            FunctionTool(search_hotels),
            FunctionTool(search_flights),
            FunctionTool(request_user_input),
            FunctionTool(get_travel_tips),
            FunctionTool(search_restaurants),  # 새로 추가
        ],
    )
    return agent
```

#### 3단계: Instruction 업데이트

```python
instruction="""...

도구 사용 가이드:
- 호텔 문의 시: ...
- 항공편 문의 시: ...
- 여행지 정보: ...
- 레스토랑 문의 시: search_restaurants(city, cuisine, budget)  # 추가

예시:
"서울 한식 레스토랑 추천해줘" → search_restaurants("서울", "한식", "중")

..."""
```

#### 4단계: 프론트엔드 렌더링 (선택)

검색 결과를 UI에 표시하려면 `frontend/src/components/ToolResultCard.tsx`를 수정:

```tsx
// ToolResultCard.tsx
if (result.tool === "search_restaurants" && result.result.restaurants) {
  return (
    <div className="restaurants-result">
      <h3>레스토랑 검색 결과</h3>
      {result.result.restaurants.map((restaurant, idx) => (
        <RestaurantCard key={idx} restaurant={restaurant} />
      ))}
    </div>
  );
}
```

#### 5단계: 서버 재시작

```bash
./stop.sh
./start.sh
```

---

## 디버깅 가이드

### 1. 로그 확인

**백엔드 로그**:
```bash
tail -f logs/backend.log
```

**실시간 모니터링**:
```bash
./start.sh  # 실시간 로그 출력 포함
```

### 2. LLM이 도구를 호출하지 않는 경우

**증상**:
- 사용자 메시지 전송 후 에이전트가 도구를 호출하지 않고 텍스트만 반환

**디버깅**:
```python
# agent.py에 로깅 추가
import logging
logging.basicConfig(level=logging.DEBUG)

def search_hotels(...):
    logging.debug(f"search_hotels called: city={city}, check_in={check_in}")
    # ...
```

**확인사항**:
1. Instruction에서 도구 사용 조건이 명확한지 확인
2. 예시가 충분한지 확인
3. Gemini API 키가 유효한지 확인
4. 모델 버전 확인 (`gemini-3-flash-preview` 권장)

### 3. 도구 호출 결과가 프론트에 표시되지 않는 경우

**확인 순서**:

1. **A2A 서버 로그 확인**:
   ```bash
   cat logs/backend.log | grep "function_call"
   ```

2. **AG-UI Gateway 로그 확인** (별도 실행 시):
   ```bash
   # main.py 실행 터미널에서 SSE 이벤트 확인
   ```

3. **브라우저 개발자 도구**:
   - Network 탭에서 `/agui/run` 요청의 SSE 스트림 확인
   - `STATE_SNAPSHOT` 이벤트에 도구 결과가 포함되어 있는지 확인

4. **프론트엔드 로그**:
   ```tsx
   // useAGUIChat.ts에서 로깅
   console.log("SSE event:", event);
   ```

### 4. A2A 이벤트 인코딩 확인

`a2a_server.py`의 `ADKAgentExecutor`에서 이벤트 변환 로직 확인:

```python
# function_call 이벤트가 DataPart로 올바르게 변환되는지 확인
async for event in runner.run_async(...):
    if event.type == 'function_call':
        print(f"Function call: {event.name}, args: {event.args}")
```

### 5. 포트 및 서버 상태 확인

```bash
# 모든 서버가 실행 중인지 확인
lsof -ti :8001  # A2A 서버
lsof -ti :8000  # AG-UI Gateway (main.py)
lsof -ti :5173  # 프론트엔드

# AgentCard 확인
curl http://localhost:8001/.well-known/agent-card.json
```

---

## 모범 사례

### 1. 타입 힌트 사용

```python
def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    guests: int = 2
) -> dict:
    """타입 힌트를 명확히 지정"""
```

**이유**:
- Google ADK가 타입 정보를 사용하여 LLM에게 전달
- LLM이 올바른 인자 타입으로 호출하도록 유도

### 2. Docstring 작성

```python
def search_hotels(...) -> dict:
    """
    도시와 날짜로 호텔을 검색합니다.

    Args:
        city: 여행 도시 (예: 도쿄, 오사카, 제주)
        check_in: 체크인 날짜 (YYYY-MM-DD)
        check_out: 체크아웃 날짜 (YYYY-MM-DD)
        guests: 투숙 인원 수

    Returns:
        호텔 검색 결과 목록
    """
```

**이유**:
- ADK가 docstring을 LLM에게 전달하여 도구 이해도 향상
- 개발자 간 협업 시 코드 가독성 향상

### 3. 일관된 반환 형식

```python
# 성공 시
return {
    "status": "success",
    "data": {...}
}

# 실패 시
return {
    "status": "error",
    "message": "에러 메시지"
}
```

**이유**:
- 프론트엔드에서 일관된 방식으로 결과 처리 가능
- 에러 핸들링 간소화

### 4. 기본값 제공

```python
def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    guests: int = 2  # 기본값 제공
) -> dict:
```

**이유**:
- LLM이 일부 인자를 누락해도 함수 호출 가능
- 사용자 경험 향상 (인원수를 명시하지 않아도 작동)

### 5. 명확한 Instruction 작성

```python
# ❌ 나쁜 예
instruction="호텔을 검색할 때는 search_hotels를 사용하세요."

# ✅ 좋은 예
instruction="""
호텔 문의 시:
1) 도시, 체크인, 체크아웃, 인원수가 모두 있으면
   → search_hotels(city, check_in, check_out, guests)
2) 하나라도 누락되면
   → request_user_input("hotel_booking_details", "", "도시명")

예시:
"서울 호텔 알려줘" (날짜 없음)
→ request_user_input("hotel_booking_details", "", "서울")
"""
```

### 6. 테스트 작성

```python
# test_agent.py
def test_search_hotels():
    result = search_hotels("도쿄", "2026-06-10", "2026-06-14", 2)
    assert result["status"] == "success"
    assert len(result["hotels"]) > 0
```

백엔드 로직의 정확성을 검증하기 위해 `pytest`와 `pytest-asyncio`를 사용합니다. 특히 SSE 스트리밍 응답이 올바른 규격으로 전달되는지 확인합니다.

**테스트 파일 구조**:
- `backend/tests/conftest.py`: 테스트용 클라이언트 및 환경 설정
- `backend/tests/test_a2a_stream.py`: A2A 서버의 스트리밍 로직 검증
- `backend/tests/test_agui_run.py`: `/agui/run` 엔드포인트의 통합 검증

**실행 방법**:
```bash
cd backend
uv run pytest
```

#### 6-2. Playwright E2E 회귀 테스트

에이전트 instruction, tool schema, 응답 포맷을 수정했다면 프런트와의 연결까지 함께 검증해야 합니다.

**주요 E2E 파일**:
- `tests/e2e/default-values.spec.ts`
- `tests/e2e/flight-form.spec.ts`
- `tests/e2e/natural-language.spec.ts`
- `tests/e2e/full-flow.spec.ts`
- `tests/e2e/response-capture.spec.ts`

**실행**:
```bash
# 프론트엔드 디렉토리로 이동 후 실행 (서버는 미리 실행되어 있어야 함)
cd frontend
npm test

# 특정 시나리오만 실행
npx playwright test tests/e2e/full-flow.spec.ts
```

**특히 확인할 회귀 포인트**:
1. `request_user_input` 호출 시 `.user-input-form` 이 표시되는지
2. `context` 값이 도시/출발지/목적지 기본값으로 반영되는지
3. 폼 제출 후 자연어 사용자 메시지가 다시 생성되는지
4. `search_hotels`, `search_flights` 결과가 `.tool-card`로 렌더링되는지

### 7. 에러 처리

```python
def search_hotels(city, check_in, check_out, guests):
    try:
        # 검색 로직
        if not city:
            return {
                "status": "error",
                "message": "도시명이 필요합니다."
            }
        # ...
    except Exception as e:
        return {
            "status": "error",
            "message": f"검색 중 오류 발생: {str(e)}"
        }
```

---

## 참고 자료

- [Google ADK 공식 문서](https://github.com/google/agent-development-kit)
- [A2A Protocol 스펙](https://github.com/a2a-sdk)
- [AG-UI Protocol 스펙](https://github.com/ag-ui-protocol)
- [Gemini API 문서](https://ai.google.dev/docs)

---

## 문의

에이전트 개발 관련 문의는 프로젝트 관리자에게 연락해주세요.
