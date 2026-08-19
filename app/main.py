from fastapi import FastAPI
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph,MessagesState,START,END
import json
import asyncio
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse

load_dotenv()

model =ChatDeepSeek(model="deepseek-chat")
async def call_model(state:MessagesState)->dict:
    """模型节点：读状态里的消息->调用模型->把回答写入状态"""
    responese = await model.ainvoke(state["messages"])
    return {"messages": [responese]}

graph_builder=StateGraph(MessagesState) #1,定义”图：，状态=消息列表
graph_builder.add_node("model", call_model) #2，注册工位：取名“model”，干活函数=call_model
graph_builder.add_edge(START, "model")  #3，注册边（传送带：入口->model工位：从START到model
graph_builder.add_edge("model", END) #4，注册边（传送带：model工位->出口：从model到END
graph = graph_builder.compile() #5，编译成可执行图

app = FastAPI()

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


PAGE = r"""<!DOCTYPE html>
<html>
<head>
    <title>SSE Demo</title>
</head>
<body>
    <h3>SSE Demo</h3>
    <button onclick="runDemo('/sse-demo')">假数据流</button>
    <div id="out" style="white-space:pre-wrap;font-size:24px"></div>
    <input id="q" value="给我讲个笑话" style="width:300px">
    <button onclick="runDemo('/chat/stream?message=' + encodeURIComponent(document.getElementById('q').value))">真实 DeepSeek 流</button>
    <script>
        async function runDemo(url) {
            const out=document.getElementById("out");
            out.textContent=""; //清空输出
            const resp=await fetch(url); //发起请求
            const reader=resp.body.getReader(); //获取流读取器
            const decoder=new TextDecoder("utf-8");
            while(true){
                const {done,value}=await reader.read(); //读取流
                if(done) break; //流结束
                const text=decoder.decode(value); //解码
                for(const part of text.split("\n\n")){ //按行处理
                    if(!part.startsWith("data:")) continue; //只处理data行
                    const payload=JSON.parse(part.slice(5)); //解析json
                    out.textContent+=payload.content; //输出内容
                    }
                }
            }
    </script>
</body>
</html>
"""

@app.get("/sse-demo-page",response_class=HTMLResponse)
async def sse_demo_page():
    return PAGE

