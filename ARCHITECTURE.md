# MobileAssist-Agent 双端口架构详解

## 架构总览

系统采用**双进程架构**，通过 HTTP 解耦两个独立服务，避免不同 ML 框架在同一进程中的 C 扩展冲突。

```
用户请求
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  主服务  :8000  (start_main.py)                          │
│  ├─ BGE-M3 Embedding (sentence-transformers)            │
│  ├─ bge-reranker-v2-m3 (transformers)                   │
│  ├─ FAISS 索引 (47 个工具)                               │
│  ├─ MiMo API (生成回复)                                  │
│  └─ HTTP 调用 ──────────────────────────────────────┐    │
└─────────────────────────────────────────────────────┼────┘
                                                      │
                                                      ▼
                          ┌───────────────────────────────────┐
                          │  意图服务  :8001  (intent_service.py) │
                          │  └─ LoRA 微调 Qwen-7B (transformers) │
                          └───────────────────────────────────┘
```

**为什么要分成两个进程？**

- `sentence-transformers`（主服务的 BGE-M3）和 `transformers`（意图服务的 Qwen-7B）都依赖 PyTorch
- `httpx`（OpenAI SDK 的依赖）的 C 扩展与 PyTorch 的 CUDA 初始化存在冲突
- 如果在同一进程中加载，会导致 segfault（段错误，退出码 139）
- 解决方案：将意图分类模型放到独立进程中，主服务通过 HTTP 调用

---

## 端口 8001 — 意图分类子服务

### 职责

接收用户 query，返回**意图类别标签**。不负责生成回复，只做分类判断。

### 启动方式

```bash
D:\Anaconda\envs\fastApi\python.exe intent_service.py --port 8001
```

等待出现 `Intent classifier loaded.` 表示就绪。

### 加载的模型

| 模型 | 路径 | 用途 |
|------|------|------|
| LoRA 微调 Qwen-7B | `lora/model/lora/` | 6 分类意图识别 |

模型文件约 3GB（`model.safetensors`），启动时加载到 GPU 显存。

### 暴露的端点

#### `GET /health` — 健康检查

```bash
curl http://127.0.0.1:8001/health
```

返回：
```json
{"status": "ok", "model": "E:\\1111\\模拟agent\\lora\\model\\lora"}
```

#### `POST /v1/chat/completions` — 意图分类（OpenAI 兼容格式）

```bash
curl -X POST http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "intent-classifier",
    "messages": [
      {"role": "user", "content": "打开WiFi"}
    ],
    "max_tokens": 20,
    "temperature": 0
  }'
```

返回（标准 OpenAI Chat Completion 格式）：
```json
{
  "id": "intent-1779080506",
  "object": "chat.completion",
  "model": "intent-classifier",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "system_op"},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
}
```

`choices[0].message.content` 就是意图标签，取值为以下 6 种之一：

| 标签 | 含义 | 示例 query |
|------|------|-----------|
| `tool_call` | 工具调用 | "帮我查一下明天北京的天气" |
| `knowledge_qa` | 知识问答 | "什么是量子纠缠" |
| `chitchat` | 闲聊 | "你好啊" |
| `system_op` | 系统操作 | "打开WiFi"、"调高音量" |
| `web_search` | 网络搜索 | "搜索最近的餐厅" |
| `navigation` | 导航出行 | "导航到公司" |

### 内部实现流程

```
POST /v1/chat/completions
  │
  ├─ 1. 从 messages 中提取最后一条 user message 的 content 作为 query
  │
  ├─ 2. 拼接 system prompt（自动生成，不需要客户端传）
  │     "判断以下用户输入的意图类别，只输出类别名称。
  │      类别：tool_call / knowledge_qa / chitchat / system_op / web_search / navigation"
  │
  ├─ 3. 调用 tokenizer.apply_chat_template() 格式化输入
  │
  ├─ 4. model.generate() 推理（beam search，max_new_tokens=10）
  │
  ├─ 5. 解码输出 token，提取纯文本标签
  │
  └─ 6. 封装为 OpenAI 格式返回
```

关键代码（`intent_service.py:105-145`）：

