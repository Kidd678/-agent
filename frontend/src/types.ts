export interface ChatRequest {
  user_id: string
  session_id: string
  query: string
}

export interface DebugInfo {
  faiss_top20: { rank: number; tool_id: string; score: number }[]
  rerank_top5: { rank: number; tool_id: string; rerank_score: number }[]
  llm_tool_calls: { tool: string; arguments: string }[]
  tool_results: { tool: string; result: string }[]
  llm_final_response: string
}

export interface ChatResponse {
  response: string
  intent: string
  tools_used: string[]
  latency_ms: number
  debug?: DebugInfo
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  intent?: string
  tools_used?: string[]
  latency_ms?: number
  debug?: DebugInfo
}
