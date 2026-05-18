import type { Message } from '../types'

interface Props {
  message: Message
  onSelectDebug: (message: Message) => void
}

const INTENT_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  chitchat:       { bg: 'bg-slate-100',   text: 'text-slate-600',   label: '闲聊' },
  knowledge_qa:   { bg: 'bg-purple-100',  text: 'text-purple-600',  label: '知识问答' },
  tool_call:      { bg: 'bg-blue-100',    text: 'text-blue-600',    label: '工具调用' },
  system_op:      { bg: 'bg-amber-100',   text: 'text-amber-600',   label: '系统操作' },
  web_search:     { bg: 'bg-teal-100',    text: 'text-teal-600',    label: '网络搜索' },
  navigation:     { bg: 'bg-rose-100',    text: 'text-rose-600',    label: '导航出行' },
}

function UserAvatar() {
  return (
    <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center shrink-0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="#64748b" className="w-4 h-4">
        <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
      </svg>
    </div>
  )
}

function BotAvatar() {
  return (
    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shrink-0 shadow-sm shadow-blue-500/20">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-4 h-4">
        <path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
      </svg>
    </div>
  )
}

export function MessageBubble({ message, onSelectDebug }: Props) {
  const isUser = message.role === 'user'
  const intentInfo = message.intent ? INTENT_COLORS[message.intent] : null

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && <BotAvatar />}

      <div className={`max-w-[75%] ${isUser ? '' : 'ml-2'}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 ${
            isUser
              ? 'bg-blue-500 text-white rounded-br-md shadow-sm shadow-blue-500/20'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {!isUser && message.intent && (
          <div className="mt-1.5 flex items-center gap-2 flex-wrap">
            {intentInfo && (
              <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full font-medium ${intentInfo.bg} ${intentInfo.text}`}>
                {intentInfo.label}
              </span>
            )}
            {message.tools_used && message.tools_used.length > 0 && (
              <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 font-medium">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-3 h-3 mr-1">
                  <path fillRule="evenodd" d="M6.955 1.45A.5.5 0 017.452 1h1.096a.5.5 0 01.497.45l.17 1.699a6.965 6.965 0 011.874.953l1.592-.854a.5.5 0 01.614.078l.776.777a.5.5 0 01.078.614l-.854 1.592a6.965 6.965 0 01.953 1.874l1.699.17a.5.5 0 01.45.497v1.096a.5.5 0 01-.45.497l-1.699.17a6.965 6.965 0 01-.953 1.874l.854 1.592a.5.5 0 01-.078.614l-.777.776a.5.5 0 01-.614.078l-1.592-.854a6.965 6.965 0 01-1.874.953l-.17 1.699a.5.5 0 01-.497.45H7.452a.5.5 0 01-.497-.45l-.17-1.699a6.965 6.965 0 01-1.874-.953l-1.592.854a.5.5 0 01-.614-.078l-.776-.777a.5.5 0 01-.078-.614l.854-1.592a6.965 6.965 0 01-.953-1.874l-1.699-.17A.5.5 0 011 8.548V7.452a.5.5 0 01.45-.497l1.699-.17A6.965 6.965 0 014.1 4.911l-.854-1.592a.5.5 0 01.078-.614l.777-.776a.5.5 0 01.614-.078l1.592.854A6.965 6.965 0 018.17 2.12l.17-1.699zM8 10.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" clipRule="evenodd" />
                </svg>
                {message.tools_used.join(', ')}
              </span>
            )}
            {message.latency_ms !== undefined && (
              <span className="text-xs text-slate-400">
                {message.latency_ms.toFixed(0)}ms
              </span>
            )}
            <button
              onClick={() => onSelectDebug(message)}
              className="text-xs text-blue-500 hover:text-blue-700 font-medium cursor-pointer transition-colors"
            >
              查看详情
            </button>
          </div>
        )}
      </div>

      {isUser && <UserAvatar />}
    </div>
  )
}
