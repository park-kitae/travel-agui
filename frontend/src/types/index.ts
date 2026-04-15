// AG-UI 이벤트 타입 정의
export type AGUIEventType =
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  | 'STEP_STARTED'
  | 'STEP_FINISHED'
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CHUNK'
  | 'TEXT_MESSAGE_END'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  | 'STATE_SNAPSHOT'
  | 'USER_INPUT_REQUEST'
  | 'USER_FAVORITE_REQUEST'

export interface AGUIEvent {
  type: AGUIEventType
  [key: string]: unknown
}

export interface RunStartedEvent extends AGUIEvent {
  type: 'RUN_STARTED'
  runId: string
  threadId: string
}

export interface TextMessageStartEvent extends AGUIEvent {
  type: 'TEXT_MESSAGE_START'
  messageId: string
  role: 'assistant'
}

export interface TextMessageChunkEvent extends AGUIEvent {
  type: 'TEXT_MESSAGE_CHUNK'
  messageId: string
  delta: string
}

export interface TextMessageEndEvent extends AGUIEvent {
  type: 'TEXT_MESSAGE_END'
  messageId: string
}

export interface ToolCallStartEvent extends AGUIEvent {
  type: 'TOOL_CALL_START'
  toolCallId: string
  toolCallName: string
  parentMessageId?: string
}

export interface ToolCallArgsEvent extends AGUIEvent {
  type: 'TOOL_CALL_ARGS'
  toolCallId: string
  delta: string
}

export interface ToolCallEndEvent extends AGUIEvent {
  type: 'TOOL_CALL_END'
  toolCallId: string
}

export interface StepStartedEvent extends AGUIEvent {
  type: 'STEP_STARTED'
  stepName: string
}

export interface StateSnapshotEvent extends AGUIEvent {
  type: 'STATE_SNAPSHOT'
  snapshot: ToolSnapshot
}

export interface RunErrorEvent extends AGUIEvent {
  type: 'RUN_ERROR'
  message: string
  code?: string
}

export interface UserInputRequestEvent extends AGUIEvent {
  type: 'USER_INPUT_REQUEST'
  requestId: string
  inputType: string
  fields: FormField[]
}

// 취향 옵션 정의
export interface FavoriteOptionDef {
  type: 'radio' | 'checkbox'
  label: string
  choices: string[]
}

// 취향 타입 — 단일 정의 (여러 곳에 union 반복 방지)
export const FAVORITE_TYPES = ['hotel_preference', 'flight_preference'] as const
export type FavoriteType = typeof FAVORITE_TYPES[number]

// 취향 요청 이벤트
export interface UserFavoriteRequestEvent extends AGUIEvent {
  type: 'USER_FAVORITE_REQUEST'
  requestId: string
  favoriteType: FavoriteType
  options: Record<string, FavoriteOptionDef>
}

// 취향 요청 상태 (훅에서 관리)
export interface FavoriteRequest {
  requestId: string
  favoriteType: FavoriteType
  options: Record<string, FavoriteOptionDef>
  submitted: boolean
}

// 사용자 취향 (AgentState 일부)
export interface UserPreferences {
  hotel_grade?: string
  hotel_type?: string
  amenities?: string[]
  seat_class?: string
  seat_position?: string
  meal_preference?: string
  airline_preference?: string[]
}

// 폼 필드 정의
export interface FormField {
  name: string
  type: 'text' | 'date' | 'number' | 'select'
  label: string
  required: boolean
  placeholder?: string
  options?: string[]
  min?: number
  max?: number
  default?: string  // 기본값
}

// ── 양방향 상태 동기화 타입 ───────────────────────

export interface TravelContext {
  destination: string | null
  origin: string | null
  check_in: string | null
  check_out: string | null
  nights: number | null
  guests: number | null
  trip_type: 'round_trip' | 'one_way' | null
}

export interface AgentStatus {
  current_intent: 'collecting_hotel_params' | 'collecting_flight_params' | 'searching' | 'presenting_results' | 'awaiting_input' | 'idle'
  missing_fields: string[]
  active_tool: string | null
}

export interface AgentState {
  travel_context: TravelContext
  agent_status: AgentStatus
  last_updated: number
  user_preferences: UserPreferences
}

export interface UIContext {
  selected_hotel_code: string | null
  selected_flight_id: string | null
  current_view: 'chat' | 'hotel_list' | 'hotel_detail' | 'flight_list'
}

export interface SessionPrefs {
  currency: 'KRW' | 'USD' | 'JPY'
  language: 'ko' | 'en' | 'ja'
}

