import { useState } from 'react'
import { FavoriteRequest, FavoriteOptionDef } from '../types'

interface Props {
  request: FavoriteRequest
  onSubmit: (favoriteType: 'hotel_preference' | 'flight_preference', selections: Record<string, string | string[]>) => void
  disabled?: boolean
}

export function FavoritePanel({ request, onSubmit, disabled }: Props) {
  const [selections, setSelections] = useState<Record<string, string | string[]>>({})

  const handleRadioChange = (fieldName: string, value: string) => {
    setSelections(prev => ({ ...prev, [fieldName]: value }))
  }

  const handleCheckboxToggle = (fieldName: string, choice: string) => {
    setSelections(prev => {
      const current = (prev[fieldName] as string[] | undefined) ?? []
      const next = current.includes(choice)
        ? current.filter(c => c !== choice)
        : [...current, choice]
      return { ...prev, [fieldName]: next }
    })
  }

  const handleConfirm = () => {
    if (!disabled) {
      onSubmit(request.favoriteType, selections)
    }
  }

  const title = request.favoriteType === 'hotel_preference' ? '호텔 취향' : '항공 취향'

  return (
    <div className="favorite-panel">
      <div className="favorite-panel-header">
        <span className="favorite-panel-title">{title} 선택</span>
        <span className="favorite-panel-hint">선택 사항 · 원하는 항목만 골라주세요</span>
      </div>
      <div className="favorite-panel-body">
        {Object.entries(request.options).map(([fieldName, optDef]: [string, FavoriteOptionDef]) => (
          <div key={fieldName} className="favorite-field">
            <div className="favorite-field-label">{optDef.label}</div>
            <div className="favorite-choices">
              {optDef.type === 'radio' && optDef.choices.map(choice => {
                const selected = selections[fieldName] === choice
                return (
                  <button
                    key={choice}
                    type="button"
                    className={`favorite-chip ${selected ? 'selected' : ''}`}
                    onClick={() => handleRadioChange(fieldName, selected ? '' : choice)}
                    disabled={disabled}
                  >
                    {choice}
                  </button>
                )
              })}
              {optDef.type === 'checkbox' && optDef.choices.map(choice => {
                const current = (selections[fieldName] as string[] | undefined) ?? []
                const selected = current.includes(choice)
                return (
                  <button
                    key={choice}
                    type="button"
                    className={`favorite-chip ${selected ? 'selected' : ''}`}
                    onClick={() => handleCheckboxToggle(fieldName, choice)}
                    disabled={disabled}
                  >
                    {choice}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="favorite-panel-footer">
        <button
          type="button"
          className="favorite-confirm-btn"
          onClick={handleConfirm}
          disabled={disabled}
        >
          확인
        </button>
      </div>
    </div>
  )
}
