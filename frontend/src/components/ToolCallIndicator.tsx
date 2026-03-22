import { ToolCallInfo } from '../types'

interface Props {
  toolCalls: ToolCallInfo[]
  currentStep?: string
}

const TOOL_LABELS: Record<string, { label: string; icon: string }> = {
  search_hotels: { label: '호텔 검색 중', icon: '🏨' },
  search_flights: { label: '항공편 검색 중', icon: '✈️' },
  get_travel_tips: { label: '여행 정보 조회 중', icon: '🗺️' },
}

export function ToolCallIndicator({ toolCalls, currentStep }: Props) {
  const activeCalls = toolCalls.filter(tc => !tc.done)
  const doneCalls = toolCalls.filter(tc => tc.done)

  if (toolCalls.length === 0 && !currentStep) return null

  return (
    <div className="tool-indicator">
      {/* 완료된 툴콜 */}
      {doneCalls.map(tc => {
        const meta = TOOL_LABELS[tc.name]
        return (
          <div key={tc.id} className="tool-call-item done">
            <span className="tool-call-icon">{meta?.icon ?? '🔧'}</span>
            <span className="tool-call-label">{meta?.label.replace(' 중', ' 완료') ?? tc.name}</span>
            <span className="tool-call-check">✓</span>
          </div>
        )
      })}

      {/* 진행 중인 툴콜 */}
      {activeCalls.map(tc => {
        const meta = TOOL_LABELS[tc.name]
        let parsedArgs: Record<string, string> = {}
        try { parsedArgs = JSON.parse(tc.args || '{}') } catch {}

        return (
          <div key={tc.id} className="tool-call-item active">
            <span className="tool-call-icon">{meta?.icon ?? '🔧'}</span>
            <div className="tool-call-body">
              <span className="tool-call-label">{meta?.label ?? tc.name}</span>
              {Object.keys(parsedArgs).length > 0 && (
                <span className="tool-call-args">
                  {Object.entries(parsedArgs)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' · ')}
                </span>
              )}
            </div>
            <span className="tool-spinner" />
          </div>
        )
      })}

      {/* 현재 스텝 (툴콜 없이 스텝만 있을 때) */}
      {currentStep && activeCalls.length === 0 && (
        <div className="tool-call-item active">
          <span className="tool-call-icon">⚙️</span>
          <span className="tool-call-label">{currentStep}</span>
          <span className="tool-spinner" />
        </div>
      )}
    </div>
  )
}
