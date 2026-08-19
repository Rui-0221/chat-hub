from fastapi import FastAPI
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph,MessagesState,START,END
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