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

        {/* ── CLIENT → SERVER ───────────────── */}
        <section className="sp-section">
          <ArrowHeader direction="↑" label="CLIENT → SERVER" pulsing={clientPulsing} />
          <div className="sp-fields">
            <FieldRow
              label="selected_hotel"
              value={uiContext.selected_hotel_code}
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="selected_flight"
              value={uiContext.selected_flight_id}
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="current_view"
              value={uiContext.current_view}
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="currency"
              value="KRW"
              highlightClass="sp-highlight-client"
            />
            <FieldRow
              label="language"
              value="ko"
              highlightClass="sp-highlight-client"
            />
          </div>
        </section>

        <div className="sp-divider" />

        {/* ── SERVER → CLIENT ───────────────── */}
        <section className="sp-section">
          <ArrowHeader direction="↓" label="SERVER → CLIENT" pulsing={serverPulsing} />

          <div className="sp-subsection-title">Travel Context</div>
          <div className="sp-fields">
            <FieldRow label="destination" value={tc?.destination} highlightClass="sp-highlight-server" />
            <FieldRow label="origin" value={tc?.origin} highlightClass="sp-highlight-server" />
            <FieldRow label="check_in" value={tc?.check_in} highlightClass="sp-highlight-server" />
            <FieldRow label="check_out" value={tc?.check_out} highlightClass="sp-highlight-server" />
            <FieldRow label="nights" value={tc?.nights} highlightClass="sp-highlight-server" />
            <FieldRow label="guests" value={tc?.guests} highlightClass="sp-highlight-server" />
            <FieldRow label="trip_type" value={tc?.trip_type} highlightClass="sp-highlight-server" />
          </div>

          <div className="sp-subsection-title" style={{ marginTop: '12px' }}>Agent Status</div>
          <div className="sp-fields">
            <FieldRow label="intent" value={as?.current_intent} highlightClass="sp-highlight-server" />
            <FieldRow label="active_tool" value={as?.active_tool} highlightClass="sp-highlight-server" />
            <FieldRow
              label="missing_fields"
              value={as?.missing_fields?.length ? as.missing_fields.join(', ') : null}
              highlightClass="sp-highlight-server"
            />
          </div>
        </section>
      </aside>
    </>
  )
}
