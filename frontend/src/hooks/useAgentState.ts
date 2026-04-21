import { useState, useCallback } from 'react'
import {
  AgentState,
  UIContext,
  FavoriteRequest,
  TravelContext,
  AgentStateSnapshot,
  AgentStatus,
  JsonPatchOperation,
  UserPreferences,
} from '../types'

const DEFAULT_UI_CONTEXT: UIContext = {
  selected_hotel_code: null,
  selected_flight_id: null,
  current_view: 'chat',
}

const DEFAULT_TRAVEL_CONTEXT: TravelContext = {
  destination: null,
  origin: null,
  check_in: null,
  check_out: null,
  nights: null,
  guests: null,
  rooms: null,
  trip_type: null,
  budget_range: null,
  travel_purpose: null,
}

const DEFAULT_AGENT_STATUS: AgentStatus = {
  current_intent: 'idle',
  missing_fields: [],
  active_tool: null,
}

interface ClientStateEnvelope {
  travel_context: TravelContext
  ui_context: UIContext
  agent_status: AgentStatus
  user_preferences: UserPreferences
}

function decodePointerToken(token: string): string {
  return token.replace(/~1/g, '/').replace(/~0/g, '~')
}

function cloneEnvelope(state: ClientStateEnvelope): ClientStateEnvelope {
  return JSON.parse(JSON.stringify(state)) as ClientStateEnvelope
}

function buildEnvelope(agentState: AgentState | null, uiContext: UIContext): ClientStateEnvelope {
  return {
    travel_context: agentState?.travel_context ?? DEFAULT_TRAVEL_CONTEXT,
    ui_context: uiContext,
    agent_status: agentState?.agent_status ?? DEFAULT_AGENT_STATUS,
    user_preferences: agentState?.user_preferences ?? {},
  }
}

function applyOperation(target: Record<string, unknown> | unknown[], operation: JsonPatchOperation): void {
  const tokens = operation.path
    .split('/')
    .slice(1)
    .map(decodePointerToken)

  if (tokens.length === 0) {
    return
  }

  let cursor: Record<string, unknown> | unknown[] = target
  for (const token of tokens.slice(0, -1)) {
    const next = Array.isArray(cursor) ? cursor[Number(token)] : cursor[token]
    if (next && typeof next === 'object') {
      cursor = next as Record<string, unknown> | unknown[]
    } else {
      return
    }
  }

  const lastToken = tokens[tokens.length - 1]
  if (Array.isArray(cursor)) {
    const index = Number(lastToken)
    if (Number.isNaN(index)) {
      return
    }

    if (operation.op === 'remove') {
      cursor.splice(index, 1)
      return
    }

    cursor[index] = operation.value
    return
  }

  if (operation.op === 'remove') {
    delete cursor[lastToken]
    return
  }

  cursor[lastToken] = operation.value ?? null
}

function applyJsonPatch(baseState: ClientStateEnvelope, operations: JsonPatchOperation[]): ClientStateEnvelope {
  const nextState = cloneEnvelope(baseState)
  for (const operation of operations) {
    applyOperation(nextState as unknown as Record<string, unknown>, operation)
  }
  return nextState
}

// 새 필드 추가 시 여기만 수정 — null로 덮어쓰지 않을 핵심 여행 정보
const PERSISTENT_FIELDS: ReadonlyArray<keyof TravelContext> = [
  'destination', 'check_in', 'check_out', 'nights', 'guests', 'rooms',
  'origin', 'trip_type', 'budget_range', 'travel_purpose',
]

export function useAgentState() {
  const [agentState, setAgentState] = useState<AgentState | null>(null)
  const [uiContext, setUiContext] = useState<UIContext>(DEFAULT_UI_CONTEXT)
  const [pendingFavoriteRequest, setPendingFavoriteRequest] = useState<FavoriteRequest | null>(null)

  // AgentStateSnapshot을 받아 agentState를 병합 업데이트
  // PERSISTENT_FIELDS에 있는 필드는 기존 값이 있으면 null로 초기화하지 않음
  const applyAgentStateSnapshot = useCallback((s: AgentStateSnapshot) => {
    setAgentState(prev => {
      const prevTc = prev?.travel_context ?? ({} as Partial<TravelContext>)
      const merged: Record<string, unknown> = { ...prevTc }

      for (const [key, value] of Object.entries(s.travel_context)) {
        const isPersistent = PERSISTENT_FIELDS.includes(key as keyof TravelContext)
        if (isPersistent && value === null && prevTc[key as keyof TravelContext] != null) {
          continue
        }
        merged[key] = value
      }

      // user_preferences: 스냅샷에 있으면 병합, 없으면 기존 값 유지
      const mergedPrefs: UserPreferences = s.user_preferences
        ? { ...prev?.user_preferences, ...s.user_preferences }
        : prev?.user_preferences ?? {}

      return {
        travel_context: merged as unknown as TravelContext,
        agent_status: s.agent_status,
        last_updated: Date.now(),
        user_preferences: mergedPrefs,
      }
    })
  }, [])

  const applyAgentStateDelta = useCallback((delta: JsonPatchOperation[]) => {
    if (delta.length === 0) {
      return
    }

    setAgentState(prev => {
      const baseState = buildEnvelope(prev, uiContext)
      const nextState = applyJsonPatch(baseState, delta)

      setUiContext(nextState.ui_context)

      return {
        travel_context: nextState.travel_context,
        agent_status: nextState.agent_status,
        last_updated: Date.now(),
        user_preferences: nextState.user_preferences,
      }
    })
  }, [uiContext])

  const updateUiContext = useCallback((patch: Partial<UIContext>) => {
    setUiContext(prev => ({ ...prev, ...patch }))
  }, [])

  const updateUserPreferences = useCallback((patch: Partial<UserPreferences>) => {
    setAgentState(prev => {
      const base = prev ?? {
        travel_context: {} as TravelContext,
        agent_status: { current_intent: 'idle' as const, missing_fields: [], active_tool: null },
        last_updated: Date.now(),
        user_preferences: {},
      }
      return {
        ...base,
        user_preferences: { ...base.user_preferences, ...patch },
        last_updated: Date.now(),
      }
    })
  }, [])

  const resetAgentState = useCallback(() => {
    setAgentState(null)
    setUiContext(DEFAULT_UI_CONTEXT)
    setPendingFavoriteRequest(null)
  }, [])

  return {
    agentState,
    uiContext,
    pendingFavoriteRequest,
    applyAgentStateSnapshot,
    applyAgentStateDelta,
    updateUiContext,
    updateUserPreferences,
    setPendingFavoriteRequest,
    resetAgentState,
  }
}
