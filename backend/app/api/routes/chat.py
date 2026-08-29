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
        try:
            async for event, metadata in agent.astream(
                {"messages": [HumanMessage(content=payload.message)]},
                stream_mode="messages",
                config=config,
            ):
                if not isinstance(event, (AIMessage, AIMessageChunk)):
                    continue
                if (
                    payload.agent_id == "multi-agent-supervisor"
                    and metadata.get("langgraph_node") != "supervisor"
                ):
                    continue
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