```python
def predict_sync(query: str) -> tuple[str, float, str]:
    # 拼接 system + user 消息
    messages = [
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": query},
    ]
    # 使用模型的 chat template 格式化
    text = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = _tokenizer(text, return_tensors="pt").to(_model.device)

    # 推理
    with torch.no_grad():
        outputs = _model.generate(**inputs, max_new_tokens=10, do_sample=False)

    # 解码新生成的 token
    new_tokens = outputs.sequences[0][inputs["input_ids"].shape[-1]:]
    raw = _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    # 解析标签
    label = "chitchat"  # 默认值
    for l in INTENT_LIST:
        if l in raw.lower():
            label = l
            break

    return label, confidence, raw
```

推理通过 `asyncio.to_thread()` 放到线程池执行，不阻塞 FastAPI 事件循环。

---

## 端口 8000 — 主服务

### 职责

系统的**核心入口**，接收用户请求，完成意图识别→工具召回→执行→生成回复的完整链路。

### 启动方式

```bash
D:\Anaconda\envs\fastApi\python.exe start_main.py
```

等待出现 `Uvicorn running on http://127.0.0.1:8000` 表示就绪。

### 加载的模型/资源

| 模型/资源 | 来源 | 用途 |
|-----------|------|------|
| BAAI/bge-m3 | HuggingFace cache | 将 query 和工具描述编码为向量 |
| BAAI/bge-reranker-v2-m3 | HuggingFace cache | 对粗排结果精排 |
| FAISS 索引 | `data/tool_index/` | 47 个工具的向量检索 |
| 工具注册表 | `tools/registry.json` | 工具元数据（名称、描述、参数） |

启动时**必须先加载这些模型，再导入 httpx/openai**，否则 C 扩展冲突导致 segfault。
这就是 `start_main.py` 的作用（`start_main.py:1-30`）：

```python
# 1. 先加载检索模型（sentence-transformers / transformers）
from app.services.retrieval.embedder import ToolEmbedder
from app.services.retrieval.faiss_store import FaissToolStore
from app.services.retrieval.reranker import ToolReranker

embedder = ToolEmbedder.get_instance()
store = FaissToolStore()
store.load(Path("data/tool_index"), Path("tools/registry.json"))
reranker = ToolReranker.get_instance()

# 2. 预设到 RetrievalPipeline（避免运行时重复加载）
RetrievalPipeline._embedder = embedder
RetrievalPipeline._store = store
RetrievalPipeline._reranker = reranker
RetrievalPipeline._initialized = True

# 3. 现在安全导入 httpx/openai
import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
```

### 暴露的端点

#### `GET /health` — 健康检查

```bash
curl http://127.0.0.1:8000/health
```

返回：
```json
{"status": "ok"}
```

#### `POST /chat` — 核心对话端点

**请求体**（`app/models/request.py`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户标识 |
| `session_id` | string | 会话标识（用于记忆管理） |
| `query` | string | 用户输入的自然语言 |

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","session_id":"s1","query":"你好"}'
```

**响应体**（`app/models/response.py`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `response` | string | 助手回复的自然语言 |
| `intent` | string | 识别出的意图标签 |
| `tools_used` | string[] | 调用的工具列表（无工具调用时为空） |
| `latency_ms` | float | 端到端耗时（毫秒） |

示例返回：
```json
{
  "response": "你好！有什么可以帮你的吗？",
  "intent": "chitchat",
  "tools_used": [],
  "latency_ms": 3245.67
}
```

### 内部处理流程

```
POST /chat
  │
  ├─ 阶段 1：并发执行（asyncio.gather）
  │   ├─ SessionStore.get(session_id)        → 读取历史对话记忆
  │   └─ IntentClassifier.predict(query)      → HTTP 调用 :8001 获取意图标签
  │
  ├─ 阶段 2：Router.dispatch(intent)          → 根据意图分发到对应链路
  │   │
  │   ├─ chitchat ────────────────────────────→ _handle_chitchat()
  │   │   └─ MiMo API 生成闲聊回复
  │   │
  │   ├─ knowledge_qa ────────────────────────→ _handle_knowledge_qa()
  │   │   └─ MiMo API 生成知识回答
  │   │
  │   ├─ tool_call / system_op / web_search / navigation
  │   │   └─ _handle_tool_call()
  │   │       ├─ RetrievalPipeline.retrieve(query)   → 工具召回
  │   │       │   ├─ BGE-M3 编码 query 为向量
  │   │       │   ├─ FAISS 粗排 Top-20
  │   │       │   └─ bge-reranker 精排 Top-5
  │   │       │
  │   │       └─ MCPExecutor.run(query, tools)       → 工具调用
  │   │           ├─ MiMo API 第 1 次调用：LLM 决定调用哪些工具
  │   │           ├─ asyncio.gather 并发执行所有工具
  │   │           └─ MiMo API 第 2 次调用：根据工具结果生成最终回复
  │   │
  │   └─ 其他 ─────────────────────────────────→ _handle_chitchat()（兜底）
  │
  ├─ 阶段 3：更新记忆
  │   └─ SessionStore.update(session_id, query, response)
  │
  └─ 返回 ChatResponse
