import { useState, useCallback, useRef } from 'react'
import type { Message, ChatResponse } from '../types'

const USER_ID = 'web-user'
let sessionCounter = 0

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const sessionIdRef = useRef(`session-${++sessionCounter}`)

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || loading) return

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: USER_ID,
          session_id: sessionIdRef.current,
          query,
        }),
      })

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const data: ChatResponse = await resp.json()

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: Date.now(),
        intent: data.intent,
        tools_used: data.tools_used,
        latency_ms: data.latency_ms,
        debug: data.debug,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const errMsg: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `请求失败: ${err instanceof Error ? err.message : String(err)}`,
        timestamp: Date.now(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }, [loading])

  const clearMessages = useCallback(() => {
    setMessages([])
    sessionIdRef.current = `session-${++sessionCounter}`
  }, [])

  return { messages, loading, sendMessage, clearMessages }
}
