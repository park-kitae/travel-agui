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
  const { messages, isRunning, error, sendMessage, stopStreaming, clearMessages, markFormSubmitted } = useAGUIChat()
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

  const handleFormSubmit = (messageId: string, data: Record<string, string>) => {
    if (isRunning) return

    // 폼 제출 상태 업데이트
    markFormSubmitted(messageId)

    // 날짜를 자연어로 변환하는 함수
    const formatDate = (dateStr: string): string => {
      const date = new Date(dateStr)
      const year = date.getFullYear()
      const month = date.getMonth() + 1
      const day = date.getDate()
      return `${year}년 ${month}월 ${day}일`
    }

    let formattedMessage = ''

    // 호텔 예약 폼
    if (data.city !== undefined || data.check_in !== undefined) {
      const city = data.city || ''
      const checkIn = data.check_in ? formatDate(data.check_in) : ''
      const checkOut = data.check_out ? formatDate(data.check_out) : ''
      const guests = data.guests || ''

      if (city && checkIn && checkOut && guests) {
        formattedMessage = `${city}에서 ${checkIn}부터 ${checkOut}까지 ${guests}명이 숙박할 호텔을 검색합니다.`
      } else if (checkIn && checkOut && guests) {
        formattedMessage = `${checkIn}부터 ${checkOut}까지 ${guests}명이 숙박할 호텔을 검색합니다.`
      }
    }
    // 항공편 예약 폼
    else if (data.origin !== undefined || data.destination !== undefined) {
      const origin = data.origin || ''
      const destination = data.destination || ''
      const tripType = data.trip_type || '편도'
      const departureDate = data.departure_date ? formatDate(data.departure_date) : ''
      const returnDate = data.return_date ? formatDate(data.return_date) : ''
      const passengers = data.passengers || ''

      if (tripType === '왕복' && origin && destination && departureDate && returnDate && passengers) {
        formattedMessage = `${origin}에서 ${destination}까지 ${departureDate} 출발, ${returnDate} 귀국, ${passengers}명의 왕복 항공편을 검색합니다.`
      } else if (origin && destination && departureDate && passengers) {
        formattedMessage = `${origin}에서 ${destination}까지 ${departureDate} 출발, ${passengers}명의 편도 항공편을 검색합니다.`
      }
    }

    // 폴백: 기존 방식
    if (!formattedMessage) {
      formattedMessage = Object.entries(data)
        .filter(([key]) => key !== '_formatted')
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
    }

    sendMessage(formattedMessage)
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
              <ChatMessageBubble
                key={msg.id}
                message={msg}
                onFormSubmit={(data) => handleFormSubmit(msg.id, data)}
              />
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