```

### 阶段详解

#### 阶段 1：并发意图识别 + 记忆读取

`app/routes/chat.py:20-24`：

```python
history, intent_result = await asyncio.gather(
    SessionStore.get(req.session_id),       # 读取最近 10 轮对话
    IntentClassifier.predict(req.query),     # 调用 :8001 意图分类
)
```

`asyncio.gather` 让两个操作并发执行，减少等待时间。

`IntentClassifier.predict` 的实现（`app/services/intent/classifier.py:26-53`）：

```python
# 创建 OpenAI 兼容客户端，指向 :8001
http_client = httpx.AsyncClient(
    transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
)
client = AsyncOpenAI(
    api_key="unused",
    base_url="http://127.0.0.1:8001/v1",
    http_client=http_client,
)

# 调用意图服务
resp = await client.chat.completions.create(
    model="intent-classifier",
    messages=[
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        {"role": "user", "content": query},
    ],
    max_tokens=20, temperature=0,
)
```

> 注：`local_address="0.0.0.0"` 是为了绕过 httpx 在 Windows 上连接 localhost 的兼容性问题。

#### 阶段 2a：闲聊 / 知识问答链路

`app/services/routing/router.py:76-88`：

```python
async def _handle_chitchat(cls, query: str) -> RouteResult:
    client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    resp = await client.chat.completions.create(
        model=LLM_MODEL,  # mimo-v2.5-pro
        messages=[
            {"role": "system", "content": "你是一个友好的手机助手，用简短自然的方式回复。"},
            {"role": "user", "content": query},
        ],
    )
    return RouteResult(response=resp.choices[0].message.content, tools_used=[])
```

`knowledge_qa` 类似，区别是会把 `history`（对话历史）一起传给 LLM。

#### 阶段 2b：工具调用链路

**第一步：工具召回**（`app/services/retrieval/pipeline.py:40-67`）

```
用户 query
    │
    ▼
BGE-M3 编码（sentence-transformers）
    │  query → 1024 维向量
    ▼
FAISS 粗排（Inner Product）
    │  从 47 个工具中召回 Top-20
    ▼
bge-reranker-v2-m3 精排（Cross-Encoder）
    │  计算 query-工具相关性分数，取 Top-5
    ▼
返回 5 个最相关的工具定义
```

```python
async def retrieve(cls, query: str, top_k: int = 5) -> list[dict]:
    # 1. 编码 query
    query_vec = await asyncio.to_thread(cls._embedder.encode_query, query)
    # 2. FAISS 粗排 Top-20
    candidates = await asyncio.to_thread(cls._store.search, query_vec, 20)
    # 3. 附加工具文本
    for cand in candidates:
        cand["tool_text"] = cls._store.get_tool_text(cand["tool_id"])
    # 4. Reranker 精排 Top-5
    results = await asyncio.to_thread(cls._reranker.rerank, query, candidates, top_k)
    # 5. 返回工具元数据
    return [r["tool_meta"] for r in results]
```

**第二步：LLM Tool Call + 执行**（`app/services/agent/mcp_executor.py:46-101`）

```python
async def run(self, query: str, tools: list[dict], history: list[dict]) -> dict:
    openai_tools = ToolRegistry.to_openai_tools(tools)

    # 第 1 次 MiMo API 调用：让 LLM 决定用哪些工具
    response = await self.client.chat.completions.create(
        model=self.model,
        messages=history + [{"role": "user", "content": query}],
        tools=openai_tools,
        tool_choice="auto",
    )

    message = response.choices[0].message
    if not message.tool_calls:
        return {"response": message.content, "tools_used": []}

    # 并发执行所有工具调用
    tool_results = await asyncio.gather(*[
        self._execute_tool(tc.function.name, tc.function.arguments)
        for tc in message.tool_calls
    ])

    # 第 2 次 MiMo API 调用：根据工具结果生成最终回复
    final_response = await self.client.chat.completions.create(
        model=self.model,
        messages=history + [
            {"role": "user", "content": query},
            message,           # assistant 的 tool_calls 消息
            *tool_messages,    # 每个工具的执行结果
        ],
    )

    return {
        "response": final_response.choices[0].message.content,
        "tools_used": [tc.function.name for tc in message.tool_calls],
    }
