# Graph Report - .  (2026-06-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 764 nodes · 1493 edges · 50 communities (41 shown, 9 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d1e63f25`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 46|Community 46]]

## God Nodes (most connected - your core abstractions)
1. `ContextBuilder` - 47 edges
2. `DomainRuntime` - 33 edges
3. `ADKAgentExecutor` - 31 edges
4. `TravelState` - 28 edges
5. `SerializedStateStore` - 28 edges
6. `TravelContext` - 24 edges
7. `UserPreferences` - 23 edges
8. `UIContext` - 22 edges
9. `TravelDomainPlugin` - 20 edges
10. `AgentStatus` - 16 edges

## Surprising Connections (you probably didn't know these)
- `State Panel Sidebar Tasks` --references--> `types/index.ts`  [EXTRACTED]
  openspec/changes/state-panel-sidebar/tasks.md → frontend/src/types/index.ts
- `SerializedStateStore` --uses--> `SerializedStateStore`  [INFERRED]
  backend/domain_runtime.py → backend/state/store.py
- `RuntimeEmission` --uses--> `SerializedStateStore`  [INFERRED]
  backend/domain_runtime.py → backend/state/store.py
- `_reset_runtime_and_modules()` --calls--> `reset_runtime_for_tests()`  [INFERRED]
  backend/tests/test_fake_plugin_smoke.py → backend/domain_runtime.py
- `State Panel Sidebar Design` --conceptually_related_to--> `Travel AGUI E2E 테스트 가이드`  [INFERRED]
  openspec/changes/state-panel-sidebar/design.md → frontend/tests/README.md

## Import Cycles
- None detected.

## Communities (50 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (64): TravelState, Any, TravelState, TravelState, Any, RuntimeEmission, ui_context 기반 컨텍스트 주입 테스트., user_preferences 기반 취향 주입 테스트. (+56 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (33): AgentExecutor, ADKAgentExecutor, _normalize_tool_result(), Any, executor.py — ADK Runner를 A2A AgentExecutor로 래핑, ADK Runner를 A2A AgentExecutor로 래핑합니다., _TextStreamState, DomainRuntime (+25 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (37): build_coordinator_instruction(), create_coordinator_agent(), Travel coordinator agent factory., 라우팅 중심의 간결한 코디네이터 instruction을 생성합니다., 여행 상담 코디네이터 에이전트를 생성합니다., create_flight_agent(), Flight domain sub-agent factory., 항공편 전담 서브 에이전트를 생성합니다. (+29 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (42): a2a_to_agui_stream(), converter.py — A2A 스트리밍 이벤트를 AG-UI SSE 이벤트로 변환, A2A 서버의 스트리밍 응답을 AG-UI SSE 이벤트로 변환합니다.      SendStreamingMessageResponse.root 는, _async_gen(), collect_stream(), execute_and_collect_stream(), make_data_artifact(), make_event_response() (+34 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (25): FavoritePanel(), Props, Props, UserInputForm(), cn(), SUGGESTIONS, FavoriteOptionDef, FavoriteRequest (+17 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (18): Any, MonkeyPatch, DomainPlugin, Fake domain package used to prove runtime swappability., AgentCapabilities, AgentCard, AgentSkill, FakeDomainPlugin (+10 more)

