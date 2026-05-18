import { useEffect, useRef } from 'react'
import type { Message } from '../types'
import { MessageBubble } from './MessageBubble'

interface Props {
  messages: Message[]
  loading: boolean
  onSelectDebug: (message: Message) => void
}

const SUGGESTIONS = [
  { icon: '🌤️', text: '明天北京天气怎么样' },
  { icon: '⏰', text: '设置明早7点闹钟' },
  { icon: '📱', text: '打开WiFi' },
  { icon: '💡', text: '什么是量子纠缠' },
]

export function ChatArea({ messages, loading, onSelectDebug }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-10 h-10">
              <path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-slate-800 mb-2">MobileAssist-Agent</h2>
          <p className="text-sm text-slate-400 mb-8">你的智能手机助手，试试下面的问题</p>
          <div className="grid grid-cols-2 gap-2">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  const el = document.querySelector<HTMLTextAreaElement>('textarea')
                  if (el) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')!.set!
                    nativeInputValueSetter.call(el, s.text)
                    el.dispatchEvent(new Event('input', { bubbles: true }))
                    el.focus()
                  }
                }}
                className="text-left px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50 transition-all cursor-pointer group"
              >
                <span className="text-base mr-1.5">{s.icon}</span>
                <span className="text-sm text-slate-600 group-hover:text-blue-600 transition-colors">{s.text}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      <div className="max-w-3xl mx-auto">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} onSelectDebug={onSelectDebug} />
        ))}

        {loading && (
          <div className="flex justify-start mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shrink-0 mr-2 shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-4 h-4">
                <path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
              </svg>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-blue-400 rounded-full pulse-dot" />
                <div className="w-2 h-2 bg-blue-400 rounded-full pulse-dot" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 bg-blue-400 rounded-full pulse-dot" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