```

工具执行是 mock 实现（`app/services/agent/mcp_executor.py:24-36`），后续替换为真实逻辑。

---

## 调用链路时序图

### 闲聊场景：用户输入 "你好"

```
客户端         主服务(:8000)          意图服务(:8001)         MiMo API
  │               │                       │                    │
  │──POST /chat──▶│                       │                    │
  │               │──POST /v1/chat───────▶│                    │
  │               │   completions         │                    │
  │               │                       │──model.generate()──│
  │               │◀──{"content":"chitchat"}                    │
  │               │                       │                    │
  │               │──chat.completions.create()─────────────────▶│
  │               │   "你好" → 闲聊回复                          │
  │               │◀──"你好！有什么可以帮你的？"───────────────────│
  │               │                       │                    │
  │◀──JSON────────│                       │                    │
```

### 工具调用场景：用户输入 "打开WiFi"

```
客户端         主服务(:8000)          意图服务(:8001)     FAISS/Reranker    MiMo API
  │               │                       │                    │              │
  │──POST /chat──▶│                       │                    │              │
  │               │──POST /v1/chat───────▶│                    │              │
  │               │                       │                    │              │
  │               │◀──{"content":"system_op"}                   │              │
  │               │                       │                    │              │
  │               │──BGE-M3 encode─────────────────────────────│              │
  │               │──FAISS search──────────────────────────────▶│              │
  │               │◀──Top-20 candidates────────────────────────│              │
  │               │──Reranker──────────────────────────────────▶│              │
  │               │◀──Top-5 tools──────────────────────────────│              │
  │               │                       │                    │              │
  │               │──chat.completions(create, tools)──────────────────────────▶│
  │               │◀──tool_calls: [system_wifi]───────────────────────────────│
  │               │                       │                    │              │
  │               │──execute tool(system_wifi)──▶ [Mock] 结果   │              │
  │               │                       │                    │              │
  │               │──chat.completions(create, tool_result)───────────────────▶│
  │               │◀──"WiFi已打开"───────────────────────────────────────────│
  │               │                       │                    │              │
  │◀──JSON────────│                       │                    │              │
```

---

## 两个端口的对比

| 维度 | 端口 8001（意图服务） | 端口 8000（主服务） |
|------|---------------------|-------------------|
| **入口文件** | `intent_service.py` | `start_main.py` → `app/main.py` |
| **核心职责** | 意图分类（6 分类） | 请求编排、工具召回、生成回复 |
| **加载模型** | LoRA Qwen-7B（~3GB） | BGE-M3 + Reranker + FAISS |
| **依赖库** | torch, transformers | sentence-transformers, faiss, openai |
| **API 格式** | OpenAI 兼容 | 自定义 REST |
| **被调用方** | 被主服务调用 | 被客户端调用 |
| **对外暴露** | 不直接面向用户 | 直接面向用户 |
| **重启影响** | 主服务意图分类失败 | 客户端无法使用 |

---

## 常见问题

### Q: 为什么意图服务用 OpenAI 兼容格式？

复用 OpenAI SDK 的 `AsyncOpenAI` 客户端，免去手写 HTTP 请求和错误处理。接口标准化也便于后续替换为其他模型服务（如 vLLM、TGI）。

### Q: 为什么工具调用要调两次 MiMo API？

- 第 1 次：让 LLM 看到工具列表，决定是否调用、调用哪个、传什么参数（function calling）
- 第 2 次：把工具执行结果喂回 LLM，让它生成用户可读的自然语言回复

### Q: `asyncio.to_thread` 的作用？

模型推理（`model.generate()`）是 CPU/GPU 密集的同步操作。如果不放到线程池，会阻塞 FastAPI 的 asyncio 事件循环，导致其他请求排队等待。

### Q: 为什么用 `start_main.py` 而不是直接 `uvicorn app.main:app`？

`uvicorn app.main:app` 会在导入 `app.main` 时触发所有模块的顶层 import。如果 `httpx` 先于 `sentence-transformers` 被导入，加载 BGE-M3 模型时会 segfault。`start_main.py` 确保模型先加载，再启动 uvicorn。
