import { useState, useCallback } from 'react'
import { ChatMessage } from '../types'

export function useChatMessages() {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages(prev => [...prev, msg])
  }, [])

  const updateMessage = useCallback((id: string, updater: (m: ChatMessage) => ChatMessage) => {
    setMessages(prev => prev.map(m => m.id === id ? updater(m) : m))
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    addMessage,
    updateMessage,
    clearMessages,
  }
}
