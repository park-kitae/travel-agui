## Backend Tests

**경로**: `backend/tests/state-panel-sidebar/`

**실행 명령어**:
```bash
cd backend
uv run pytest tests/state-panel-sidebar/ -v
```

### 1. agent_state STATE_SNAPSHOT 발행 (a2a_server.py)

- [x] `test_context_extraction.py` — 컨텍스트 추출 로직 검증 완료
- [x] `test_snapshot_emission.py` — agent_state STATE_SNAPSHOT 발행 순서 및 구조 검증 완료
- [ ] `test_agent_state_snapshot_on_hotel_search.py` — search_hotels 호출 전 agent_state STATE_SNAPSHOT 발행 확인
- [ ] `test_agent_state_snapshot_on_flight_search.py` — search_flights 호출 전 origin, destination, trip_type 포함 확인
- [ ] `test_agent_state_snapshot_on_user_input_request.py` — request_user_input 호출 시 missing_fields 포함 확인
- [ ] `test_agent_state_snapshot_partial_context.py` — 목적지만 파악된 경우 나머지 필드 null 확인
- [ ] `test_tool_result_snapshot_type_field.py` — 기존 tool result STATE_SNAPSHOT에 `snapshot_type: "tool_result"` 포함 확인

### 2. RunAgentInput.state 처리 (main.py)

- [x] `test_main_state_handling.py` — state 필드 추출 및 전달 로직 검증 완료
- [ ] `test_run_agent_input_state_missing.py` — state 필드 없을 때 오류 없이 처리 확인
- [ ] `test_run_agent_input_state_empty_dict.py` — state가 빈 dict일 때 graceful 처리 확인

---

## Frontend Tests

**경로**: `frontend/tests/e2e/state-panel-sidebar/`

**실행 명령어**:
```bash
cd frontend
npx playwright test tests/e2e/state-panel-sidebar/ --reporter=list
```

### 3. StatePanel 렌더링

- [x] `state-panel-basic.spec.ts` — 초기 로드 시 StatePanel이 우측에 표시되고 모든 필드가 "-"로 초기화 확인
- [ ] `state-panel-sections.spec.ts` — "↑ CLIENT → SERVER"와 "↓ SERVER → CLIENT" 섹션 헤더 표시 확인

### 4. 서버→클라이언트 상태 표시

- [x] `state-panel-updates.spec.ts` — 에이전트로부터 agent_state 수신 시 travel_context 업데이트 및 하이라이트 확인
- [ ] `state-panel-agent-status-update.spec.ts` — current_intent, missing_fields, active_tool 필드 업데이트 확인
- [ ] `state-panel-server-highlight.spec.ts` — 서버 상태 업데이트 시 녹색 하이라이트 1.5초 표시 확인

### 5. 클라이언트→서버 상태 표시

- [x] `state-panel-updates.spec.ts` — 호텔 카드 클릭 시 selected_hotel_code 업데이트 및 하이라이트 확인
- [ ] `state-panel-current-view-update.spec.ts` — 호텔 상세 뷰 진입 시 current_view: "hotel_detail" 표시 확인
- [ ] `state-panel-client-highlight.spec.ts` — 클라이언트 상태 변경 시 파란색 하이라이트 1.5초 표시 확인

### 6. RunAgentInput.state 전송 검증

- [x] `state-panel-updates.spec.ts` — 메시지 전송 시 state 필드 포함 및 selected_hotel_code 연동 확인
- [ ] `run-agent-input-state-included.spec.ts` — 메시지 전송 시 네트워크 요청에 state 필드 포함 확인 (Playwright network intercept 활용)
- [ ] `run-agent-input-state-hotel-selected.spec.ts` — 호텔 선택 후 메시지 전송 시 selected_hotel_code가 state에 포함 확인

### 7. 반응형 동작

- [x] `state-panel-basic.spec.ts` — 1024px 미만 뷰포트에서 StatePanel 기본 숨김 및 토글 확인
- [ ] `state-panel-mobile-hidden.spec.ts` — 1024px 미만 뷰포트에서 StatePanel 기본 숨김 확인
- [ ] `state-panel-toggle.spec.ts` — 토글 버튼 클릭 시 StatePanel 슬라이드 표시/숨김 확인
- [ ] `state-panel-desktop-visible.spec.ts` — 1024px 이상 뷰포트에서 StatePanel 항상 표시 확인

### 8. 방향 표시 애니메이션

- [ ] `state-panel-arrow-pulse.spec.ts` — 상태 업데이트 시 해당 방향 화살표 pulse 애니메이션 1초간 적용 확인
