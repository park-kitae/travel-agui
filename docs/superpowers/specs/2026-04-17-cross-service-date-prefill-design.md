# Cross-Service Date Prefill 설계 스펙

**날짜:** 2026-04-17  
**범위:** `request_user_input` 발행 시 호텔/항공 날짜 자동 연동 보강

---

## 배경

현재 여행 상태의 canonical 날짜 필드는 `TravelContext.check_in` / `TravelContext.check_out` 이다.

- 호텔 검색은 `check_in` / `check_out` 을 그대로 사용한다.
- 항공 검색은 `departure_date` 를 `TravelContext.check_in` 으로 저장하지만, `return_date` 는 `TravelContext.check_out` 으로 저장하지 않는다.
- `request_user_input()` 는 전달받은 `context` JSON만 사용해 폼 `default` 값을 채운다.

이 구조 때문에 다음 문제가 생긴다.

1. 사용자가 호텔을 먼저 조회한 뒤 항공 입력 폼을 열면 날짜 재사용은 프롬프트 품질에 의존한다.
2. 사용자가 항공을 먼저 조회한 뒤 호텔 입력 폼을 열면 `return_date` 가 state에 남지 않아 체크아웃 자동 연동이 깨질 수 있다.

사용자 요구사항은 다음과 같다.

- `request_user_input` 를 내려줄 때 먼저 state 값을 확인한다.
- 호텔 입력 폼이면 기존 항공 날짜를 호텔 날짜로 연동한다.
- 항공 입력 폼이면 기존 호텔 날짜를 항공 날짜로 연동한다.
- 값이 없으면 기존 규칙을 유지한다.

---

## 목표

- `USER_INPUT_REQUEST` 이벤트가 프론트로 내려가기 직전에 state 기반 날짜 prefill을 보장한다.
- 호텔/항공 어느 쪽을 먼저 조회했는지와 무관하게 날짜 연동이 일관되게 동작하게 한다.
- 기존 LLM 프롬프트 기반 fallback은 유지하되, 실제 동작은 서버가 보장한다.
- 날짜가 없을 때는 현재 동작을 그대로 유지한다.

---

## 접근 방식 비교

### 접근 1 — StateManager emission 보강 + flight return_date 영속화 (**권장**)

`StateManager.apply_tool_result()` 에서 `request_user_input` 결과를 프론트로 내리기 직전에 현재 `TravelState` 를 확인해 날짜 필드의 기본값을 보강한다. 동시에 `search_flights` 호출 시 `return_date -> TravelContext.check_out` 저장을 추가한다.

**장점**
- 실제 `USER_INPUT_REQUEST` payload 기준으로 보장되므로 LLM 호출 품질에 덜 의존한다.
- 호텔→항공, 항공→호텔 양방향 동작을 서버 레벨에서 일관되게 만들 수 있다.
- 변경 범위가 `state/manager.py` 중심이라 책임이 명확하다.

**단점**
- 폼 기본값 보강 로직이 state 레이어에 추가된다.

### 접근 2 — `input_tools.request_user_input()` 내부 cross-mapping

`request_user_input()` 안에서 `context` JSON에 `check_in/check_out` 혹은 `departure_date/return_date` 가 있으면 반대쪽 필드명으로 변환해 default를 채운다.

**장점**
- 폼 생성 함수 안에서만 처리하므로 구현 위치가 직관적이다.

**단점**
- 여전히 LLM이 충분한 `context` 를 넘겨주지 않으면 동작하지 않는다.
- 글로벌 state를 직접 보지 못하므로 “state 먼저 확인” 요구를 충족하지 못한다.

### 접근 3 — `agent.py` 프롬프트만 수정

에이전트 instruction을 강화해 항상 기존 state를 보고 반대 서비스 날짜를 `request_user_input` 에 담도록 유도한다.

**장점**
- 코드 변경이 가장 작다.

**단점**
- 가장 취약하다. LLM 응답 편차에 따라 실제 폼 기본값이 달라질 수 있다.
- 서버가 보장하지 못하므로 회귀 가능성이 높다.

### 권장안

**접근 1**을 채택한다.

이 변경은 “request_user_input 내려줄 때 state를 먼저 확인”이라는 요구를 가장 정확하게 만족한다. 또한 현재 구조에서 항공 `return_date` 가 canonical state에 보존되지 않는 비대칭 문제를 함께 해결한다.

---

## 설계

### 1. Canonical state 유지 규칙

`TravelContext` 의 canonical 날짜 필드는 계속 `check_in` / `check_out` 으로 유지한다.

- 호텔 검색:
  - `check_in -> TravelContext.check_in`
  - `check_out -> TravelContext.check_out`
