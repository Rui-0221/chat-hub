# Chat Hub

一个前后端分离的企业 AI Agent 对话工作台。前端使用 Next.js 14、React 18 与 TypeScript；后端使用 FastAPI、LangGraph、SQLite、Chroma、DeepSeek 和 Ollama。

## 核心能力

- **企业 OA 助手：** 通过 LangGraph Tool Calling 查询 SQLite 员工数据，并使用 Ollama `bge-m3` Embedding 与 Chroma 检索公司手册，组合结构化数据查询与 RAG 制度问答。
- **Supervisor 多 Agent：** 将数学、编程和通用问题分派给 3 个专业 Agent，并通过 `thread_id` 与进程内 `MemorySaver` 维护多轮对话上下文。
- **Thinking Mode 与执行链路可视化：** 为 OA 助手、Supervisor 和子 Agent 启用 DeepSeek Thinking Mode；后端穿透 LangGraph 嵌套子图，前端实时展示可折叠思考内容、Agent 路由步骤与子任务结果。
- **多会话工作台：** 支持 Agent 切换、停止生成，以及会话的新建、重命名、删除和浏览器本地恢复。

## 项目结构

```text
chat-hub/
├─ backend/                  # 独立 Python 后端项目
│  ├─ app/
│  │  ├─ api/routes/        # 版本化 HTTP 接口
│  │  ├─ core/              # 环境与路径配置
│  │  ├─ db/                # SQLModel、会话与仓储
│  │  ├─ resources/         # 公司手册原文
│  │  ├─ schemas/           # API 数据结构
│  │  └─ services/          # 智能体、工具与知识库
│  ├─ scripts/              # 公司手册索引脚本
│  └─ tests/                # 无外部服务的烟雾测试
└─ frontend/                # 独立 Next.js 前端项目
   ├─ app/                  # 页面、布局与样式
   ├─ components/           # 工作台 UI 组件
   ├─ lib/                  # API、SSE 与本地会话
   └─ types/                # TypeScript 类型
```

## 准备环境

- Python 3.13 与 [uv](https://docs.astral.sh/uv/)
- Node.js 18.17+ 与 pnpm
- DeepSeek API key
- 本地 Ollama，以及嵌入模型 `bge-m3`

## 启动后端

在第一个 PowerShell 终端中运行：

```powershell
Set-Location backend
Copy-Item .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY
uv sync --frozen

# 首次运行或手册更新后重建索引；需要 Ollama 正在运行
uv run python -m scripts.seed_knowledge_base

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端健康检查为 `http://127.0.0.1:8000/health`，交互式接口文档为 `http://127.0.0.1:8000/docs`。

## 启动前端

在第二个 PowerShell 终端中运行：

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

访问 `http://127.0.0.1:3000`。前端默认把同源 `/api/*` 请求转发到 `http://127.0.0.1:8000`；部署到其他地址时修改 `frontend/.env.local` 中的 `BACKEND_ORIGIN`。

## 核心接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/health` | 健康检查，不初始化 AI 服务 |
| GET | `/api/v1/agents` | 获取智能体列表 |
| POST | `/api/v1/chat` | SSE 流式聊天，返回 `token`、`reasoning`、`step`、`agent_result`、`error`、`end` 事件 |
| GET/POST | `/api/v1/employees` | 查询或新增员工 |
| GET | `/api/v1/employees/{id}` | 按 ID 查询员工 |

聊天请求示例：

```json
{
  "message": "年假应该如何申请？",
  "thread_id": "your-thread-id",
  "agent_id": "oa-assistant"
}
```

聊天流使用 `data: <JSON>\n\n` 格式发送以下事件：

| 事件 | 说明 | 主要字段 |
| --- | --- | --- |
| `token` | OA 助手或 Supervisor 最终回复的文本片段 | `content` |
| `reasoning` | DeepSeek Thinking Mode 的实时思考内容；子 Agent 事件会标注来源 | `content`、可选 `agent` |
| `step` | Supervisor 进入某个子 Agent 的路由步骤 | `agent` |
| `agent_result` | 子 Agent 完成后返回的完整结论 | `agent`、`content` |
| `error` | 流式生成期间的统一错误信息 | `message` |
| `end` | 当前生成结束，并返回实际使用的会话线程 ID | `thread_id` |

`multi-agent-supervisor` 使用 LangGraph `subgraphs=True` 穿透嵌套子图：子 Agent 的思考内容会实时流式返回，正文则聚合为 `agent_result`，最后由 Supervisor 输出面向用户的结论。

### DeepSeek Thinking Mode 兼容

DeepSeek Thinking Mode 在 Tool Calling 的后续模型调用中要求原样回传 assistant 消息的 `reasoning_content`。项目通过 `_ThinkingChatDeepSeek` 扩展请求序列化，为缺失值提供空串兜底，避免工具循环第二次请求因字段缺失返回 400。

## 验证

```powershell
Set-Location backend
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app scripts
uv lock --check

Set-Location ..\frontend
pnpm typecheck
pnpm build
```

## 使用边界

- `backend/app/resources/handbook.md` 是项目演示模板，不是法律意见、劳动合同或真实公司承诺。
- 员工接口与员工查询工具目前没有认证和字段脱敏，只适合本地演示；接入真实数据前必须增加身份认证、权限、审计和隐私保护。
- 对话记忆使用进程内 `MemorySaver`，服务重启后不会保留，也不适合多 worker 生产部署。
- `reasoning` 思考内容只在当次生成时展示，不写入浏览器本地历史；子 Agent 的路由步骤和结论会随会话保存。
- 不运行索引脚本时，手册工具会提示知识库尚未建立；健康检查与智能体列表仍可用。
