# MobileAssist-Agent 调试记录与项目状态

## 项目概述

模拟 vivo 蓝心小v"中控 3.0"架构的手机端多工具调度助手。用户输入自然语言 query，系统完成意图识别、工具召回、subagent 调度、结果聚合，返回自然语言响应。

**技术栈：** FastAPI · asyncio · MiMo API · BGE-M3 · LoRA SFT · MCP Tool Call

---

## 调试过程中遇到的问题与解决方案

### 问题 1：FlagEmbedding 导入导致 segfault（退出码 139）

**现象：** 启动 FastAPI 服务时，`from app.main import app` 触发 segfault，进程直接崩溃。

**根因：** `embedder.py` 和 `reranker.py` 在模块顶层 `import` 了 `FlagEmbedding`，而 `FlagEmbedding` 内部加载了完整的 torch/transformers。这与 `classifier.py` 中 `transformers` 的导入在同一进程中冲突。

**解决方案：** 将 `RetrievalPipeline` 中对 `embedder`、`reranker`、`faiss_store` 的导入改为延迟导入（放在 `initialize()` 方法内部），避免在模块加载阶段触发。

```python
# pipeline.py - 修改前
from app.services.retrieval.embedder import ToolEmbedder  # 顶层导入

# pipeline.py - 修改后
async def initialize(cls, ...):
    from app.services.retrieval.embedder import ToolEmbedder  # 延迟导入
```

同理，`router.py` 中对 `RetrievalPipeline` 和 `MCPExecutor` 的导入也改为延迟导入。

---

### 问题 2：Router.dispatch 缺少 await

**现象：** 请求 `/chat` 返回 500，日志报 `AttributeError: 'coroutine' object has no attribute 'response'`。

**根因：** `Router.dispatch()` 中调用 `_handle_chitchat()`、`_handle_knowledge_qa()` 等 async 方法时，缺少 `await`，返回的是协程对象而非 `RouteResult`。

**解决方案：** 在 `dispatch()` 的每个分支加上 `await`。

```python
# 修改前
if label == "chitchat":
    return cls._handle_chitchat(query)

# 修改后
if label == "chitchat":
    return await cls._handle_chitchat(query)
```

---

### 问题 3：MiMo API 模型名大小写

**现象：** API 调用报错 `Not supported model MiMo-V2.5-Pro`。

**根因：** `.env` 文件中写的是 `MiMo-V2.5-Pro`（大写），但 MiMo API 要求小写 `mimo-v2.5-pro`。

**解决方案：** 修改 `.env` 中的 `LLM_MODEL=mimo-v2.5-pro`，同时修改 `config.py` 中的默认值。

---

### 问题 4：类型注解 NameError

**现象：** 使用 `TYPE_CHECKING` 块后，运行时报 `NameError: name 'MCPExecutor' is not defined`。

**根因：** Python 在运行时会解析类体中的类型注解（如 `_executor: MCPExecutor | None`），而 `TYPE_CHECKING` 块中的导入只在类型检查时可用。

**解决方案：** 在模块顶部添加 `from __future__ import annotations`，将所有注解变为惰性字符串，同时去掉 `TYPE_CHECKING` 块。

---

### 问题 5：httpx 与 sentence-transformers 的 C 扩展冲突（segfault）

**现象：** 将意图分类改为独立子服务后，主服务在加载 BGE-M3 模型时仍然 segfault。

**根因：** `httpx`（`openai` 库的依赖）的 C 扩展（h2/hpack）与 `sentence-transformers` 的 CUDA 初始化存在冲突。如果 httpx 先于 sentence-transformers 被导入，加载模型时会崩溃。

**复现：**
```python
import httpx  # 先导入 httpx
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")  # segfault
```

```python
from sentence_transformers import SentenceTransformer  # 先加载模型
model = SentenceTransformer("BAAI/bge-m3")  # 正常
import httpx  # 后导入 httpx，无冲突
```

**解决方案：** 创建 `start_main.py` 启动脚本，在导入任何 httpx/openai 相关模块之前，先同步预加载检索模型。

```python
# start_main.py
# 1. 先加载模型
from app.services.retrieval.embedder import ToolEmbedder
embedder = ToolEmbedder.get_instance()
# ... 加载 reranker、faiss ...

# 2. 再启动 uvicorn（此时才导入 httpx/openai）
import uvicorn
uvicorn.run("app.main:app", ...)
```

同时将 FlagEmbedding 替换为 sentence-transformers + transformers 原生实现，减少一层依赖冲突。

---

### 问题 6：FlagEmbedding 替换为 sentence-transformers

