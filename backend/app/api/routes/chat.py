from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from app.schemas.chat import ChatRequest
from app.services.agent_registry import has_agent
from app.services.agent_runtime import get_agent_graph


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# supervisor 会转诊到的子 agent 节点名：它们的内容先缓存，节点切回 supervisor 时
# 作为一条完整结果发出（agent_result 事件），而不是逐 token 转发。
_SUPERVISOR_SUB_AGENT_NODES = {"math_agent", "code_agent", "general_agent"}


def _encode_event(payload: dict[str, str]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("")
async def chat(payload: ChatRequest) -> StreamingResponse:
    if not has_agent(payload.agent_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未知智能体：{payload.agent_id}",
        )

    # Initialize before response headers are sent so provider failures become
    # a regular HTTP error instead of a broken 200 stream.
    try:
        agent = get_agent_graph(payload.agent_id)
    except Exception as exc:
        logger.exception("Unable to initialize agent %s", payload.agent_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能服务初始化失败，请检查模型密钥与本地依赖。",
        ) from exc

    thread_id = payload.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async def event_stream() -> AsyncIterator[str]:
        # 子 agent 结果缓存：agent 名 -> 累积文本，节点切回 supervisor 时事件化
        agent_results: dict[str, str] = {}
        last_outer: str | None = None
        try:
            # subgraphs=True：穿透 supervisor 的嵌套子图，逐 token 拿到所有节点的
            # LLM 流（默认不透传，会把嵌套子图聚合为整条消息）。
            async for namespace, (event, metadata) in agent.astream(
                {"messages": [HumanMessage(content=payload.message)]},
                stream_mode="messages",
                subgraphs=True,
                config=config,
            ):
                if not isinstance(event, (AIMessage, AIMessageChunk)):
                    continue
                # 外层节点名：嵌套子图时 namespace 形如 ("supervisor:<uuid>",)，
                # 顶层直接调用时为空元组，此时回退到 metadata 的节点名。
                outer = (
                    str(namespace[0]).split(":")[0]
                    if namespace
                    else metadata.get("langgraph_node")
                )

                if payload.agent_id == "multi-agent-supervisor":
                    # 节点切换提示（进入某个子 agent 时）
                    if outer != last_outer:
                        if outer in _SUPERVISOR_SUB_AGENT_NODES:
                            yield _encode_event({"type": "step", "agent": outer})
                        last_outer = outer
                    if outer in _SUPERVISOR_SUB_AGENT_NODES:
                        # 子 agent 的思考：实时逐 token 转发（带归属），正文仍缓存
                        agent_reasoning = event.additional_kwargs.get("reasoning_content")
                        if agent_reasoning:
                            yield _encode_event(
                                {"type": "reasoning", "content": agent_reasoning, "agent": outer}
                            )
                        # 子 agent 的 token：只积累不转发，完成后作为整体结果发出
                        if isinstance(event.content, str) and event.content:
                            agent_results[outer] = agent_results.get(outer, "") + event.content
                        continue
                    if outer == "supervisor" and agent_results:
                        for name, content in agent_results.items():
                            if content:
                                yield _encode_event(
                                    {"type": "agent_result", "agent": name, "content": content}
                                )
                        agent_results = {}

                # 思考流（deepseek thinking mode 的 reasoning_content）
                reasoning = event.additional_kwargs.get("reasoning_content")
                if reasoning:
                    yield _encode_event({"type": "reasoning", "content": reasoning})

                if isinstance(event.content, str) and event.content:
                    yield _encode_event({"type": "token", "content": event.content})
            yield _encode_event({"type": "end", "thread_id": thread_id})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Chat stream failed for agent %s", payload.agent_id)
            yield _encode_event(
                {"type": "error", "message": "生成回复时发生错误，请稍后重试。"}
            )
            yield _encode_event({"type": "end", "thread_id": thread_id})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
