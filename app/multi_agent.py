# -*- coding: utf-8 -*-
"""第9课: 多智能体协作——数学/编程/通用 三个专科医生 + 主管(分诊台)"""
from dotenv import load_dotenv
load_dotenv()  # ① 这里为什么也要 load_dotenv?(提示: main.py 的 import 在 load_dotenv 之前)

from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import MemorySaver

model = ChatDeepSeek(model="deepseek-chat")

# ② 三个专科医生: 工厂函数一行生产一个"第7课式"的图
math_agent = create_react_agent(
    model=model,
    prompt="""你是数学专家,负责回答数学、计算类问题; 与数学无关的问题不要回答。""",
    tools=[],                    # 数学诊所不带工具
    name="math_agent",                 # --填空A: 诊所的名字--
).with_config(tags=["skip_stream"])  # ③ 这个标签是干嘛的? 想一想

code_agent = create_react_agent(
    model=model,
    prompt="""你是编程专家,负责解决编程问题。""",
    tools=[],
    name="code_agent",                 # --填空B--
).with_config(tags=["skip_stream"])

general_agent = create_react_agent(
    model=model,
    prompt="""你是通用助手,负责回答数学和编程之外的问题。""",
    tools=[],
    name="general_agent",                 # --填空C--
).with_config(tags=["skip_stream"])

# ④ 主管(分诊台)
supervisor = create_supervisor(
    agents=[math_agent, code_agent, general_agent],   # --填空D: 三个手下--
    model=model,
    prompt="""你是主管,负责管理三个助手:
- math_agent: 数学、计算
- code_agent: 编程、代码
- general_agent: 其他通用问题

请根据用户问题选择最合适的 一个 助手来回答。
如果助手已经给出了答案,你没有新内容可补充,就只把答案直接转告用户。""",
    output_mode="last_message",          # --填空E: 最后只输出主管的最终答复--
    parallel_tool_calls=False,    # --填空F: 一次只转诊一人--
    add_handoff_back_messages=False,  # --填空G: 转诊中间过程不回填对话--
)

supervisor_agent = supervisor.compile(checkpointer=MemorySaver())  # ⑤ 老规矩: 记忆抽屉柜
