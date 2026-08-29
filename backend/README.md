# Chat Hub Backend

FastAPI、LangGraph、SQLite 与 Chroma 组成的 Chat Hub 后端服务。

从仓库根目录启动：

```powershell
uv sync --project backend --frozen
uv run --project backend uvicorn app.main:app --app-dir backend --reload --port 8000
```

健康检查位于 `GET /health`，版本化业务接口位于 `/api/v1`。公司手册索引需要本地 Ollama 已安装 `bge-m3` 后执行：

```powershell
uv run --directory backend python -m scripts.seed_knowledge_base
```

复制 `.env.example` 为 `.env` 并配置 DeepSeek 密钥；服务也兼容读取仓库根目录原有的 `.env`。
