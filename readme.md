# OncallAgent (Python 版) ｜ 大模型 Agent 开发项目

本项目是 Go 版 [OncallAgent](https://github.com/meilin-agent/OncallAgent) 的 **Python 语言移植版**,供学习对照使用。

**架构、功能、API 接口、配置格式、前端页面与 Go 版一致**,实现语言为 Python,Agent 编排采用 LangGraph:

| Go 版 | Python 版 |
|---|---|
| GoFrame + Eino | FastAPI + **LangGraph**(StateGraph / ToolNode / 条件路由) |
| eino compose.Graph | LangGraph StateGraph(节点 + 边 + 消息归约) |
| eino react / planexecute | LangGraph ReAct 图(agent + tools_condition 循环)与 Plan-Execute-Replan 图(planner / executor / replanner + respond 条件路由) |
| milvus-sdk-go | pymilvus |
| testserver(Go) | prometheus_client 移植版 |

### LangGraph 编排结构(与 Go 版 Eino 的对应)

- **对话 Agent**(`internal/ai/agent/chat_pipeline/`):RAG 预检索渲染初始消息后,进入 LangGraph ReAct 图——
  `START → agent(ChatOpenAI.bind_tools) → tools_condition →(有 tool_calls)tools(ToolNode)→ agent`,无工具调用即到 `END`;消息在 `state.messages`(add_messages)中累积,`step` 计数镜像 Go 版 MaxStep=25
- **AI 运维 Agent**(`internal/ai/agent/plan_execute_replan/`):LangGraph 官方 Plan-Execute-Replan 模式——
  `planner(think 模型,强制 plan 工具)→ executor(quick 模型,内层 ReAct 子图,≤10 次模型调用)→ replanner(强制 plan/respond 二选一)→ 条件路由:respond → END,plan → 回 executor`;外层迭代上限由 `recursion_limit` 控制(≈20 轮)

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. 一键启动(Windows)

双击 `start-oncall.bat` 自动拉起全套服务:

1. Docker Desktop 自检并启动
2. 端口检查(6872 / 8080 / 2112)
3. 启动 Docker 栈:Milvus(etcd/minio/standalone)+ Prometheus
4. 启动告警模拟器 test-server(纯 Python,端口 2112)
5. 检查 Ollama 并预热向量模型(nomic-embed-text)
6. 启动后端 `python main.py`(端口 6872)
7. 启动前端 `python -m http.server 8080`
8. 自动打开浏览器

演示完双击 `stop-oncall.bat` 一键停止。

### 3. 手动启动

```bash
# 后端(项目根目录)
.venv\Scripts\python main.py

# 前端(另开终端)
cd frontend && python -m http.server 8080

# 告警模拟器(另开终端,可选,AI Ops 需要)
.venv\Scripts\python manifest\docker\prometheusTestServer\main.py
```

### 4. 初始化知识库

```bash
.venv\Scripts\python internal\cmd\knowledge_cmd.py
```

### 5. CLI 冒烟脚本(对应 Go 版 internal/ai/cmd)

| 脚本 | 说明 |
|---|---|
| `internal/cmd/knowledge_cmd.py` | 批量建库(docs 下 .md → Milvus) |
| `internal/cmd/recall_cmd.py` | 检索召回测试 |
| `internal/cmd/chat_cmd.py` | 两轮对话测试(记忆) |
| `internal/cmd/ai_ops_cmd.py` | AIOps 冒烟测试 |
| `internal/cmd/llm_tool_cmd.py` | 模型+工具绑定测试 |

### 6. 测试

```bash
.venv\Scripts\pytest tests\ -v
```

## 接口

| 端点 | 方法 | 功能 | 请求体 |
|---|---|---|---|
| `/api/chat` | POST | 快速对话 | `{"Id": "...", "Question": "..."}` |
| `/api/chat_stream` | POST | 流式对话(SSE) | 同上 |
| `/api/upload` | POST | 文件上传入库 | multipart 字段 `file` |
| `/api/ai_ops` | POST | AI 运维分析 | 无 |

统一响应:`{"message": "OK" | <错误文本>, "data": <结果|null>}`,成功与失败均为 HTTP 200。

## 目录结构(镜像 Go 版分层)

```
main.py                     # FastAPI 入口(对应 main.go)
api/chat/v1/chat.py         # 请求/响应 Pydantic 模型(对应 api/chat/v1/chat.go)
internal/
  controller/chat/          # 4 个接口处理器(对应 internal/controller/chat)
  logic/sse/sse.py          # SSE 事件格式化(对应 internal/logic/sse)
  ai/
    models/open_ai.py       # think/quick 模型客户端工厂
    embedder/               # Ollama 向量编码
    loader/ indexer/ retriever/   # 文档加载/Milvus 写入/检索
    agent/
      chat_pipeline/        # RAG 对话流水线
      knowledge_index_pipeline/   # 知识库构建
      plan_execute_replan/  # AIOps Plan-Execute-Replan
    tools/                  # 6 个 LLM 工具
  cmd/                      # 5 个 CLI 冒烟脚本
utility/
  mem/                      # 会话内存(滑动窗口 6,成对丢弃)
  middleware/               # 统一响应格式
  client/milvus_client.py   # Milvus 建库建表/索引/加载
  config/                   # config.yaml 读取
manifest/
  config/                   # config.yaml / config.example.yaml
  docker/                   # compose/prometheus/alert.rules/testserver(Python 移植)
frontend/                   # 前端(原样拷贝)
tests/                      # pytest(对应 Go 版单测)
docs/                       # 知识库文档
```

## 与 Go 版的已知差异(有意为之的 7 处)

1. 上传接口返回真实 `filePath` 与 `fileSize`(Go 版有 stat 目录的 bug)
2. `mysql_crud` 移除 stdin 交互确认(HTTP 服务下不可用)
3. 日志 MCP 地址从代码硬编码移入 `config.yaml` 的 `log_mcp_url`
4. SSE 端点不经过统一响应包装(Go 版会在流尾追加一段 JSON,前端忽略)
5. `query_internal_docs` 错误处理从 log.Fatal 改为抛异常(避免进程级炸弹)
6. SSE 握手 client_id 直接用会话 Id(Go 版读 query 参数的死代码)
7. 一键启动脚本改为启动 Python 进程(原版为 go build/run)