export interface ClientState {
  ui_context: UIContext
  session_prefs: SessionPrefs
  travel_context?: Partial<TravelContext> | null  // 누적된 여행 컨텍스트 (호텔↔항공 날짜 재사용)
}

// 도구 결과 스냅샷
export interface ToolResultSnapshot {
  snapshot_type: 'tool_result'
  tool: string
  result: HotelSearchResult | FlightSearchResult | TravelTipsResult | HotelDetailResult | Record<string, unknown>
}

export interface AgentStateSnapshot {
  snapshot_type: 'agent_state'
  travel_context: TravelContext
  agent_status: AgentStatus
}

// 하위 호환: snapshot_type 없는 기존 구조 포함
export type ToolSnapshot = ToolResultSnapshot | AgentStateSnapshot | {
  snapshot_type?: undefined
  tool: string
  result: HotelSearchResult | FlightSearchResult | TravelTipsResult | HotelDetailResult | Record<string, unknown>
}

export interface Hotel {
  hotel_code: string
  name: string
  area: string
  price: number
  rating: number
  stars: number
  city: string
  check_in: string
  check_out: string
  guests: number
}

export interface RoomType {
  type: string
  size: string
  price_per_night: number
  max_guests: number
  bed: string
}

export interface HotelDetail {
  hotel_code: string
  name: string
  city: string
  area: string
  stars: number
  rating: number
  address: string
  phone: string
  description: string
  amenities: string[]
  room_types: RoomType[]
  check_in_time: string
  check_out_time: string
  cancel_policy: string
  highlights: string[]
}

export interface HotelDetailResult {
  status: string
  hotel_code?: string
  name?: string
  city?: string
  area?: string
  stars?: number
  rating?: number
  address?: string
  phone?: string
  description?: string
  amenities?: string[]
  room_types?: RoomType[]
  check_in_time?: string
  check_out_time?: string
  cancel_policy?: string
  highlights?: string[]
  message?: string
}

export interface HotelSearchResult {
  status: string
  city?: string
  check_in?: string
  check_out?: string
  guests?: number
  count?: number
  hotels?: Hotel[]
  message?: string
}

export interface Flight {
  airline: string
  flight: string
  depart: string
  arrive: string
  duration: string
  price: number
  class: string
  departure_date: string
  passengers: number
  total_price: number
}

export interface FlightSearchResult {
  status: string
  origin?: string
  destination?: string
  departure_date?: string
  return_date?: string
  passengers?: number
  trip_type?: string
  // 편도
  count?: number
  flights?: Flight[]
  // 왕복
  outbound_count?: number
  inbound_count?: number
  outbound_flights?: Flight[]
  inbound_flights?: Flight[]
  message?: string
}

export interface TravelTipsResult {
  status: string
  destination?: string
  overview?: string
  best_season?: string
  currency?: string
  language?: string
  spots?: string[]
  food?: string[]
  tips?: string[]
  message?: string
}

// 채팅 메시지
export type MessageRole = 'user' | 'assistant'
export type MessageStatus = 'streaming' | 'done' | 'error'

export interface ToolCallInfo {
  id: string
  name: string
  args: string
  done: boolean
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  status: MessageStatus
  toolCalls: ToolCallInfo[]
  snapshots: ToolSnapshot[]
  timestamp: Date
  currentStep?: string
  userInputRequest?: UserInputRequest
}

// 사용자 입력 요청 상태
export interface UserInputRequest {
  requestId: string
  inputType: string
  fields: FormField[]
  submitted: boolean
}

// AG-UI RunAgentInput
export interface RunAgentInput {
  threadId: string
  runId: string
  state: ClientState | Record<string, unknown>
  messages: Array<{ role: string; content: string }>
  tools: unknown[]
  context: unknown[]
  forwardedProps: Record<string, unknown>
}

// ── 이벤트 타입가드 (as 캐스팅 대신 사용) ────────────────
export function isUserInputRequestEvent(e: AGUIEvent): e is UserInputRequestEvent {
  return e.type === 'USER_INPUT_REQUEST'
}

export function isUserFavoriteRequestEvent(e: AGUIEvent): e is UserFavoriteRequestEvent {
  return e.type === 'USER_FAVORITE_REQUEST'
}

export function isAgentStateSnapshot(s: ToolSnapshot): s is AgentStateSnapshot {
  return (s as AgentStateSnapshot).snapshot_type === 'agent_state'
}

// session_prefs 기본값 (sendMessage 내부 하드코딩 방지)
export const DEFAULT_SESSION_PREFS: SessionPrefs = {
  currency: 'KRW',
  language: 'ko',
}