- 항공 검색:
  - `departure_date -> TravelContext.check_in`
  - `return_date -> TravelContext.check_out` **(신규 보강)**

즉, 내부 state는 서비스별 필드명을 별도로 저장하지 않고, 공통 일정 표현으로 통일한다.

### 2. `USER_INPUT_REQUEST` 발행 시 날짜 기본값 보강

`StateManager.apply_tool_result(thread_id, "request_user_input", result)` 에 helper를 추가한다.

#### 호텔 입력 폼(`hotel_booking_details`)

- 현재 field `default` 가 비어 있고
- `TravelContext.check_in` 값이 있으면 → `check_in.default` 에 채운다.
- `TravelContext.check_out` 값이 있으면 → `check_out.default` 에 채운다.

#### 항공 입력 폼(`flight_booking_details`)

- 현재 field `default` 가 비어 있고
- `TravelContext.check_in` 값이 있으면 → `departure_date.default` 에 채운다.
- `TravelContext.check_out` 값이 있으면 → `return_date.default` 에 채운다.

#### 우선순위

1. 툴 결과가 이미 가진 `field.default`
2. 현재 `TravelState.travel_context` 의 canonical 날짜
3. 아무 값도 없으면 기존 빈 값 유지

즉, 서버는 **빈 기본값만 보강**하고 이미 명시된 값은 덮어쓰지 않는다.

### 3. 프롬프트 문구 정합성

`backend/agent.py` 의 instruction에는 현재도 cross-service 날짜 재사용 규칙이 적혀 있다. 이 변경 후에는 문구와 실제 동작이 더 일치하게 된다.

필요 시 아래 취지를 반영한 문구만 최소 수정한다.

- state에 기존 일정이 있으면 `request_user_input` 에 자동 반영된다.
- 없으면 기존 기본 규칙을 따른다.

---

## 변경 파일

### 수정
- `backend/state/manager.py`
  - `search_flights` 의 `return_date -> check_out` 저장 추가
  - `request_user_input` 결과 필드 default 보강 helper 추가
- `backend/tests/state/test_manager.py`
  - 항공 `return_date` state 저장 회귀 테스트 추가
  - `request_user_input` USER_INPUT_REQUEST 날짜 보강 테스트 추가
- `backend/tests/state-panel-sidebar/test_context_extraction.py`
  - flight 검색 후 canonical state에 `check_out` 반영 검증 추가
- `backend/agent.py` *(선택적 최소 수정)*
  - 규칙 설명 문구 정합성 업데이트

---

## 데이터 흐름

```text
search_hotels(city, check_in, check_out, guests)
  -> StateManager.apply_tool_call()
  -> TravelContext.check_in/check_out 저장

search_flights(origin, destination, departure_date, passengers, return_date)
  -> StateManager.apply_tool_call()
  -> TravelContext.check_in/check_out 저장

request_user_input(...)
  -> tool result fields 생성
  -> StateManager.apply_tool_result()
  -> 현재 TravelContext 확인
  -> 비어 있는 날짜 default만 보강
  -> USER_INPUT_REQUEST snapshot 발행
```

---

## 테스트 전략

### 단위 테스트

`backend/tests/state/test_manager.py`

1. `search_flights` 호출 시 `return_date` 가 `TravelContext.check_out` 에 저장되는지 검증
2. 호텔 일정이 저장된 상태에서 `flight_booking_details` USER_INPUT_REQUEST 결과가
   - `departure_date.default == check_in`
   - `return_date.default == check_out`
   로 보강되는지 검증
3. 항공 일정이 저장된 상태에서 `hotel_booking_details` USER_INPUT_REQUEST 결과가
   - `check_in.default == check_in`
   - `check_out.default == check_out`
   로 보강되는지 검증
4. 필드 기본값이 이미 존재하면 state 값으로 덮어쓰지 않는지 검증
5. state 값이 없으면 기존 결과가 그대로 유지되는지 검증

### 통합 성격 테스트

`backend/tests/state-panel-sidebar/test_context_extraction.py`

- `search_flights` 후 emitted snapshot의 `travel_context.check_out` 이 채워지는지 검증한다.

---

## 에러 처리 / 비기능 요구사항

- state 값이 `None` 이거나 빈 문자열이면 보강하지 않는다.
- 날짜 형식 검증은 기존 도구/폼 레벨에 맡기고, 이번 변경에서는 값 복사만 수행한다.
- 기존 event payload shape는 유지한다. (`fields` 배열 구조 불변)

---

## 결정 사항

- 내부 canonical date state는 계속 `check_in/check_out` 로 유지한다.
- cross-service prefill은 `request_user_input` **결과 발행 시점**에 보강한다.
- 항공 `return_date` 도 canonical state로 저장한다.
- 값이 없으면 기존 룰을 그대로 유지한다.
