import type { Message, DebugInfo } from '../types'

interface Props {
  message: Message | null
  onClose: () => void
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</h3>
      {children}
    </div>
  )
}

function DebugContent({ debug }: { debug: DebugInfo }) {
  return (
    <>
      {debug.faiss_top20.length > 0 && (
        <Section title="FAISS 粗排 Top-20">
          <div className="space-y-1">
            {debug.faiss_top20.map(item => (
              <div key={item.rank} className="flex items-center text-xs">
                <span className="w-6 text-gray-400 shrink-0">{item.rank}.</span>
                <span className="flex-1 font-mono text-gray-700 truncate">{item.tool_id}</span>
                <span className="text-gray-400 ml-2 shrink-0">{item.score.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {debug.rerank_top5.length > 0 && (
        <Section title="Reranker 精排 Top-5">
          <div className="space-y-1">
            {debug.rerank_top5.map(item => (
              <div key={item.rank} className="flex items-center text-xs">
                <span className="w-6 text-gray-400 shrink-0">{item.rank}.</span>
                <span className="flex-1 font-mono text-gray-700 truncate">{item.tool_id}</span>
                <span className="text-gray-400 ml-2 shrink-0">{item.rerank_score.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {debug.llm_tool_calls.length > 0 && (
        <Section title="LLM 工具调用决策">
          <div className="space-y-2">
            {debug.llm_tool_calls.map((tc, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-2">
                <div className="text-xs font-mono font-semibold text-blue-600">{tc.tool}</div>
                <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap break-all">
                  {tc.arguments}
                </pre>
              </div>
            ))}
          </div>
        </Section>
      )}

      {debug.tool_results.length > 0 && (
        <Section title="工具执行结果">
          <div className="space-y-2">
            {debug.tool_results.map((tr, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-2">
                <div className="text-xs font-mono font-semibold text-green-600">{tr.tool}</div>
                <div className="text-xs text-gray-600 mt-1">{tr.result}</div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {debug.llm_final_response && (
        <Section title="LLM 最终回复">
          <div className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2">
            {debug.llm_final_response}
          </div>
        </Section>
      )}
    </>
  )
}

export function DebugPanel({ message, onClose }: Props) {
  return (
    <div className="w-80 border-l border-gray-200 bg-white flex flex-col shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700">调试面板</h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 cursor-pointer"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {!message ? (
          <div className="text-center text-gray-400 text-sm mt-8">
            点击消息中的「查看调试详情」按钮
          </div>
        ) : (
          <>
            <div className="mb-4">
              <div className="text-xs text-gray-400 mb-1">Query</div>
              <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-2">
                {message.role === 'user' ? message.content : '(assistant message)'}
              </div>
            </div>

            {message.intent && (
              <Section title="意图识别">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700 font-mono">
                    {message.intent}
                  </span>
                  {message.latency_ms !== undefined && (
                    <span className="text-xs text-gray-400">
                      {message.latency_ms.toFixed(0)}ms
                    </span>
                  )}
                </div>
              </Section>
            )}

            {message.debug && <DebugContent debug={message.debug} />}
          </>
        )}
      </div>
    </div>
  )
}
