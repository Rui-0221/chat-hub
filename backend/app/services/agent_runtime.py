from __future__ import annotations

from functools import lru_cache

from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph_supervisor import create_supervisor

from app.core.config import settings
from app.services.tools import get_employee_info, search_handbook


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    return ChatDeepSeek(model=settings.deepseek_model)


def _build_oa_graph(model: BaseChatModel) -> CompiledStateGraph:
    tools = [get_employee_info, search_handbook]
    model_with_tools = model.bind_tools(tools)
    instructions = SystemMessage(
        content=(
            "你是企业 OA 助手。涉及员工资料时调用员工查询工具；涉及考勤、休假、"
            "加班、差旅、报销、薪资、晋升、安全或其他制度时，必须先调用公司手册工具。"
            "制度答复应说明命中的制度标题与版本，并明确手册是演示模板；资料没有答案时，"
            "直接说明手册未收录，不要凭常识补写公司规则。"
        )
    )

    async def call_agent(state: MessagesState) -> dict:
        response = await model_with_tools.ainvoke([instructions, *state["messages"]])
        return {"messages": [response]}

    def route_tool_call(state: MessagesState) -> str:
        return "tools" if state["messages"][-1].tool_calls else END

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_agent)
    builder.add_node("tools", ToolNode(tools=tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_tool_call, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=MemorySaver())


def _build_supervisor_graph(model: BaseChatModel) -> CompiledStateGraph:
    math_agent = create_react_agent(
        model=model,
        prompt="你是数学专家，负责数学、计算和逻辑推理问题。",
        tools=[],
        name="math_agent",
    ).with_config(tags=["skip_stream"])
    code_agent = create_react_agent(
        model=model,
        prompt="你是编程专家，负责软件开发、调试和代码解释问题。",
        tools=[],
        name="code_agent",
    ).with_config(tags=["skip_stream"])
    general_agent = create_react_agent(
        model=model,
        prompt="你是通用助手，负责数学和编程之外的日常问题。",
        tools=[],
        name="general_agent",
    ).with_config(tags=["skip_stream"])
    supervisor = create_supervisor(
        agents=[math_agent, code_agent, general_agent],
        model=model,
        prompt=(
            "你是主管。请把数学问题交给 math_agent，把编程问题交给 code_agent，"
            "其余问题交给 general_agent。收到助手答案后，直接向用户给出清晰结论。"
        ),
        output_mode="last_message",
        parallel_tool_calls=False,
        add_handoff_back_messages=False,
    )
    return supervisor.compile(checkpointer=MemorySaver())


@lru_cache(maxsize=1)
def get_agent_graphs() -> dict[str, CompiledStateGraph]:
    model = get_chat_model()
    return {
        "oa-assistant": _build_oa_graph(model),
        "multi-agent-supervisor": _build_supervisor_graph(model),
    }


def get_agent_graph(agent_id: str) -> CompiledStateGraph:
    return get_agent_graphs()[agent_id]
