# Chat Hub 前端

基于 Next.js 14 App Router、React 18 与 TypeScript 的企业 AI 对话工作台。支持智能体切换、SSE 流式回复、停止生成、多会话历史、本地会话恢复和移动端适配。

## 本地运行

复制 `.env.example` 为 `.env.local`，按需设置后端地址，然后运行：

```bash
pnpm dev
```

默认通过 Next.js rewrite 将 `/api/v1/*` 转发到 `http://127.0.0.1:8000`，可通过 `BACKEND_ORIGIN` 修改。

## 可用命令

```bash
pnpm dev        # 启动开发服务器
pnpm build      # 生产构建
pnpm start      # 运行生产构建
pnpm typecheck  # 严格 TypeScript 检查
```

## 接口约定

- `GET /api/v1/agents`：返回智能体列表。
- `POST /api/v1/chat`：接收 `message`、`thread_id`、`agent_id`，返回 `token | error | end` 类型的 SSE 事件。

浏览器会将多会话历史保存到 `chat-hub-session-history`，首次加载时兼容迁移旧的 `chat-hub-session`，并兼容旧版消息中的 `role: "ai"` 格式。历史只存在当前浏览器；`threadId` 对应的服务端上下文并不随之保存，后端重启或清理状态后，旧会话可能无法继续原有上下文。
