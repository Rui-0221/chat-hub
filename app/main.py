# -*- coding: utf-8 -*-
"""chat-hub 后端主入口

端点一览:
  GET  /hello          健康检查
  GET  /chat           单智能体一次性对话(无流式)
  GET  /sse-demo       SSE 格式演示
  POST /chat/stream    单智能体流式对话(带记忆)
  POST /kb/chat        RAG 知识库问答(带记忆)
  POST /agent/chat     统一智能体入口(agent_id 切换, 带记忆/工具)
  GET  /agents         智能体名录(前端下拉框数据源)
"""

# ================= 导入 =================
import asyncio
import json
from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, START, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from agents import get_agent, get_all_agent_info, register
from db import create_db_and_tables
from employee_router import employee_router
from multi_agent import supervisor_agent
from rag import handbook_store
from tools import get_employee_info, search_handbook

# ================= 全局配置 =================
load_dotenv()  # 加载 .env(DEEPSEEK_API_KEY 等)
model = ChatDeepSeek(model="deepseek-chat")  # 所有智能体共用的对话模型

# ================= 应用与中间件 =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时自动执行一次: 自动建表(不存在才会建)"""
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的源, 常用端口在此添加
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(employee_router)  # 挂上员工 CRUD 接口

# ================= 请求模型 =================
class UserInput(BaseModel):
    """用户发来的聊天请求"""
    message: str
    thread_id: str | None = None    # 会话id: 同一个id=同一个记忆抽屉; None=新抽屉
    stream_tokens: bool = True      # 是否流式输出
    agent_id: str = "oa-assistant"  # 选择哪个智能体(详见 /agents 名录)


# ================= 图1: 基础聊天(无工具) =================
async def call_model(state: MessagesState) -> dict:
    """模型节点: 读状态里的消息 -> 调模型 -> 把回答写回状态"""
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


graph_builder = StateGraph(MessagesState)      # ① 定义"图", 状态=消息列表
graph_builder.add_node("model", call_model)    # ② 注册工位: 取名"model", 干活函数=call_model
graph_builder.add_edge(START, "model")         # ③ 传送带: 入口 -> 模型工位
graph_builder.add_edge("model", END)           # ④ 传送带: 模型工位 -> 出口
graph = graph_builder.compile(checkpointer=MemorySaver())  # ⑤ 编译成可执行图(挂上记忆抽屉柜)


# ================= 图2: OA助手(带工具) =================
agent_model = model.bind_tools([get_employee_info, search_handbook])


async def call_agent(state: MessagesState) -> dict:
    """agent 节点: 和 call_model 一样, 但模型绑定了工具"""
    response = await agent_model.ainvoke(state["messages"])
    return {"messages": [response]}


def needs_tool(state: MessagesState) -> str:
    """裁判: 模型最后一条消息里有没有申请使用工具(tool_calls)"""
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END  # 没有申请使用工具 -> 显示最终答案


agent_builder = StateGraph(MessagesState)
agent_builder.add_node("agent", call_agent)     # 模型(雇员)工位
agent_builder.add_node("tools", ToolNode(tools=[get_employee_info, search_handbook]))  # 工具工位
agent_builder.add_edge(START, "agent")
agent_builder.add_conditional_edges("agent", needs_tool, {"tools": "tools", END: END})  # 走哪条路裁判说了算
agent_builder.add_edge("tools", "agent")        # 工具跑完回到模型(循环的关键)
agent_graph = agent_builder.compile(checkpointer=MemorySaver())  # 给图挂上记忆抽屉柜


# ================= 智能体注册表: 统一登记 =================
# 以后新增智能体: 建好图后在这里加一行即可, 前端自动显示
register("oa-assistant", "OA助手: 员工信息查询与公司手册知识库", agent_graph)
register("multi-agent-supervisor", "多智能体主管: 数学/编程/通用问题的分诊专家", supervisor_agent)


# ================= 基础端点 =================
@app.get("/hello")
async def hello():
    """健康检查"""
    return {"message": "Hello, World!"}


@app.get("/chat")
async def chat(message: str):
    """单智能体一次性对话(无流式)"""
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})
    return {"reply": result["messages"][-1].content}


@app.get("/sse-demo")
async def sse_demo():
    """SSE 格式示例: 模拟生成假数据流"""
    async def fake_stream():
        for word in ["这", "是", "一", "条", "假", "流"]:
            await asyncio.sleep(0.3)
            yield f"data: {json.dumps({'content': word})}\n\n"
    return StreamingResponse(fake_stream(), media_type="text/event-stream")


# ================= SSE 聊天端点 =================
@app.post("/chat/stream")
async def chat_stream(user_input: UserInput):
    """单智能体流式对话(带记忆)"""
    config = {"configurable": {"thread_id": user_input.thread_id or str(uuid4())}}

    async def event_gen():
        async for chunk, metadata in graph.astream(
            {"messages": [HumanMessage(content=user_input.message)]},
            stream_mode="messages",
            config=config,
        ):
            content = chunk.content
            if isinstance(content, str) and content:
                yield f"data: {json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ================= RAG 端点 =================
@app.post("/kb/chat")
async def kb_chat(user_input: UserInput):
    """RAG 知识库问答: 检索 -> 增强 -> 生成"""
    async def event_gen():
        # 第一步: 检索 —— 从手册向量库找与问题最相关的3段
        docs = handbook_store.similarity_search(user_input.message, k=3)
        context = "\n\n".join(doc.page_content for doc in docs)

        # 第二步: 增强 —— 提示词只准依据资料回答, 防编造(RAG的核心)
        system = SystemMessage(content=(
            "你是公司的OA助手。用户的问题只能依据下面公司的资料回答；"
            "资料中没有的，明确说明“公司手册上没有相关信息”，不要编造。\n\n"
            f"【资料】\n{context}"
        ))

        # 第三步: 生成 —— 流式输出
        async for chunk in model.astream([system, HumanMessage(content=user_input.message)]):
            content = chunk.content
            if isinstance(content, str) and content:
                yield f"data:{json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
        yield f"data:{json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ================= 统一智能体入口(agent_id 切换) =================
@app.post("/agent/chat")
async def agent_chat(user_input: UserInput):
    """统一智能体入口: 传 agent_id 选择要对话的智能体(详见 /agents)"""
    async def event_gen():
        config = {"configurable": {"thread_id": user_input.thread_id or str(uuid4())}}
        agent = get_agent(user_input.agent_id)  # 翻登记簿拿图 —— 这就是"切换智能体"

        async for event, metadata in agent.astream(
            {"messages": [HumanMessage(content=user_input.message)]},
            stream_mode="messages",
            config=config,
        ):
            # 双格式兼容过滤(第9课教训): 流的形态随图不同
            #   oa-assistant: 逐字 AIMessageChunk, 节点名为 agent
            #   multi-agent-supervisor: 整条 AIMessage, 且只有主管节点的话给用户
            if not isinstance(event, (AIMessage, AIMessageChunk)):
                continue
            if user_input.agent_id == "multi-agent-supervisor" and metadata.get("langgraph_node") != "supervisor":
                continue
            content = event.content
            if isinstance(content, str) and content:
                yield f"data:{json.dumps({'type': 'token', 'content': content}, ensure_ascii=False)}\n\n"
        yield f"data:{json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ================= 智能体名录 =================
@app.get("/agents")
async def list_agents():
    """所有可切换智能体的名片列表(前端下拉框数据源)"""
    return get_all_agent_info()
