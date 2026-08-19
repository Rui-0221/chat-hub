from fastapi import FastAPI
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
load_dotenv()

model =ChatDeepSeek(model="deepseek-chat")
app = FastAPI()

@app.get("/hello")
async def hello():
    return{"message": "Hello, World!"}

@app.get("/chat")
async def chat(message: str):
    response = await model.ainvoke(message)
    return{"reply":response.content}