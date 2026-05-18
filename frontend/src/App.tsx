import { useState } from 'react'
import { useChat } from './hooks/useChat'
import { ChatArea } from './components/ChatArea'
import { ChatInput } from './components/ChatInput'
import { DebugPanel } from './components/DebugPanel'
import type { Message } from './types'

function App() {
  const { messages, loading, sendMessage, clearMessages } = useChat()
  const [debugMessage, setDebugMessage] = useState<Message | null>(null)
  const [showDebug, setShowDebug] = useState(false)

  const handleSelectDebug = (message: Message) => {
    setDebugMessage(message)
    setShowDebug(true)
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200/80 bg-white/80 backdrop-blur-sm px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm shadow-blue-500/20">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-5 h-5">
              <path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
            </svg>
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-800 leading-tight">MobileAssist-Agent</h1>
            <p className="text-xs text-slate-400">智能手机助手</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearMessages}
            className="text-xs text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            清空对话
          </button>
          <button
            onClick={() => setShowDebug(!showDebug)}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 ${
              showDebug
                ? 'bg-blue-500 text-white shadow-sm shadow-blue-500/25'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
              <path fillRule="evenodd" d="M6.701 2.25c.578-.103 1.168-.228 1.754-.38a.75.75 0 01.594.71v3.515a.75.75 0 01-.374.65 8.964 8.964 0 00-.968.558 5.08 5.08 0 00-.076.058 3.17 3.17 0 00-.07.063l-.003.003a.75.75 0 01-.693.15A18.455 18.455 0 015 8.07v3.18a.75.75 0 01-.374.65 7.496 7.496 0 00-1.56 1.158.75.75 0 01-1.062-1.06A5.996 5.996 0 014 11.18V8.07a16.932 16.932 0 01-.75-.248V4.74a.75.75 0 01.594-.71c.24-.043.483-.084.728-.122.578-.103 1.168-.228 1.754-.38a.75.75 0 01.594.71v.001c0 .247-.043.49-.123.724zM14.22 4.72a.75.75 0 011.06 0 18.455 18.455 0 011.082 2.35.75.75 0 01-.693.15.75.75 0 01-.374-.65V3.06a5.996 5.996 0 00-1.56-1.158.75.75 0 011.062-1.06c.5.443.934.96 1.282 1.535.348.576.613 1.2.788 1.857.06.228.106.46.138.696a.75.75 0 01-.374.65c-.24.152-.49.293-.747.424z" clipRule="evenodd" />
            </svg>
            调试面板
          </button>
        </div>
      </div>

      {/* Main area */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <ChatArea messages={messages} loading={loading} onSelectDebug={handleSelectDebug} />
          <ChatInput onSend={sendMessage} loading={loading} />
        </div>

        {showDebug && (
          <DebugPanel message={debugMessage} onClose={() => setShowDebug(false)} />
        )}
      </div>
    </div>
  )
}

export default App
