import { ReactNode, useEffect, useRef, useState } from 'react'
import { AgentState, UIContext, UserPreferences } from '../types'

interface StatePanelProps {
  agentState: AgentState | null
  uiContext: UIContext
}

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

function SectionHeader({
  label,
  direction,
  pulsing,
  badge,
}: {
  label: string
  direction?: '↑' | '↓'
  pulsing?: boolean
  badge?: ReactNode
}) {
  return (
    <div className="sp-section-header">
      {direction ? <span className={`sp-arrow ${pulsing ? 'sp-arrow-pulse' : ''}`}>{direction}</span> : null}
      <span className="sp-section-label">{label}</span>
      {badge}
    </div>
  )
}

const TRAVEL_PURPOSE_LABEL: Record<string, string> = {
  leisure: '여가/관광',
  business: '비즈니스',
  honeymoon: '허니문',
  family: '가족 여행',
}

export function StatePanel({ agentState, uiContext }: StatePanelProps) {
  const tc = agentState?.travel_context
  const as = agentState?.agent_status
  const pref: UserPreferences | undefined = agentState?.user_preferences

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
    <div className="state-panel sp-open">
      <section className="sp-section">
        <SectionHeader
          label="핵심 여행 정보"
          badge={<span className="sp-badge sp-badge-stable">고정</span>}
        />
        <div className="sp-fields">
          <FieldRow label="도착지" value={tc?.destination} highlightClass="sp-highlight-server" />
          <FieldRow label="출발지" value={tc?.origin} highlightClass="sp-highlight-server" />
          <FieldRow label="체크인" value={tc?.check_in} highlightClass="sp-highlight-server" />
          <FieldRow label="체크아웃" value={tc?.check_out} highlightClass="sp-highlight-server" />
          <FieldRow label="숙박 (박)" value={tc?.nights} highlightClass="sp-highlight-server" />
          <FieldRow label="인원 (명)" value={tc?.guests} highlightClass="sp-highlight-server" />
          <FieldRow label="객실 수" value={tc?.rooms} highlightClass="sp-highlight-server" />
          <FieldRow label="여행 유형" value={tc?.trip_type} highlightClass="sp-highlight-server" />
          <FieldRow label="예산 수준" value={tc?.budget_range} highlightClass="sp-highlight-server" />
          <FieldRow
            label="여행 목적"
            value={tc?.travel_purpose ? (TRAVEL_PURPOSE_LABEL[tc.travel_purpose] ?? tc.travel_purpose) : null}
            highlightClass="sp-highlight-server"
          />
        </div>
      </section>

      <div className="sp-divider" />

      <section className="sp-section">
        <SectionHeader label="CLIENT → SERVER" direction="↑" pulsing={clientPulsing} />
        <div className="sp-fields">
          <FieldRow label="선택 호텔" value={uiContext.selected_hotel_code} highlightClass="sp-highlight-client" />
          <FieldRow label="선택 항공편" value={uiContext.selected_flight_id} highlightClass="sp-highlight-client" />
          <FieldRow label="현재 화면" value={uiContext.current_view} highlightClass="sp-highlight-client" />
          <FieldRow label="통화" value="KRW" highlightClass="sp-highlight-client" />
          <FieldRow label="언어" value="ko" highlightClass="sp-highlight-client" />
        </div>
      </section>

      <div className="sp-divider" />

      <section className="sp-section">
        <SectionHeader label="SERVER → CLIENT" direction="↓" pulsing={serverPulsing} />
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

      <div className="sp-divider" />

      <section className="sp-section">
        <SectionHeader
          label="사용자 취향"
          badge={
            <div className="sp-badge-group">
              <span className={`sp-badge ${(pref?.hotel_grade || pref?.hotel_type) ? 'sp-badge-done' : 'sp-badge-pending'}`}>
                호텔 {(pref?.hotel_grade || pref?.hotel_type) ? '✓' : '미수집'}
              </span>
              <span className={`sp-badge ${(pref?.seat_class || pref?.seat_position) ? 'sp-badge-done' : 'sp-badge-pending'}`}>
                항공 {(pref?.seat_class || pref?.seat_position) ? '✓' : '미수집'}
              </span>
            </div>
          }
        />
        <div className="sp-fields">
          <FieldRow label="호텔 등급" value={pref?.hotel_grade} highlightClass="sp-highlight-server" />
          <FieldRow label="호텔 유형" value={pref?.hotel_type} highlightClass="sp-highlight-server" />
          <FieldRow
            label="편의시설"
            value={pref?.amenities?.length ? pref.amenities.join(', ') : null}
            highlightClass="sp-highlight-server"
          />
          <FieldRow label="좌석 등급" value={pref?.seat_class} highlightClass="sp-highlight-server" />
          <FieldRow label="좌석 위치" value={pref?.seat_position} highlightClass="sp-highlight-server" />
          <FieldRow label="기내식" value={pref?.meal_preference} highlightClass="sp-highlight-server" />
          <FieldRow
            label="선호 항공사"
            value={pref?.airline_preference?.length ? pref.airline_preference.join(', ') : null}
            highlightClass="sp-highlight-server"
          />
        </div>
      </section>
    </div>
  )
}
