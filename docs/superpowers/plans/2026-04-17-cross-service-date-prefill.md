# Cross-Service Date Prefill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `request_user_input` 를 프론트로 내릴 때 현재 여행 state를 기준으로 호텔/항공 날짜를 자동 연동하고, 값이 없으면 기존 동작을 유지한다.

**Architecture:** `TravelContext.check_in/check_out` 를 canonical 일정 상태로 계속 사용한다. `StateManager.apply_tool_call()` 에서 항공 `return_date` 를 `check_out` 으로 저장하고, `StateManager.apply_tool_result()` 에서 `request_user_input` 결과의 비어 있는 날짜 기본값만 state 기반으로 보강한다.

**Tech Stack:** Python 3.11+, dataclasses, ag-ui-protocol, pytest, pytest-asyncio, uv

---

## File Map

| 파일 | 변경 |
|------|------|
| `backend/state/manager.py` | 수정 — 항공 `return_date` state 저장 및 `request_user_input` 날짜 prefill helper 추가 |
| `backend/tests/state/test_manager.py` | 수정 — state 저장 / USER_INPUT_REQUEST prefill 회귀 테스트 추가 |
| `backend/tests/state-panel-sidebar/test_context_extraction.py` | 수정 — flight 검색 후 canonical `check_out` 반영 검증 추가 |
| `backend/agent.py` | 선택 수정 — 규칙 설명 문구 정합성 업데이트 |

---

## Task 1: failing tests for canonical flight return date storage

**Files:**
- Modify: `backend/tests/state/test_manager.py`
- Modify: `backend/tests/state-panel-sidebar/test_context_extraction.py`
- Test: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state-panel-sidebar/test_context_extraction.py`

- [ ] **Step 1: Add a failing unit test for `search_flights` storing `return_date` into `check_out`**

Add to `backend/tests/state/test_manager.py`:

```python
@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_stores_return_date_in_check_out(manager):
    args = {
        "origin": "서울",
        "destination": "오사카",
        "departure_date": "2026-07-01",
        "passengers": 1,
        "return_date": "2026-07-05",
    }

    events = [e async for e in manager.apply_tool_call("thread-return", "search_flights", args)]
    snap = events[0].snapshot

    assert snap["travel_context"]["check_in"] == "2026-07-01"
    assert snap["travel_context"]["check_out"] == "2026-07-05"
```

- [ ] **Step 2: Add a failing sidebar/context extraction test for the same behavior**

Update `backend/tests/state-panel-sidebar/test_context_extraction.py`:

```python
assert tc["check_out"] == "2026-07-05"
```

- [ ] **Step 3: Run only the new failing tests and confirm RED**

Run:

```bash
cd backend && uv run pytest tests/state/test_manager.py::test_apply_tool_call_search_flights_stores_return_date_in_check_out tests/state-panel-sidebar/test_context_extraction.py::test_apply_tool_call_search_flights_extracts_context -v
```

Expected: FAIL because `check_out` is currently unset for flight searches.

---

## Task 2: minimal production change for canonical state persistence

**Files:**
- Modify: `backend/state/manager.py`
- Test: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state-panel-sidebar/test_context_extraction.py`

- [ ] **Step 1: Update `search_flights` state extraction to persist `return_date`**

In `backend/state/manager.py`, inside the `tool_name == "search_flights"` branch, extend the `replace()` call so it also writes:

```python
check_out=args.get("return_date") or tc.check_out,
```

- [ ] **Step 2: Re-run the focused tests and confirm GREEN**

Run:

```bash
cd backend && uv run pytest tests/state/test_manager.py::test_apply_tool_call_search_flights_stores_return_date_in_check_out tests/state-panel-sidebar/test_context_extraction.py::test_apply_tool_call_search_flights_extracts_context -v
```

Expected: PASS

---

## Task 3: failing tests for request_user_input date prefill enrichment

**Files:**
- Modify: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state/test_manager.py`

- [ ] **Step 1: Add a failing test for hotel -> flight date prefill**

Append to `backend/tests/state/test_manager.py`:

```python
@pytest.mark.asyncio
async def test_apply_tool_result_request_user_input_prefills_flight_dates_from_state(manager):
    await anext(manager.apply_client_state("thread-prefill-flight", {
        "travel_context": {
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
        }
    }))

    result = {
        "status": "user_input_required",
        "input_type": "flight_booking_details",
        "fields": [
            {"name": "departure_date", "type": "date", "default": ""},
            {"name": "return_date", "type": "date", "default": ""},
        ],
    }

    events = [e async for e in manager.apply_tool_result("thread-prefill-flight", "request_user_input", result)]
    fields = {field["name"]: field for field in events[0].snapshot["fields"]}

    assert fields["departure_date"]["default"] == "2026-06-10"
    assert fields["return_date"]["default"] == "2026-06-14"
