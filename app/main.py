from fastapi import FastAPI
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage 
from langgraph.graph import StateGraph,MessagesState,START,END
import json
import asyncio
from fastapi.responses import StreamingResponse
from pydantic import BaseModel # 导入BaseModel
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db import create_db_and_tables
from employee_router import employee_router
from rag import handbook_store
from langgraph.prebuilt import ToolNode # 现成的"执行工具"工位
from langchain_core.messages import AIMessageChunk # 过滤器用
from tools import get_employee_info,search_handbook

@asynccontextmanager
async def lifespan(app:FastAPI):
    """应用启动时自动执行一次：自动建表（不存在才会自动建表）"""
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的源，可以根据需要修改
    allow_credentials=True,# 允许携带cookie
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)
app.include_router(employee_router)# 挂上员工接口

class UserInput(BaseModel):
    """用户发来的聊天请求"""
    message: str
    thread_id: str | None = None  # 可选字段，会话id,默认为None,表示消息所属的线程ID
    stream_tokens: bool =True  # 可选字段，默认为True，表示是否流式输出token

load_dotenv() # 加载环境变量

model =ChatDeepSeek(model="deepseek-chat") # 实例化模型
async def call_model(state:MessagesState)->dict: # 定义模型节点的处理函数
    """模型节点：读状态里的消息->调用模型->把回答写入状态"""
    responese = await model.ainvoke(state["messages"])
    return {"messages": [responese]}

graph_builder=StateGraph(MessagesState) #1,定义”图：，状态=消息列表
graph_builder.add_node("model", call_model) #2，注册工位：取名“model”，干活函数=call_model
graph_builder.add_edge(START, "model")  #3，注册边（传送带：入口->model工位：从START到model
graph_builder.add_edge("model", END) #4，注册边（传送带：model工位->出口：从model到END
graph = graph_builder.compile() #5，编译成可执行图

# ----带工具的agent(第二个图)----
agent_model = model.bind_tools([get_employee_info,search_handbook])

async def call_agent(state:MessagesState)->dict:
    """agent 节点：和call_model一样，但用的模型绑定了工具"""
    response = await agent_model.ainvoke(state["messages"])
    return {"messages":[response]}

def needs_tool(state:MessagesState)->str:
    """裁判：模型最后一条消息里有没有申请使用工具（tool_calls)"""
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END # 没有申请使用工具->显示最终答案

agent_builder = StateGraph(MessagesState)
agent_builder.add_node("agent",call_agent) #模型（雇员）工位
agent_builder.add_node("tools",ToolNode(tools=[get_employee_info,search_handbook])) #工具工位
agent_builder.add_edge(START,"agent")
agent_builder.add_conditional_edges("agent",needs_tool,{"tools":"tools",END:END}) # 走哪条路（进入哪个节点）裁判说了算
agent_builder.add_edge("tools","agent") # 工具跑完回到模型（循环的关键）
agent_graph =agent_builder.compile()

@app.get("/hello")
async def hello():
    return{"message": "Hello, World!"}

@app.get("/chat")
async def chat(message: str):
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]}) #调用图，传入状态=消息列表=[用户消息]
    return{"reply": result["messages"][-1].content}

# SSE示例：模拟生成假数据流
@app.get("/sse-demo")
async def sse_demo():
    async def fake_stream():
        for i,word in enumerate(["这","是","一","条", "假", "流"]):
            await asyncio.sleep(0.3) #模拟生成耗时
            yield f"data: {json.dumps({'content':word})}\n\n"
    return StreamingResponse(fake_stream(), media_type="text/event-stream")

# SSE示例：调用图生成消息流
"""
@app.get("/chat/stream")
async def chat_steam(message: str):
    async def event_gen(): # 定义异步生成器函数
        async for chunk, metadata in graph.astream( # 调用图，传入状态=消息列表=[用户消息]
            {"messages":[HumanMessage(content=message)]}, # 传入状态=消息列表=[用户消息]
            stream_mode="messages", # 指定流模式为"messages"，表示按消息流式输出
        ):
            content=chunk.content # 获取消息内容
            if isinstance(content,str) and content: #跳过空消息
                yield f"data: {json.dumps({'content':content})}\n\n" # 按SSE格式输出消息
    return StreamingResponse(event_gen(), media_type="text/event-stream")
"""

@app.post("/chat/stream")
async def chat_stream(user_input: UserInput):
    async def event_gen():
        async for chunk, metadata in graph.astream(
            {"messages": [HumanMessage(content=user_input.message)]},
            stream_mode="messages",
        ):
            content=chunk.content
            if isinstance(content,str) and content:
                yield f"data: {json.dumps({'type': 'token', 'content':content},ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n" 
    return StreamingResponse(event_gen(), media_type="text/event-stream")

@app.post("/kb/chat")
async def kb_chat(user_input:UserInput):
    async def event_gen():
        # ---第一步：检索----
        docs =handbook_store.similarity_search(user_input.message,k=3)
        context = "\n\n".join(doc.page_content for doc in docs)

        # 第二步：增强（提示词只准提供依据资料，防编造--rag的核心）
        system=SystemMessage(content=(
            "你是公司的OA助手。用户的问题只能依据下面公司的资料回答；"
            "资料中没有的，明确说明“公司手册上没有相关信息”，不要编造。\n\n"
            f"【资料】\n{context}"
        ))

        # 第三步：生成（复用之前的流式写法）
        async for chunk in model.astream([system,HumanMessage(content=user_input.message)]):
            content =chunk.content
            if isinstance(content,str) and content:
                yield f"data:{json.dumps({'type':'token','content':content},ensure_ascii=False)}\n\n"
        yield f"data:{json.dumps({'type':'end'})}\n\n"
    return StreamingResponse(event_gen(),media_type="text/event-stream")

@app.post("/agent/chat")
async def agent_chat(user_input:UserInput):
    async def event_gen():
        async for chunk,metadata in agent_graph.astream(
            {"messages":[HumanMessage(content=user_input.message)]},
            stream_mode="messages"
        ):
            # 流里混着两种信息：模型的话（AIMessagechunk)和工具的执行结果（ToolMessage)
            # 只把模型的话转发给用户
            if isinstance(chunk,AIMessageChunk):
                content =chunk.content
                if isinstance(content,str) and content:
                    yield f"data:{json.dumps({'type':'token','content':content},ensure_ascii=False)}\n\n"
        yield f"data:{json.dumps({'type':'end'})}\n\n"
    return StreamingResponse(event_gen(),media_type="text/event-stream")
        
