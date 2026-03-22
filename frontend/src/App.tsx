import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { useAGUIChat } from './hooks/useAGUIChat'
import { ChatMessageBubble } from './components/ChatMessageBubble'

const SUGGESTIONS = [
  '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)',
  '서울에서 오사카 가는 항공편 검색해줘 (7월 1일, 2명)',
  '방콕 여행 정보 알려줘',
  '제주도 4성급 호텔 알려줘 (8월 15일~17일)',
]

export default function App() {
  const { messages, isRunning, error, sendMessage, stopStreaming, clearMessages } = useAGUIChat()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 새 메시지마다 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isRunning) return
    setInput('')
    sendMessage(text)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = (text: string) => {
    if (isRunning) return
    sendMessage(text)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="app">
      {/* 헤더 */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">✈</span>
            <div>
              <div className="logo-title">Travel AI</div>
              <div className="logo-sub">여행 상담 에이전트</div>
            </div>
          </div>
          <div className="header-right">
            <div className={`status-dot ${isRunning ? 'running' : 'idle'}`} />
            <span className="status-label">{isRunning ? '응답 중...' : '대기 중'}</span>
            {messages.length > 0 && (
              <button className="clear-btn" onClick={clearMessages} title="대화 초기화">
                ↺
              </button>
            )}
          </div>
        </div>
      </header>

      {/* 채팅 영역 */}
      <main className="chat-area">
        {isEmpty ? (
          <div className="welcome">
            <div className="welcome-icon">✈️</div>
            <h1 className="welcome-title">어디로 떠나고 싶으신가요?</h1>
            <p className="welcome-desc">
              호텔, 항공편, 여행 정보를 AI가 실시간으로 검색해 드립니다
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="suggestion-btn" onClick={() => handleSuggestion(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map(msg => (
              <ChatMessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {/* 에러 배너 */}
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* 입력 영역 */}
      <footer className="input-area">
        <div className="input-inner">
          <textarea
            ref={inputRef}
            className="input-box"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="여행 목적지, 날짜, 인원을 알려주세요... (Enter로 전송)"
            rows={1}
            disabled={isRunning}
          />
          <button
            className={`send-btn ${isRunning ? 'stop' : 'send'}`}
            onClick={isRunning ? stopStreaming : handleSend}
            disabled={!isRunning && !input.trim()}
          >
            {isRunning ? '■' : '↑'}
          </button>
        </div>
        <div className="input-hint">
          Shift+Enter로 줄바꿈 · Google ADK + AG-UI 미들웨어
        </div>
      </footer>
    </div>
  )
}