```

- [ ] **Step 2: Add a failing test for flight -> hotel date prefill**

```python
@pytest.mark.asyncio
async def test_apply_tool_result_request_user_input_prefills_hotel_dates_from_state(manager):
    await anext(manager.apply_client_state("thread-prefill-hotel", {
        "travel_context": {
            "check_in": "2026-07-01",
            "check_out": "2026-07-05",
        }
    }))

    result = {
        "status": "user_input_required",
        "input_type": "hotel_booking_details",
        "fields": [
            {"name": "check_in", "type": "date", "default": ""},
            {"name": "check_out", "type": "date", "default": ""},
        ],
    }

    events = [e async for e in manager.apply_tool_result("thread-prefill-hotel", "request_user_input", result)]
    fields = {field["name"]: field for field in events[0].snapshot["fields"]}

    assert fields["check_in"]["default"] == "2026-07-01"
    assert fields["check_out"]["default"] == "2026-07-05"
```

- [ ] **Step 3: Add a failing test proving existing defaults are not overwritten**

```python
@pytest.mark.asyncio
async def test_apply_tool_result_request_user_input_preserves_existing_date_defaults(manager):
    await anext(manager.apply_client_state("thread-preserve", {
        "travel_context": {
            "check_in": "2026-08-01",
            "check_out": "2026-08-05",
        }
    }))

    result = {
        "status": "user_input_required",
        "input_type": "flight_booking_details",
        "fields": [
            {"name": "departure_date", "type": "date", "default": "2026-09-01"},
            {"name": "return_date", "type": "date", "default": "2026-09-05"},
        ],
    }

    events = [e async for e in manager.apply_tool_result("thread-preserve", "request_user_input", result)]
    fields = {field["name"]: field for field in events[0].snapshot["fields"]}

    assert fields["departure_date"]["default"] == "2026-09-01"
    assert fields["return_date"]["default"] == "2026-09-05"
```

- [ ] **Step 4: Run the new tests and confirm RED**

Run:

```bash
cd backend && uv run pytest tests/state/test_manager.py -k "prefill or preserves_existing_date_defaults" -v
```

Expected: FAIL because `apply_tool_result()` currently forwards fields unchanged.

---

## Task 4: implement request_user_input prefill enrichment in StateManager

**Files:**
- Modify: `backend/state/manager.py`
- Test: `backend/tests/state/test_manager.py`

- [ ] **Step 1: Add a small helper that enriches date defaults from canonical state**

Inside `backend/state/manager.py`, add a focused helper such as:

```python
def _prefill_request_user_input_fields(
    self,
    input_type: str,
    fields: list[dict],
    state: TravelState,
) -> list[dict]:
    ...
```

Behavior:
- For `hotel_booking_details`, fill empty `check_in` / `check_out` defaults from `state.travel_context.check_in/check_out`
- For `flight_booking_details`, fill empty `departure_date` / `return_date` defaults from `state.travel_context.check_in/check_out`
- Do not overwrite non-empty defaults
- Return a new list to avoid mutating caller-owned data in place

- [ ] **Step 2: Use the helper inside `apply_tool_result()` for `request_user_input`**

Update the `user_input_request` snapshot branch so it emits enriched fields instead of raw `result.get("fields", [])`.

- [ ] **Step 3: Run the focused prefill tests and confirm GREEN**

Run:

```bash
cd backend && uv run pytest tests/state/test_manager.py -k "prefill or preserves_existing_date_defaults" -v
```

Expected: PASS

---

## Task 5: align prompt text and run regression suite

**Files:**
- Modify: `backend/agent.py` *(only if wording needs alignment)*
- Test: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state-panel-sidebar/test_context_extraction.py`

- [ ] **Step 1: If needed, minimally update `backend/agent.py` wording**

Keep this change documentation-only. Do not change unrelated prompt rules.

- [ ] **Step 2: Run targeted backend regression tests**

Run:

```bash
cd backend && uv run pytest tests/state/test_manager.py tests/state-panel-sidebar/test_context_extraction.py -v
```

Expected: PASS

- [ ] **Step 3: Run backend diagnostics/build-equivalent verification**

Run:

```bash
cd backend && uv run pytest -q
```

Expected: Full backend test suite passes, or only pre-existing unrelated failures remain.

---

## Task 6: final review and handoff

**Files:**
- Review: `backend/state/manager.py`
- Review: `backend/tests/state/test_manager.py`
- Review: `backend/tests/state-panel-sidebar/test_context_extraction.py`
- Review: `backend/agent.py`

- [ ] **Step 1: Diff review**

Check that the implementation is minimal and limited to:
- canonical flight return-date persistence
- request_user_input date default enrichment
- optional prompt wording alignment

- [ ] **Step 2: Capture verification notes**

Record:
- exact tests run
- whether defaults were preserved when already present
- whether empty-state fallback remained unchanged

- [ ] **Step 3: Hand off to execution mode**

Recommended execution approach: **Subagent-Driven** using `superpowers:subagent-driven-development`, because the work naturally splits into test-writing, minimal state-layer implementation, and verification.
