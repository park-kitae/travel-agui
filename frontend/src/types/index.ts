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

// 도구 결과 스냅샷
export interface ToolSnapshot {
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
  state: Record<string, unknown>
  messages: Array<{ role: string; content: string }>
  tools: unknown[]
  context: unknown[]
  forwardedProps: Record<string, unknown>
}
