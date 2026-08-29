from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    key: str = Field(description="Stable agent identifier")
    name: str = Field(description="Short display name")
    description: str = Field(description="Agent purpose")
    capabilities: list[str] = Field(default_factory=list)
