# -*- coding: utf-8 -*-
"""第10课: 智能体注册表——登记所有可切换的智能体

设计要点:
- 只做"登记簿", 不 import 任何图(避免与 main.py 循环导入)
- 用法: main.py 建好图之后主动 register() 登记; 端点用 get_agent() 翻簿拿图
"""
from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field


@dataclass
class Agent:
    """一条登记: 介绍 + 图"""
    description: str
    graph: CompiledStateGraph


class AgentInfo(BaseModel):
    """给前端的"名片"字段, 也是 /agents 接口的返回结构"""
    key: str = Field(description="智能体代号")
    description: str = Field(description="智能体介绍")


_registry: dict[str, Agent] = {}  # 登记簿: key -> 登记条


def register(key: str, description: str, graph: CompiledStateGraph):
    """登记一个新智能体(幂等: 重复登记直接覆盖)"""
    _registry[key] = Agent(description=description, graph=graph)


def get_agent(agent_id: str) -> CompiledStateGraph:
    """翻登记簿, 按钥匙拿图"""
    return _registry[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    """拿到所有"名片", 给前端下拉框用"""
    return [AgentInfo(key=k, description=v.description) for k, v in _registry.items()]