### Community 6 - "Community 6"
Cohesion: 0.24
Nodes (9): clearConversation(), gotoApp(), lastUserBubbleText(), selectors, sendUserMessage(), takeScreenshot(), waitForFlightResults(), waitForForm() (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (28): dependencies, lucide-react, @radix-ui/react-dialog, react, react-dom, devDependencies, playwright, @playwright/test (+20 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (10): _delta_by_path(), test_apply_tool_call_request_user_favorite_sets_awaiting_intent(), test_apply_tool_call_request_user_input_collecting_hotel_params(), test_apply_tool_call_request_user_input_parses_flight_context_json_string(), test_apply_tool_call_request_user_input_parses_hotel_context_json_string(), test_apply_tool_call_search_flights_updates_travel_context(), test_apply_tool_call_search_hotels_updates_travel_context(), test_merge_client_state_applies_falsey_present_preference_values() (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.17
Nodes (19): make_request_body(), make_runtime(), parse_sse_events(), /agui/run 엔드포인트 테스트 A2A 서버를 mock하여 실제 서버 없이 SSE 스트림 검증, messages가 빈 리스트이면 기본 메시지('안녕하세요')로 A2A 호출., A2A 서버 mock — RUN_STARTED / RUN_FINISHED 이벤트가 반드시 포함되어야 한다., A2A 서버 연결 실패 시 RUN_ERROR 이벤트가 포함되어야 한다., client_state는 A2A metadata로 전달되고 SSE에는 중복 없이 단일 agent_state만 노출된다. (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.14
Nodes (22): AGUIEvent, AGUIEventType, FAVORITE_TYPES, FavoriteType, HotelDetail, MessageRole, MessageStatus, RunErrorEvent (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (19): map_runtime_emission_to_payload(), RuntimeEmission, Convert typed runtime emissions into the current stream payload contract., Runtime emission for incremental state updates., Runtime emission for full state snapshots., Runtime emission for UI-driven requests., RuntimeDeltaPayload, RuntimeSnapshotPayload (+11 more)

### Community 12 - "Community 12"
Cohesion: 0.20
Nodes (9): DomainRuntime, get_runtime(), get_runtime_app_name(), Any, Resolve a stable app/session identity from runtime-backed objects., Owns the shared plugin and its opaque state store., DomainRuntime, InMemorySessionService (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (8): Any, RuntimeEmission, AgentCard, DomainPlugin, LlmAgent, Common domain contract for runtime plugins., Domain-specific plugin boundary for the shared chat runtime., Protocol

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (9): Props, Flight, FlightSearchResult, Hotel, HotelDetailResult, HotelSearchResult, RoomType, ToolResultSnapshot (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (13): applyJsonPatch(), applyOperation(), ClientStateEnvelope, cloneEnvelope(), DEFAULT_AGENT_STATUS, DEFAULT_TRAVEL_CONTEXT, DEFAULT_UI_CONTEXT, PERSISTENT_FIELDS (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.19
Nodes (14): useAgentState(), generateId(), handleEvent(), useAGUIChat(), useChatMessages(), App(), ClientState, DEFAULT_SESSION_PREFS (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (12): _load_plugin_from_env(), PreparedRequest, DomainPlugin, Singleton runtime for shared domain plugin execution., Runtime-prepared request payload for downstream transport., backend/domains/travel/agent.py, backend/domains/travel/context.py, backend/domains/travel/plugin.py (+4 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (9): Any, Store already-serialized plugin state without inspecting it., SerializedStateStore, AgentCard, LlmAgent, _StubAgent, _StubAgentCard, test_domain_runtime_exposes_startup_wrappers() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (10): a2a_server.py — ADK 에이전트를 A2A 프로토콜 서버로 래핑 (포트 8001)  흐름:   A2A Client (main.py), main.py — AG-UI ↔ A2A 클라이언트 미들웨어 서버 (포트 8000)  흐름:   React Client     → POST /ag, AG-UI 표준 엔드포인트.     RunAgentInput을 수신하고 A2A 서버로 전달한 뒤 AG-UI SSE 스트림으로 반환합니다., run_agent(), Travel AGUI E2E 테스트 가이드, State Panel Sidebar Proposal, Request, AG-UI Gateway Spec (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.33
Nodes (11): initialize_runtime_or_die(), reset_runtime_for_tests(), MonkeyPatch, teardown_function(), test_domain_plugin_is_importable_and_declares_required_methods(), test_domain_runtime_round_trips_opaque_state_with_plugin(), test_get_runtime_raises_before_initialization(), test_initialize_runtime_or_die_defaults_to_travel_when_env_missing() (+3 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (7): data/flights.py — 항공편 검색 정적 데이터, data/hotels.py — 호텔 검색 및 상세 정보 정적 데이터, Travel domain data exports., OptionDef, data/preferences.py — 사용자 취향 수집을 위한 고정 옵션 데이터, data/tips.py — 여행지 팁 정적 데이터, TypedDict

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (11): get_npm_cmd(), get_pids_on_port(), kill_pids(), kill_proc(), main(), cleanup(), tail -f 대체: 파일을 실시간 출력, npm 실행 명령 (Windows는 npm.cmd) (+3 more)

### Community 25 - "Community 25"
Cohesion: 0.42
Nodes (10): DomainRuntime, RuntimeEmission, _apply_tool_call(), _delta_by_path(), test_context_extraction.py — runtime plugin apply_tool_call이 컨텍스트 추출 결과를 올바르게 st, runtime(), test_apply_tool_call_partial_args(), test_apply_tool_call_request_user_input_hotel() (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.31
Nodes (3): Any, RuntimeEmission, StubPlugin

### Community 28 - "Community 28"
Cohesion: 0.27
Nodes (8): ChatMessageBubble(), Props, Props, TOOL_LABELS, ToolCallIndicator(), ToolResultCard(), ChatMessage, ToolCallInfo

### Community 29 - "Community 29"
Cohesion: 0.27
Nodes (8): FieldRow(), FieldRowProps, StatePanel(), StatePanelProps, TRAVEL_PURPOSE_LABEL, useHighlight(), AgentState, UIContext

### Community 30 - "Community 30"
Cohesion: 0.33
Nodes (6): models.py — 커스텀 AG-UI 이벤트 모델 정의, 사용자 취향 요청 이벤트 (AG-UI 확장)., 사용자 입력 요청 이벤트 (AG-UI 확장)., UserFavoriteRequestEvent, UserInputRequestEvent, BaseModel

### Community 31 - "Community 31"
Cohesion: 0.53
Nodes (4): AgentCapabilities, AgentCard, AgentSkill, test_a2a_server_uses_runtime_plugin_for_agent_and_agent_card()

### Community 32 - "Community 32"
Cohesion: 0.50
Nodes (3): Runtime-backed state handling tests for main.py., event_stream delegates request preparation to the runtime helper., test_runtime_merges_client_state_and_saves_for_thread()

## Knowledge Gaps
- **81 isolated node(s):** `LlmAgent`, `LlmAgent`, `LlmAgent`, `LlmAgent`, `Request` (+76 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State Panel Sidebar Proposal` connect `Community 20` to `Community 17`, `Community 4`, `Community 29`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `apply_tool_result()` connect `Community 0` to `Community 11`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `ADKAgentExecutor` connect `Community 1` to `Community 3`, `Community 12`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `ContextBuilder` (e.g. with `Any` and `TravelState`) actually correct?**
  _`ContextBuilder` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `DomainRuntime` (e.g. with `SerializedStateStore` and `ADKAgentExecutor`) actually correct?**
  _`DomainRuntime` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `ADKAgentExecutor` (e.g. with `DomainRuntime` and `DomainRuntime`) actually correct?**
  _`ADKAgentExecutor` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `TravelState` (e.g. with `TravelState` and `Any`) actually correct?**
  _`TravelState` has 18 INFERRED edges - model-reasoned connections that need verification._