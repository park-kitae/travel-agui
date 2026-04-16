import { useState, useCallback, useRef } from 'react'
import {
  ChatMessage,
  RunAgentInput,
  AGUIEvent,
  ToolSnapshot,
  AgentStateSnapshot,
  FavoriteRequest,
  ClientState,
  UserPreferences,
  DEFAULT_SESSION_PREFS,
  isAgentStateSnapshot,
  isUserInputRequestEvent,
  isUserFavoriteRequestEvent,
} from '../types'
import { useAgentState } from './useAgentState'
import { useChatMessages } from './useChatMessages'

const AGUI_ENDPOINT = '/agui/run'

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export function useAGUIChat() {
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const threadIdRef = useRef<string>(generateId())
  const abortRef = useRef<AbortController | null>(null)
  const isRunningRef = useRef(false)

  const {
    agentState,
    uiContext,
    pendingFavoriteRequest,
    applyAgentStateSnapshot,
    updateUiContext,
    updateUserPreferences,
    setPendingFavoriteRequest,
    resetAgentState,
  } = useAgentState()

  const { messages, addMessage, updateMessage, clearMessages } = useChatMessages()

  const sendMessage = useCallback(async (userText: string, extraPrefs?: Partial<UserPreferences>) => {
    if (isRunningRef.current || !userText.trim()) return
    setError(null)
    setIsRunning(true)
    isRunningRef.current = true

    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: userText.trim(),
      status: 'done',
      toolCalls: [],
      snapshots: [],
      timestamp: new Date(),
    }
    addMessage(userMsg)

    const assistantId = generateId()
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      status: 'streaming',
      toolCalls: [],
      snapshots: [],
      timestamp: new Date(),
    }
    addMessage(assistantMsg)

    const history = messages
      .filter(m => m.status === 'done')
      .map(m => ({ role: m.role, content: m.content }))
    history.push({ role: 'user', content: userText.trim() })

    const runId = generateId()
    // extraPrefs: submitFavorite에서 직접 전달 (React state 비동기 타이밍 우회)
    const mergedPrefs: UserPreferences = extraPrefs
      ? { ...agentState?.user_preferences, ...extraPrefs }
      : agentState?.user_preferences ?? {}
    const clientState: ClientState = {
      ui_context: uiContext,
      session_prefs: DEFAULT_SESSION_PREFS,
      travel_context: agentState?.travel_context ?? null,
      user_preferences: mergedPrefs,
    }
    const input: RunAgentInput = {
      threadId: threadIdRef.current,
      runId,
      state: clientState,
      messages: history,
      tools: [],
      context: [],
      forwardedProps: {},
    }

    const abort = new AbortController()
    abortRef.current = abort

    try {
      const res = await fetch(AGUI_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
        signal: abort.signal,
      })

      if (!res.ok || !res.body) {
        throw new Error(`서버 오류: ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const toolArgsBuffer: Record<string, string> = {}

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event: AGUIEvent
          try {
            event = JSON.parse(raw)
          } catch {
            continue
          }

          handleEvent(
            event,
            assistantId,
            toolArgsBuffer,
            updateMessage,
            applyAgentStateSnapshot,
            setPendingFavoriteRequest,
          )
        }
      }

      updateMessage(assistantId, m => ({ ...m, status: 'done', currentStep: undefined }))
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return
      const msg = err instanceof Error ? err.message : '알 수 없는 오류'
      setError(msg)
      updateMessage(assistantId, m => ({ ...m, status: 'error', content: m.content || msg }))
    } finally {
      setIsRunning(false)
      isRunningRef.current = false
    }
  }, [messages, agentState, uiContext, updateMessage, addMessage, applyAgentStateSnapshot, setPendingFavoriteRequest])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
    setIsRunning(false)
    isRunningRef.current = false
  }, [])

  const interruptAndSend = useCallback((userText: string) => {
    if (!userText.trim()) return
    abortRef.current?.abort()
    abortRef.current = null
    setIsRunning(false)
    isRunningRef.current = false
    setTimeout(() => sendMessage(userText), 0)
  }, [sendMessage])

  const clearAll = useCallback(() => {
    threadIdRef.current = generateId()
    clearMessages()
    setError(null)
    resetAgentState()
  }, [clearMessages, resetAgentState])

  const markFormSubmitted = useCallback((messageId: string) => {
    updateMessage(messageId, m => ({
      ...m,
      userInputRequest: m.userInputRequest
        ? { ...m.userInputRequest, submitted: true }
        : undefined,
    }))
  }, [updateMessage])

  const submitFavorite = useCallback((
    favoriteRequest: FavoriteRequest,
    selections: Record<string, string | string[]>
  ) => {
    // if 블록 밖에 선언해야 아래에서 참조 가능
    const prefPatch: Partial<UserPreferences> = {}
    Object.entries(selections).forEach(([key, value]) => {
      if (Array.isArray(value) ? value.length > 0 : Boolean(value)) {
        (prefPatch as Record<string, unknown>)[key] = value
      }
    })
    const hasSelections = Object.keys(prefPatch).length > 0

    if (hasSelections) {
      updateUserPreferences(prefPatch)
    }

    const marker = favoriteRequest.favoriteType === 'hotel_preference'
      ? '[호텔 취향 수집 완료]'
      : '[항공 취향 수집 완료]'

    let message: string
    if (!hasSelections) {
      message = `취향 없이 진행합니다 ${marker}`
    } else {
      const parts = Object.values(selections).flatMap(v =>
        Array.isArray(v) && v.length > 0 ? [v.join('·')] : typeof v === 'string' && v ? [v] : []
      )
      const serviceLabel = favoriteRequest.favoriteType === 'hotel_preference' ? '호텔' : '항공'
      message = `${serviceLabel} 취향: ${parts.join(', ')} ${marker}`
    }

    setPendingFavoriteRequest(null)

    // 스트리밍 중이면 먼저 인터럽트 후 전송 (취향 패널은 isRunning과 무관하게 제출 가능)
    if (isRunningRef.current) {
      abortRef.current?.abort()
      abortRef.current = null
      setIsRunning(false)
      isRunningRef.current = false
      setTimeout(() => sendMessage(message, hasSelections ? prefPatch : undefined), 0)
    } else {
      sendMessage(message, hasSelections ? prefPatch : undefined)
    }
  }, [sendMessage, setPendingFavoriteRequest, updateUserPreferences])

  return {
    messages,
    isRunning,
    error,
    agentState,
    uiContext,
    updateUiContext,
    sendMessage,
    interruptAndSend,
    stopStreaming,
    clearMessages: clearAll,
    markFormSubmitted,
    pendingFavoriteRequest,
    submitFavorite,
  }
}

// ─────────────────────────────────────────────
// AG-UI 이벤트 → 상태 업데이트 (순수 함수)
// ─────────────────────────────────────────────
function handleEvent(
  event: AGUIEvent,
  assistantId: string,
  toolArgsBuffer: Record<string, string>,
  updateMessage: (id: string, fn: (m: ChatMessage) => ChatMessage) => void,
  applyAgentStateSnapshot: (s: AgentStateSnapshot) => void,
  setPendingFavoriteRequest: (value: FavoriteRequest | null) => void,
) {
  switch (event.type) {
    case 'TEXT_MESSAGE_CHUNK': {
      const delta = event.delta as string
      if (!delta) break
      updateMessage(assistantId, m => ({ ...m, content: m.content + delta }))
      break
    }

    case 'TOOL_CALL_START': {
      const tc = {
        id: event.toolCallId as string,
        name: event.toolCallName as string,
        args: '',
        done: false,
      }
      updateMessage(assistantId, m => ({ ...m, toolCalls: [...m.toolCalls, tc] }))
      toolArgsBuffer[tc.id] = ''
      break
    }

    case 'TOOL_CALL_ARGS': {
      const tcId = event.toolCallId as string
      toolArgsBuffer[tcId] = (toolArgsBuffer[tcId] ?? '') + (event.delta as string)
      updateMessage(assistantId, m => ({
        ...m,
        toolCalls: m.toolCalls.map(tc =>
          tc.id === tcId ? { ...tc, args: toolArgsBuffer[tcId] } : tc
        ),
      }))
      break
    }

    case 'TOOL_CALL_END': {
      const tcId = event.toolCallId as string
      updateMessage(assistantId, m => ({
        ...m,
        toolCalls: m.toolCalls.map(tc =>
          tc.id === tcId ? { ...tc, done: true } : tc
        ),
      }))
      break
    }

    case 'STEP_STARTED':
      updateMessage(assistantId, m => ({ ...m, currentStep: event.stepName as string }))
      break

    case 'STEP_FINISHED':
      updateMessage(assistantId, m => ({ ...m, currentStep: undefined }))
      break

    case 'STATE_SNAPSHOT': {
      const snapshot = event.snapshot as ToolSnapshot
      if (isAgentStateSnapshot(snapshot)) {
        applyAgentStateSnapshot(snapshot)
      } else {
        updateMessage(assistantId, m => ({ ...m, snapshots: [...m.snapshots, snapshot] }))
      }
      break
    }

    case 'RUN_ERROR': {
      const errMsg = event.message as string
      updateMessage(assistantId, m => ({ ...m, status: 'error', content: m.content || errMsg }))
      break
    }

    case 'USER_INPUT_REQUEST': {
      if (!isUserInputRequestEvent(event)) break
      updateMessage(assistantId, m => ({
        ...m,
        userInputRequest: {
          requestId: event.requestId,
          inputType: event.inputType,
          fields: event.fields,
          submitted: false,
        },
      }))
      break
    }

    case 'USER_FAVORITE_REQUEST': {
      if (!isUserFavoriteRequestEvent(event)) break
      setPendingFavoriteRequest({
        requestId: event.requestId,
        favoriteType: event.favoriteType,
        options: event.options,
        submitted: false,
      })
      break
    }
  }
}
