from fastapi import FastAPI
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph,MessagesState,START,END
import json
import asyncio
from fastapi.responses import StreamingResponse
from pydantic import BaseModel # 导入BaseModel

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

app = FastAPI() # 实例化FastAPI应用

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



