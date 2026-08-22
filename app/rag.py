from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# 1,嵌入模型：把文字变成向量（坐标）的机器（跑在Ollama上，模型名要和“ollama list"一致）
embeddings =OllamaEmbeddings(model="bge-m3",keep_alive=3_600_000)

# 2,向量库：collection_name=这个库叫什么名字；persist_directory=数据存到哪个文件夹
handbook_store=Chroma(
    collection_name="handbook",
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    create_collection_if_not_exists=True, #不存在就自动建
)