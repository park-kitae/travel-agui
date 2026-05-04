import { useState, FormEvent } from 'react'
import { FormField } from '../types'
import { Button } from './ui/button'

interface Props {
  fields: FormField[]
  onSubmit: (data: Record<string, string>) => void
  disabled?: boolean
}

export function UserInputForm({ fields, onSubmit, disabled }: Props) {
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    fields.forEach(field => {
      // default 값이 있으면 사용, 없으면 빈 문자열
      initial[field.name] = field.default || ''
    })
    return initial
  })

  const handleChange = (name: string, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()

    // 필수 필드 검증
    for (const field of fields) {
      const value = formData[field.name]
      if (field.required && (!value || value.trim() === '')) {
        alert(`${field.label}은(는) 필수 입력 항목입니다.`)
        return
      }
    }

    onSubmit(formData)
  }

  return (
    <form className="user-input-form" onSubmit={handleSubmit}>
      <div className="form-fields">
        {fields.map(field => (
          <div key={field.name} className="form-field">
            <label htmlFor={field.name} className="form-label">
              {field.label}
              {field.required && <span className="required-mark">*</span>}
            </label>
            {renderField(field, formData[field.name] || '', handleChange, disabled)}
          </div>
        ))}
      </div>
      <Button
        type="submit"
        className="form-submit-btn"
        disabled={disabled}
        variant="default"
      >
        요청 전송
      </Button>
    </form>
  )
}

function renderField(
  field: FormField,
  value: string,
  onChange: (name: string, value: string) => void,
  disabled?: boolean
) {
  const commonProps = {
    id: field.name,
    value,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      onChange(field.name, e.target.value),
    required: field.required,
    disabled,
    className: 'form-input',
  }

  switch (field.type) {
    case 'date':
      return <input type="date" {...commonProps} />

    case 'number':
      return (
        <input
          type="number"
          {...commonProps}
          min={field.min}
          max={field.max}
          placeholder={field.placeholder}
        />
      )

    case 'select':
      return (
        <select {...commonProps}>
          <option value="">선택하세요</option>
          {field.options?.map(opt => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      )

    case 'text':
    default:
      return (
        <input
          type="text"
          {...commonProps}
          placeholder={field.placeholder}
        />
      )
  }
}
