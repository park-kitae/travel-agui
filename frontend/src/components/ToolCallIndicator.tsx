import { BedDouble, Check, LoaderCircle, LucideIcon, Plane, Search, Sparkles } from 'lucide-react'
import { ToolCallInfo } from '../types'

interface Props {
  toolCalls: ToolCallInfo[]
  currentStep?: string
}

const TOOL_LABELS: Record<string, { label: string; icon: LucideIcon }> = {
  search_hotels: { label: '호텔 검색 중', icon: BedDouble },
  search_flights: { label: '항공편 검색 중', icon: Plane },
  get_travel_tips: { label: '여행 정보 조회 중', icon: Sparkles },
}

export function ToolCallIndicator({ toolCalls, currentStep }: Props) {
  const activeCalls = toolCalls.filter(tc => !tc.done)
  const doneCalls = toolCalls.filter(tc => tc.done)

  if (toolCalls.length === 0 && !currentStep) return null

  return (
    <div className="tool-indicator">
      {doneCalls.map(tc => {
        const meta = TOOL_LABELS[tc.name]
        const Icon = meta?.icon ?? Search
        return (
          <div key={tc.id} className="tool-call-item done">
            <div className="tool-call-leading">
              <Icon size={16} />
            </div>
            <span className="tool-call-label">{meta?.label.replace(' 중', ' 완료') ?? tc.name}</span>
            <span className="tool-call-check"><Check size={14} /></span>
          </div>
        )
      })}

      {activeCalls.map(tc => {
        const meta = TOOL_LABELS[tc.name]
        const Icon = meta?.icon ?? Search
        let parsedArgs: Record<string, string> = {}
        try { parsedArgs = JSON.parse(tc.args || '{}') } catch {}

        return (
          <div key={tc.id} className="tool-call-item active">
            <div className="tool-call-leading">
              <Icon size={16} />
            </div>
            <div className="tool-call-body">
              <span className="tool-call-label">{meta?.label ?? tc.name}</span>
              {Object.keys(parsedArgs).length > 0 && (
                <span className="tool-call-args">
                  {Object.entries(parsedArgs).map(([k, v]) => `${k}: ${v}`).join(' · ')}
                </span>
              )}
            </div>
            <LoaderCircle size={16} className="tool-spinner-icon spin" />
          </div>
        )
      })}

      {currentStep && activeCalls.length === 0 && (
        <div className="tool-call-item active">
          <div className="tool-call-leading">
            <Search size={16} />
          </div>
          <span className="tool-call-label">{currentStep}</span>
          <LoaderCircle size={16} className="tool-spinner-icon spin" />
        </div>
      )}
    </div>
  )
}
