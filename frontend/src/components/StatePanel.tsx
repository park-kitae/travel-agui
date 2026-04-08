import { useEffect, useRef, useState } from 'react'
import { AgentState, UIContext } from '../types'

interface StatePanelProps {
  agentState: AgentState | null
  uiContext: UIContext
  isOpen: boolean
  onToggle: () => void
}

// 값이 변경될 때 하이라이트 key를 추적하는 훅
function useHighlight(value: unknown): boolean {
  const [highlighted, setHighlighted] = useState(false)
  const prevRef = useRef(value)

  useEffect(() => {
    const prev = prevRef.current
    prevRef.current = value
    if (prev !== undefined && JSON.stringify(prev) !== JSON.stringify(value)) {
      setHighlighted(true)
      const timer = setTimeout(() => setHighlighted(false), 1500)
      return () => clearTimeout(timer)
    }
  }, [value])

  return highlighted
}

interface FieldRowProps {
  label: string
  value: string | number | null | undefined
  highlightClass: string
}

function FieldRow({ label, value, highlightClass }: FieldRowProps) {
  const display = value !== null && value !== undefined ? String(value) : '-'
  const highlighted = useHighlight(value)
  return (
    <div className={`sp-field ${highlighted ? highlightClass : ''}`}>
      <span className="sp-field-label">{label}</span>
      <span className="sp-field-value">{display}</span>
    </div>
  )
}

interface ArrowHeaderProps {
  direction: '↑' | '↓'
  label: string
  pulsing: boolean
}

function ArrowHeader({ direction, label, pulsing }: ArrowHeaderProps) {
  return (
    <div className="sp-section-header">
      <span className={`sp-arrow ${pulsing ? 'sp-arrow-pulse' : ''}`}>{direction}</span>
      <span className="sp-section-label">{label}</span>
    </div>
  )
}

export function StatePanel({ agentState, uiContext, isOpen, onToggle }: StatePanelProps) {
  const tc = agentState?.travel_context
  const as = agentState?.agent_status

  // 서버→클라이언트 업데이트 pulse 감지
  const serverPulseRef = useRef(0)
  const [serverPulsing, setServerPulsing] = useState(false)
  useEffect(() => {
    if (!agentState) return
    const ts = agentState.last_updated
    if (ts !== serverPulseRef.current) {
      serverPulseRef.current = ts
      setServerPulsing(true)
      const t = setTimeout(() => setServerPulsing(false), 1000)
      return () => clearTimeout(t)
    }
  }, [agentState])

  // 클라이언트→서버 업데이트 pulse 감지
  const prevUiRef = useRef(uiContext)
  const [clientPulsing, setClientPulsing] = useState(false)
  useEffect(() => {
    if (JSON.stringify(prevUiRef.current) !== JSON.stringify(uiContext)) {
      prevUiRef.current = uiContext
      setClientPulsing(true)
      const t = setTimeout(() => setClientPulsing(false), 1000)
      return () => clearTimeout(t)
    }
  }, [uiContext])

  return (
    <>
      {/* 토글 버튼 (모바일/소형 화면) */}
      <button className="sp-toggle-btn" onClick={onToggle} title={isOpen ? '상태 패널 닫기' : '상태 패널 열기'}>
        {isOpen ? '⟩' : '⟨'} <span className="sp-toggle-label">State</span>
      </button>

      <aside className={`state-panel ${isOpen ? 'sp-open' : 'sp-closed'}`}>
        <div className="sp-header">
          <span className="sp-title">State Flow</span>
          <button className="sp-close-btn" onClick={onToggle}>✕</button>
        </div>

        {/* ── 1. 핵심 여행 정보 (절대 초기화 안 됨) ── */}
        <section className="sp-section">
          <div className="sp-section-header">
            <span className="sp-pin-icon">📌</span>
            <span className="sp-section-label">핵심 여행 정보</span>
            <span className="sp-badge sp-badge-stable">고정</span>
          </div>
          <div className="sp-fields">
            <FieldRow label="도착지" value={tc?.destination} highlightClass="sp-highlight-server" />
            <FieldRow label="출발지" value={tc?.origin} highlightClass="sp-highlight-server" />
            <FieldRow label="체크인" value={tc?.check_in} highlightClass="sp-highlight-server" />
            <FieldRow label="체크아웃" value={tc?.check_out} highlightClass="sp-highlight-server" />
            <FieldRow label="숙박 (박)" value={tc?.nights} highlightClass="sp-highlight-server" />
            <FieldRow label="인원 (명)" value={tc?.guests} highlightClass="sp-highlight-server" />
            <FieldRow label="여행 유형" value={tc?.trip_type} highlightClass="sp-highlight-server" />
          </div>
        </section>

        <div className="sp-divider" />

        {/* ── 2. 현재 선택 / 화면 상태 (변경 가능) ── */}
        <section className="sp-section">
          <ArrowHeader direction="↑" label="CLIENT → SERVER" pulsing={clientPulsing} />
          <div className="sp-fields">
            <FieldRow
              label="선택 호텔"
              value={uiContext.selected_hotel_code}
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="선택 항공편"
              value={uiContext.selected_flight_id}
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="현재 화면"
              value={uiContext.current_view}
              highlightClass="sp-highlight-client"
            />
            <FieldRow label="통화" value="KRW" highlightClass="sp-highlight-client" />
            <FieldRow label="언어" value="ko" highlightClass="sp-highlight-client" />
          </div>
        </section>

        <div className="sp-divider" />

        {/* ── 3. 에이전트 상태 (서버 응답) ── */}
        <section className="sp-section">
          <ArrowHeader direction="↓" label="SERVER → CLIENT" pulsing={serverPulsing} />
          <div className="sp-fields">
            <FieldRow label="인텐트" value={as?.current_intent} highlightClass="sp-highlight-server" />
            <FieldRow label="실행 도구" value={as?.active_tool} highlightClass="sp-highlight-server" />
            <FieldRow
              label="미입력 항목"
              value={as?.missing_fields?.length ? as.missing_fields.join(', ') : null}
              highlightClass="sp-highlight-server"
            />
          </div>
        </section>
      </aside>
    </>
  )
}
