import { useState, useCallback, useRef } from 'react'
import {
  ChatMessage,
  RunAgentInput,
  AGUIEvent,
  ToolSnapshot,
  FormField,
  AgentState,
  UIContext,
  ClientState,
  AgentStateSnapshot,
} from '../types'

const AGUI_ENDPOINT = '/agui/run'

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

const DEFAULT_UI_CONTEXT: UIContext = {
  selected_hotel_code: null,
  selected_flight_id: null,
  current_view: 'chat',
}

export function useAGUIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [agentState, setAgentState] = useState<AgentState | null>(null)
  const [uiContext, setUiContext] = useState<UIContext>(DEFAULT_UI_CONTEXT)
  const threadIdRef = useRef<string>(generateId())
  const abortRef = useRef<AbortController | null>(null)
  const isRunningRef = useRef(false)

  // 메시지 단건 업데이트 헬퍼
  const updateMessage = useCallback((id: string, updater: (m: ChatMessage) => ChatMessage) => {
    setMessages(prev => prev.map(m => m.id === id ? updater(m) : m))
  }, [])

  const sendMessage = useCallback(async (userText: string) => {
    if (isRunningRef.current || !userText.trim()) return
    setError(null)
    setIsRunning(true)
    isRunningRef.current = true

    // 1. 사용자 메시지 추가
    const userMsg: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: userText.trim(),
      status: 'done',
      toolCalls: [],
      snapshots: [],
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])

    // 2. 어시스턴트 메시지 placeholder
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
    setMessages(prev => [...prev, assistantMsg])

    // 3. history 구성 (현재 메시지 포함)
    const history = messages
      .filter(m => m.status === 'done')
      .map(m => ({ role: m.role, content: m.content }))
    history.push({ role: 'user', content: userText.trim() })

    // 4. RunAgentInput 구성 (uiContext + travel_context를 state에 포함)
    const runId = generateId()
    const clientState: ClientState = {
      ui_context: uiContext,
      session_prefs: { currency: 'KRW', language: 'ko' },
      travel_context: agentState?.travel_context ?? null,  // 호텔↔항공 날짜 재사용용
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
      // 진행 중인 tool call args 버퍼
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

          handleEvent(event, assistantId, toolArgsBuffer, updateMessage, setAgentState)
        }
      }

      // 스트림 종료 → done
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
  }, [messages, agentState, uiContext, updateMessage])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
    setIsRunning(false)
    isRunningRef.current = false
  }, [])

  // 현재 스트리밍 중단 후 즉시 새 메시지 전송 (호텔 클릭 등에서 사용)
  const interruptAndSend = useCallback((userText: string) => {
    if (!userText.trim()) return
    abortRef.current?.abort()
    abortRef.current = null
    setIsRunning(false)
    isRunningRef.current = false
    // 다음 이벤트 루프에서 sendMessage 호출 (상태 업데이트 후)
    setTimeout(() => sendMessage(userText), 0)
  }, [sendMessage])

  const clearMessages = useCallback(() => {
    threadIdRef.current = generateId()
    setMessages([])
    setError(null)
    setAgentState(null)
    setUiContext(DEFAULT_UI_CONTEXT)
  }, [])

  const updateUiContext = useCallback((patch: Partial<UIContext>) => {
    setUiContext(prev => ({ ...prev, ...patch }))
  }, [])

  const markFormSubmitted = useCallback((messageId: string) => {
    updateMessage(messageId, m => ({
      ...m,
      userInputRequest: m.userInputRequest
        ? { ...m.userInputRequest, submitted: true }
        : undefined,
    }))
  }, [updateMessage])

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
    clearMessages,
    markFormSubmitted,
  }
}

// ─────────────────────────────────────────────
// AG-UI 이벤트 → 상태 업데이트
// ─────────────────────────────────────────────
function handleEvent(
  event: AGUIEvent,
  assistantId: string,
  toolArgsBuffer: Record<string, string>,
  updateMessage: (id: string, fn: (m: ChatMessage) => ChatMessage) => void,
  setAgentState: (fn: (prev: AgentState | null) => AgentState) => void,
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
      updateMessage(assistantId, m => ({
        ...m,
        toolCalls: [...m.toolCalls, tc],
      }))
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

    case 'STEP_STARTED': {
      const step = event.stepName as string
      updateMessage(assistantId, m => ({ ...m, currentStep: step }))
      break
    }

    case 'STEP_FINISHED': {
      updateMessage(assistantId, m => ({ ...m, currentStep: undefined }))
      break
    }

    case 'STATE_SNAPSHOT': {
      const snapshot = event.snapshot as ToolSnapshot
      if ((snapshot as AgentStateSnapshot).snapshot_type === 'agent_state') {
        const s = snapshot as AgentStateSnapshot
        // 도착지·날짜·인원 등 핵심 여행 정보는 null로 덮어쓰지 않음
        const PERSISTENT_FIELDS: (keyof typeof s.travel_context)[] = [
          'destination', 'check_in', 'check_out', 'nights', 'guests', 'origin', 'trip_type',
        ]
        setAgentState(prev => {
          const prevTc = prev?.travel_context ?? {} as Partial<AgentState['travel_context']>
          const merged = { ...prevTc } as Record<string, unknown>
          for (const [key, value] of Object.entries(s.travel_context)) {
            const isPersistent = PERSISTENT_FIELDS.includes(key as keyof typeof s.travel_context)
            if (isPersistent && value === null && prevTc[key as keyof typeof prevTc] != null) {
              // 이미 값이 있는 핵심 필드는 null로 초기화하지 않음
              continue
            }
            merged[key] = value
          }
          return {
            travel_context: merged as AgentState['travel_context'],
            agent_status: s.agent_status,
            last_updated: Date.now(),
          }
        })
      } else {
        // tool_result 또는 기존 구조 → 메시지 snapshots에 추가
        updateMessage(assistantId, m => ({
          ...m,
          snapshots: [...m.snapshots, snapshot],
        }))
      }
      break
    }

    case 'RUN_ERROR': {
      const errMsg = event.message as string
      updateMessage(assistantId, m => ({
        ...m,
        status: 'error',
        content: m.content || errMsg,
      }))
      break
    }

    case 'USER_INPUT_REQUEST': {
      const requestId = event.requestId as string
      const inputType = event.inputType as string
      const fields = event.fields as FormField[]
      updateMessage(assistantId, m => ({
        ...m,
        userInputRequest: {
          requestId,
          inputType,
          fields,
          submitted: false,
        },
      }))
      break
    }
  }
}
