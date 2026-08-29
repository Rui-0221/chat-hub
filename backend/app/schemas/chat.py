from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12_000)
    thread_id: str | None = Field(default=None, max_length=128)
    agent_id: str = Field(default="oa-assistant", max_length=80)