**原因：** FlagEmbedding 库本身也存在与 torch 的兼容性问题，且引入了额外的依赖层。直接使用 sentence-transformers（embedding）和 transformers（reranker）更可控。

**修改文件：**
- `embedder.py`：`BGEM3FlagModel` → `SentenceTransformer`
- `reranker.py`：`FlagReranker` → `AutoModelForSequenceClassification` + `AutoTokenizer`

---

## 当前项目状态

### 已验证通过的功能

| 链路 | 意图类型 | 测试用例 | 结果 |
|------|----------|----------|------|
| 闲聊 | `chitchat` | "你好啊" | 正常回复 |
| 知识问答 | `knowledge_qa` | "什么是量子纠缠" | 正常回复，MiMo 生成详细回答 |
| 系统操作 | `system_op` | "打开WiFi" | 意图识别→工具召回→Tool Call→回复，工具 `system_wifi` 被调用 |

### 架构

```
start_main.py (启动入口)
├── 预加载 sentence-transformers (BGE-M3 + Reranker)
├── 加载 FAISS 索引
└── 启动 uvicorn 主服务 (:8000)

intent_service.py (独立进程 :8001)
├── 加载 LoRA 微调模型 (Qwen-7B)
└── POST /v1/chat/completions → 意图标签

主服务 (:8000)
├── POST /chat
│   ├── asyncio.gather(记忆读取, 意图分类)
│   │   └── 意图分类 → HTTP 调用 intent_service.py
│   ├── Router.dispatch(意图)
│   │   ├── tool_call/system_op/web_search/navigation
│   │   │   ├── RetrievalPipeline (BGE-M3 → FAISS Top-20 → Reranker Top-5)
│   │   │   └── MCPExecutor (LLM Tool Call → asyncio.gather 并发执行)
│   │   ├── knowledge_qa → MiMo API 直接回答
│   │   └── chitchat → MiMo API 闲聊
│   └── 更新记忆 → 返回响应
└── GET /health
```

### 关键指标

| 指标 | 当前值 | 说明 |
|------|--------|------|
| 意图分类 | MiMo API zero-shot | LoRA 模型通过独立子服务加载，6 类意图 |
| 工具召回 | BGE-M3 + FAISS + Reranker | 47 个工具，45 个已定义 + 2 个 mock |
| 端到端延迟 | ~10s | 主要耗时在 MiMo API 调用（2 次：意图 + 生成） |

---

## 启动方式

### 前置条件

- Python 3.10+
- 虚拟环境：`D:\Anaconda\envs\fastApi`
- LoRA 模型路径：`lora/model/lora`
- BGE-M3 模型缓存：`C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-m3/`
- Reranker 模型缓存：`C:/Users/32150/.cache/huggingface/hub/models--BAAI--bge-reranker-v2-m3/`
- FAISS 索引：`data/tool_index/`（已构建）

### 启动步骤

**终端 1 — 启动意图分类子服务（加载 LoRA 模型）：**

```bash
cd e:\1111\模拟agent
D:\Anaconda\envs\fastApi\python.exe intent_service.py --port 8001
```

等待出现 `Intent classifier loaded.` 后表示就绪。

**终端 2 — 启动主服务（加载 BGE + Reranker + FAISS）：**

```bash
cd e:\1111\模拟agent
D:\Anaconda\envs\fastApi\python.exe start_main.py
```

等待出现 `INFO: Uvicorn running on http://127.0.0.1:8000` 后表示就绪。

### 测试

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# 闲聊
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","session_id":"s1","query":"你好"}'

# 工具调用
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","session_id":"s2","query":"打开WiFi"}'
```

或运行测试脚本：

```bash
D:\Anaconda\envs\fastApi\python.exe test_chat.py
D:\Anaconda\envs\fastApi\python.exe test_intent.py
```

---

## 待完成事项

| 项目 | 状态 | 说明 |
|------|------|------|
| 工具召回测试集 | 缺失 | `data/tool_test/retrieval_testset.json` 未创建 |
| 意图分类评测脚本 | 缺失 | `training/eval/eval_intent.py` |
| 延迟对比评测 | 缺失 | `eval/eval_latency.py`（串行 vs 并发） |
| 端到端评测 | 缺失 | `eval/eval_e2e.py` |
| LLaMA-Factory 训练配置 | 缺失 | `training/llamafactory/qwen7b_lora_sft.yaml` |
| requirements.txt | 缺失 | 依赖清单 |
| 工具实际实现 | Mock | 所有工具目前返回 mock 数据 |
| .env.example | 缺失 | 环境变量模板 |
