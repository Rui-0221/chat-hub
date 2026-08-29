from app.schemas.agents import AgentInfo


_AGENTS: tuple[AgentInfo, ...] = (
    AgentInfo(
        key="oa-assistant",
        name="企业 OA 助手",
        description="查询员工信息、考勤休假、差旅报销与公司制度",
        capabilities=["员工信息", "公司手册", "制度问答"],
    ),
    AgentInfo(
        key="multi-agent-supervisor",
        name="多智能体主管",
        description="自动分派数学、编程和通用问题给对应专家",
        capabilities=["数学推理", "编程协助", "通用问答"],
    ),
)


def list_agents() -> list[AgentInfo]:
    return [agent.model_copy(deep=True) for agent in _AGENTS]


def has_agent(agent_id: str) -> bool:
    return any(agent.key == agent_id for agent in _AGENTS)
