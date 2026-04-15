import { useState, useCallback } from 'react'
import {
  AgentState,
  UIContext,
  FavoriteRequest,
  TravelContext,
  AgentStateSnapshot,
} from '../types'

const DEFAULT_UI_CONTEXT: UIContext = {
  selected_hotel_code: null,
  selected_flight_id: null,
  current_view: 'chat',
}

// 새 필드 추가 시 여기만 수정 — null로 덮어쓰지 않을 핵심 여행 정보
const PERSISTENT_FIELDS: ReadonlyArray<keyof TravelContext> = [
  'destination', 'check_in', 'check_out', 'nights', 'guests', 'origin', 'trip_type',
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

      return {
        travel_context: merged as unknown as TravelContext,
        agent_status: s.agent_status,
        last_updated: Date.now(),
        user_preferences: prev?.user_preferences ?? {},
      }
    })
  }, [])

  const updateUiContext = useCallback((patch: Partial<UIContext>) => {
    setUiContext(prev => ({ ...prev, ...patch }))
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
    updateUiContext,
    setPendingFavoriteRequest,
    resetAgentState,
  }
}
