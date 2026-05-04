import { Bot, User } from 'lucide-react'
import { ChatMessage as ChatMessageType, ToolResultSnapshot } from '../types'
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
      const formattedMessage = Object.entries(data)
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
      onFormSubmit({ ...data, _formatted: formattedMessage })
    }
  }

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`}>
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>

      <div className="message-body">
        {!isUser && (message.toolCalls.length > 0 || message.currentStep) && (
          <ToolCallIndicator toolCalls={message.toolCalls} currentStep={message.currentStep} />
        )}

        {!isUser && message.snapshots.length > 0 && (
          <div className="snapshots">
            {message.snapshots.map((snap, i) => (
              <ToolResultCard key={i} snapshot={snap as ToolResultSnapshot} onHotelClick={onHotelClick} />
            ))}
          </div>
        )}

        {!isUser && message.userInputRequest && !message.userInputRequest.submitted && (
          <div className="user-input-form-container">
            <UserInputForm
              fields={message.userInputRequest.fields}
              onSubmit={handleFormSubmit}
              disabled={isStreaming}
            />
          </div>
        )}

        {(message.content || isStreaming) && (
          <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'} ${message.status === 'error' ? 'bubble-error' : ''}`}>
            {message.content
              ? message.content.split('\n').map((line, i, lines) => (
                  <span key={i}>
                    {line}
                    {i < lines.length - 1 && <br />}
                  </span>
                ))
              : isStreaming
                ? <span className="typing-placeholder">답변을 정리하고 있습니다.</span>
                : null}
            {isStreaming && message.content && <span className="cursor" />}
          </div>
        )}

        <div className="message-time">
          {message.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}
