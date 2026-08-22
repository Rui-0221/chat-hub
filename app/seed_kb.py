from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag import handbook_store

# 1,读手册
with open("./resource/handbook.md",encoding="utf-8") as f:
    text=f.read()

# 2,分块
splitter =RecursiveCharacterTextSplitter(
    chunk_size=100, #规定每块约200字
    chunk_overlap=20, # 相邻块要重叠50字，防止语义被切断
    length_function=len,
)
chunks = splitter.create_documents([text]) # ->一个Document列表，每个里面有page_content(原文)

# 3，清空旧数据再入库（重复跑脚本不产生重复数据）
handbook_store.reset_collection() # 删除旧数据库+重建真空库
handbook_store.add_documents(chunks) # 这一步会调用bge-m3算向量，首次使用时较慢

result=handbook_store.similarity_search("薪资",k=3)
print(result)
for i,doc in enumerate(result):
    # f-string:{}里的是运算结果，i+1是因为表格上的i从0开始
    print(f"第{i+1}段：{doc.page_content}")
