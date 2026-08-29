from fastapi import APIRouter

from app.schemas.agents import AgentInfo
from app.services.agent_registry import list_agents


router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentInfo])
async def get_agents() -> list[AgentInfo]:
    """Return agent metadata without initializing model providers."""
    return list_agents()
