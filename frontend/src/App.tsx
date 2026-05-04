import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { ArrowUp, LoaderCircle, PanelRightOpen, RotateCcw, Square } from 'lucide-react'
import { useAGUIChat } from './hooks/useAGUIChat'
import { ChatMessageBubble } from './components/ChatMessageBubble'
import { StatePanel } from './components/StatePanel'
import { FavoritePanel } from './components/FavoritePanel'
import { Button } from './components/ui/button'
import { Badge } from './components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './components/ui/dialog'
import { Textarea } from './components/ui/textarea'

const SUGGESTIONS = [
  '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)',
  '서울에서 오사카 가는 항공편 검색해줘 (7월 1일, 2명)',
  '방콕 여행 정보 알려줘',
  '제주도 4성급 호텔 알려줘 (8월 15일~17일)',
]

export default function App() {
  const {
    messages, isRunning, error, agentState, uiContext, updateUiContext,
    pendingFavoriteRequest,
    sendMessage, interruptAndSend, stopStreaming, clearMessages,
    markFormSubmitted, submitFavorite,
  } = useAGUIChat()
  const [input, setInput] = useState('')
  const [stateViewerOpen, setStateViewerOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

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

  const handleHotelClick = (hotelCode: string, hotelName: string) => {
    updateUiContext({ selected_hotel_code: hotelCode, current_view: 'hotel_detail' })
    interruptAndSend(`${hotelName} 호텔의 상세 정보를 알려줘`)
  }

  const handleFormSubmit = (messageId: string, data: Record<string, string>) => {
    if (isRunning) return

    markFormSubmitted(messageId)

    const formatDate = (dateStr: string): string => {
      const date = new Date(dateStr)
      const year = date.getFullYear()
      const month = date.getMonth() + 1
      const day = date.getDate()
      return `${year}년 ${month}월 ${day}일`
    }

    let formattedMessage = ''

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
    } else if (data.origin !== undefined || data.destination !== undefined) {
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

    if (!formattedMessage) {
      formattedMessage = Object.entries(data)
        .filter(([key]) => key !== '_formatted')
        .map(([key, value]) => `${key}: ${value}`)
        .join(', ')
    }

    sendMessage(formattedMessage)
  }

  const handleFavoriteSubmit = (selections: Record<string, string | string[]>) => {
    if (!pendingFavoriteRequest) return
    submitFavorite(pendingFavoriteRequest, selections)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="app-shell">
      <div className="app-layout">
        <header className="header">
          <div className="header-inner">
            <div className="brand-block">
              <div className="brand-kicker">Travel Concierge</div>
              <div className="logo-title">Travel AI</div>
              <div className="logo-sub">호텔, 항공편, 여행 정보를 한 화면에서 정리합니다.</div>
            </div>

            <div className="header-actions">
              <Badge variant={isRunning ? 'success' : 'secondary'} className="status-badge">
                {isRunning ? '응답 중' : '대기 중'}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                className="state-trigger"
                onClick={() => setStateViewerOpen(true)}
                aria-label="상태 보기"
              >
                <PanelRightOpen size={16} />
                상태 보기
              </Button>
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="clear-btn"
                  onClick={clearMessages}
                  title="대화 초기화"
                  aria-label="대화 초기화"
                >
                  <RotateCcw size={16} />
                </Button>
              )}
            </div>
          </div>
        </header>

        <main className="chat-area">
          {isEmpty ? (
            <section className="welcome">
              <div className="welcome-copy">
                <Badge variant="outline" className="welcome-badge">Premium planning</Badge>
                <h1 className="welcome-title">원하는 여정을 바로 요청하세요</h1>
                <p className="welcome-desc">
                  일정, 인원, 선호 조건만 알려주시면 호텔과 항공, 여행 정보를 흐름에 맞춰 이어서 안내합니다.
                </p>
              </div>
              <div className="suggestions-grid">
                {SUGGESTIONS.map((s, i) => (
                  <Card key={i} className="suggestion-card">
                    <button className="suggestion-btn" onClick={() => handleSuggestion(s)}>
                      <CardHeader>
                        <CardTitle>추천 요청 {i + 1}</CardTitle>
                        <CardDescription>바로 실행</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p>{s}</p>
                      </CardContent>
                    </button>
                  </Card>
                ))}
              </div>
            </section>
          ) : (
            <div className="messages">
              {messages.map(msg => (
                <ChatMessageBubble
                  key={msg.id}
                  message={msg}
                  onFormSubmit={(data) => handleFormSubmit(msg.id, data)}
                  onHotelClick={handleHotelClick}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {error && (
          <div className="error-banner">
            <span className="error-banner-title">요청 처리 중 문제가 발생했습니다.</span>
            <span>{error}</span>
          </div>
        )}

        {pendingFavoriteRequest && !pendingFavoriteRequest.submitted && (
          <FavoritePanel
            request={pendingFavoriteRequest}
            onSubmit={handleFavoriteSubmit}
            disabled={false}
          />
        )}

        <footer className="input-area">
          <div className="input-composer">
            <Textarea
              ref={inputRef}
              className="input-box"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="여행 목적지, 날짜, 인원을 입력해 주세요."
              rows={1}
              disabled={isRunning || Boolean(pendingFavoriteRequest && !pendingFavoriteRequest.submitted)}
            />
            <Button
              className={`send-btn ${isRunning ? 'stop' : 'send'}`}
              size="icon"
              onClick={isRunning ? stopStreaming : handleSend}
              disabled={(!isRunning && !input.trim()) || Boolean(pendingFavoriteRequest && !pendingFavoriteRequest.submitted)}
              aria-label={isRunning ? '응답 중단' : '메시지 전송'}
            >
              {isRunning ? <Square size={16} /> : <ArrowUp size={18} />}
            </Button>
          </div>
          <div className="input-meta">
            <span>Shift+Enter 줄바꿈</span>
            {isRunning ? (
              <span className="input-running"><LoaderCircle size={14} className="spin" />에이전트 응답 생성 중</span>
            ) : (
              <span>필요한 정보가 부족하면 추가 입력을 요청합니다.</span>
            )}
          </div>
        </footer>
      </div>

      <Dialog open={stateViewerOpen} onOpenChange={setStateViewerOpen}>
        <DialogContent className="state-dialog" closeLabel="상태 뷰어 닫기">
          <DialogHeader>
            <DialogTitle>상태 뷰어</DialogTitle>
            <DialogDescription>
              현재 대화 컨텍스트와 에이전트 상태를 확인할 수 있습니다.
            </DialogDescription>
          </DialogHeader>
          <StatePanel agentState={agentState} uiContext={uiContext} />
        </DialogContent>
      </Dialog>
    </div>
  )
}
