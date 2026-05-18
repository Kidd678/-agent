# MobileAssist-Agent

面向手机端场景的多工具调度助手，模拟 vivo 蓝心小v "中控 3.0" 架构。用户输入自然语言 query，系统自动完成意图识别、工具召回、Subagent 调度、结果聚合，最终返回自然语言响应。

## 系统架构

```
用户 query
    │
    ▼
┌─────────────────────────────────────┐
│         FastAPI 异步接入层           │
│  POST /chat  ·  asyncio 事件循环    │
└──────────────┬──────────────────────┘
               │ asyncio.gather
       ┌───────┴───────┐
       ▼               ▼
  记忆读取         意图分类器
  (session)      (Qwen-7B SFT)
       └───────┬───────┘
               ▼
    ┌──────────────────────┐
    │      智能路由模块      │
    │  intent → 链路映射   │
    └──┬──────┬──────┬─────┘
       │      │      │
       ▼      ▼      ▼
   工具链路  问答链路  闲聊链路
       │
       ▼
┌─────────────────────────┐
│     工具召回 & 排序      │
│  BGE-M3 → FAISS → Top20 │
│  bge-reranker → Top5    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    MCP Subagent 调度     │
│  Tool Call → 并发执行   │
│  asyncio.gather(tools)  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│      响应生成 & 回写     │
│  LLM 润色 · 记忆更新    │
└─────────────────────────┘
```

### 双进程架构

系统采用双进程设计，通过 HTTP 解耦，避免不同 ML 框架的 C 扩展冲突：

| 服务 | 端口 | 职责 | 加载模型 |
|------|------|------|----------|
| 主服务 | 8000 | 请求编排、工具召回、生成回复 | BGE-M3 + bge-reranker + FAISS |
| 意图服务 | 8001 | 意图分类（6 分类） | LoRA 微调 Qwen-7B |

## 核心能力

### 1. 意图分类

基于 Qwen-7B 的 LoRA SFT 微调，支持 6 类意图识别：

| 标签 | 含义 | 示例 |
|------|------|------|
| `tool_call` | 工具调用 | "帮我查一下明天北京的天气" |
| `knowledge_qa` | 知识问答 | "什么是量子纠缠" |
| `chitchat` | 闲聊 | "你好啊" |
| `system_op` | 系统操作 | "打开WiFi"、"调高音量" |
| `web_search` | 网络搜索 | "搜索最近的餐厅" |
| `navigation` | 导航出行 | "导航到公司" |

### 2. 工具召回排序

两阶段检索流程：
- **粗排**：BGE-M3 编码 + FAISS 向量检索，从 47 个工具中召回 Top-20
- **精排**：bge-reranker-v2-m3 Cross-Encoder 重排，输出 Top-5

### 3. MCP Tool Call

LLM 根据召回的工具定义决定调用哪些工具，`asyncio.gather` 并发执行，再将结果聚合生成最终回复。

### 4. 会话记忆

内存级 Session 记忆，保留最近 10 轮对话历史，支持多轮上下文理解。

### 5. 前端界面

基于 React + Tailwind CSS 的聊天界面，包含：

- **对话区域**：消息气泡、用户/助手头像、意图标签、快捷提问
- **调试面板**：展示 FAISS 粗排 Top-20、Reranker 精排 Top-5、LLM Tool Call 决策、工具执行结果的完整链路
- **开发模式**：Vite dev server 代理 API 请求到后端
- **生产模式**：`npm run build` 构建静态文件，FastAPI 自动挂载

## 目录结构

```
├── app/                        # 主应用
│   ├── main.py                 # FastAPI 入口（含 CORS + 静态文件服务）
│   ├── config.py               # 配置管理
│   ├── routes/chat.py          # /chat 路由
│   ├── services/
│   │   ├── intent/             # 意图分类
│   │   ├── retrieval/          # 工具召回（Embedding + FAISS + Reranker）
│   │   ├── routing/            # 意图路由
│   │   ├── agent/              # MCP Tool Call 执行
│   │   └── memory/             # 会话记忆
│   └── models/                 # Pydantic 请求/响应模型（含 DebugInfo）
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/         # ChatArea, MessageBubble, ChatInput, DebugPanel
│   │   ├── hooks/useChat.ts    # 聊天状态管理
│   │   └── types.ts            # TypeScript 类型定义
│   ├── vite.config.ts          # Vite 配置（Tailwind + API 代理）
│   └── package.json
├── tools/
│   └── registry.json           # 47 个工具的 JSON Schema
├── data/
│   ├── raw/                    # 种子数据
│   ├── processed/              # 训练/验证/测试集
│   ├── tool_index/             # FAISS 向量索引
│   └── tool_test/              # 工具召回测试集
├── training/                   # 微调相关
│   ├── data_gen/               # 数据扩写脚本
│   └── llamafactory/           # LLaMA-Factory 训练配置
├── eval/                       # 评测脚本
├── scripts/                    # 工具脚本
├── intent_service.py           # 意图分类子服务（端口 8001）
├── start_main.py               # 主服务启动入口（端口 8000）
└── start_server.py             # 简化启动脚本
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- CUDA（推理需要 GPU）

### 安装后端依赖

```bash
pip install -r requirements.txt
```

### 安装前端依赖

```bash
cd frontend
npm install
```

### 配置环境变量

复制 `.env.example` 为 `.env`，填入实际的 API Key：

```bash
cp .env.example .env
```

### 启动服务

需要三个终端分别启动意图服务、主服务和前端：

```bash
# 终端 1：启动意图分类服务（端口 8001）
python intent_service.py

# 终端 2：启动主服务（端口 8000）
python start_main.py

# 终端 3：启动前端开发服务器（端口 5173）
cd frontend
npm run dev
```

打开浏览器访问 `http://localhost:5173` 即可使用。

### 测试对话

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","session_id":"s1","query":"帮我查一下明天北京的天气"}'
```

响应示例：

```json
{
  "response": "明天北京天气晴，气温 15-25°C，适合出行。",
  "intent": "tool_call",
  "tools_used": ["weather_query"],
  "latency_ms": 1823.45
}
```

### 生产构建

前端支持构建为静态文件，由 FastAPI 直接服务：

```bash
cd frontend
npm run build
```

构建产物输出到 `frontend/dist/`，主服务启动时会自动挂载。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 异步并发 | asyncio |
| LLM 调用 | OpenAI SDK（兼容 MiMo API） |
| 向量检索 | FAISS + BGE-M3 |
| 精排模型 | bge-reranker-v2-m3 |
| 意图微调 | LLaMA-Factory + LoRA |
| 数据格式 | Pydantic |
| 前端框架 | React 18 + TypeScript |
| 构建工具 | Vite |
| 样式方案 | Tailwind CSS |

## 量化效果

| 指标 | Baseline | 本项目 |
|------|----------|--------|
| 意图分类准确率 | ~73%（zero-shot） | ≥92%（SFT 微调） |
| 工具召回 Recall@5 | ~61%（BM25） | ≥89%（向量+重排） |
| 端到端延迟 | ~4s（串行） | ≤2s（asyncio 并发） |
