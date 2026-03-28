import { ChatMessage as ChatMessageType } from '../types'
import { ToolCallIndicator } from './ToolCallIndicator'
import { ToolResultCard } from './ToolResultCard'
import { UserInputForm } from './UserInputForm'

interface Props {
  message: ChatMessageType
  onFormSubmit?: (data: Record<string, string>) => void
  onHotelClick?: (hotelCode: string, hotelName: string) => void
}

export function ChatMessageBubble({ message, onFormSubmit, onHotelClick }: Props) {
  const isUser = message.role === 'user'
  const isStreaming = message.status === 'streaming'

  const handleFormSubmit = (data: Record<string, string>) => {
    if (onFormSubmit) {
      // 구조화된 데이터를 자연어로 변환
      const formattedMessage = Object.entries(data)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
      onFormSubmit({ ...data, _formatted: formattedMessage })
    }
  }

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="avatar assistant-avatar">
          <span>✈</span>
        </div>
      )}

      <div className="message-body">
        {/* 툴 실행 인디케이터 (어시스턴트만) */}
        {!isUser && (message.toolCalls.length > 0 || message.currentStep) && (
          <ToolCallIndicator
            toolCalls={message.toolCalls}
            currentStep={message.currentStep}
          />
        )}

        {/* 도구 결과 카드들 */}
        {!isUser && message.snapshots.length > 0 && (
          <div className="snapshots">
            {message.snapshots.map((snap, i) => (
              <ToolResultCard key={i} snapshot={snap} onHotelClick={onHotelClick} />
            ))}
          </div>
        )}

        {/* 사용자 입력 폼 */}
        {!isUser && message.userInputRequest && !message.userInputRequest.submitted && (
          <div className="user-input-form-container">
            <UserInputForm
              fields={message.userInputRequest.fields}
              onSubmit={handleFormSubmit}
              disabled={isStreaming}
            />
          </div>
        )}

        {/* 텍스트 버블 */}
        {(message.content || isStreaming) && (
          <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'} ${message.status === 'error' ? 'bubble-error' : ''}`}>
            {message.content
              ? message.content.split('\n').map((line, i) => (
                  <span key={i}>
                    {line}
                    {i < message.content.split('\n').length - 1 && <br />}
                  </span>
                ))
              : isStreaming
              ? <span className="typing-placeholder">생각 중...</span>
              : null}
            {isStreaming && message.content && <span className="cursor" />}
          </div>
        )}

        <div className="message-time">
          {message.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>

      {isUser && (
        <div className="avatar user-avatar">
          <span>나</span>
        </div>
      )}
    </div>
  )
}
