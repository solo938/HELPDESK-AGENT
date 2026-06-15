from pydantic import BaseModel, Field
from typing import Optional, Literal


class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str


class AgentState(BaseModel):
    user_id: str = Field(..., description="The ID of the user.")
    messages: list[Message] = Field(default_factory=list)
    current_route: Optional[str] = Field(None)
    plan: Optional[str] = Field(None)
    step_count: int = Field(0)
    max_steps: int = Field(5)
    tool_results: list = Field(default_factory=list)
    final_response: Optional[str] = Field(None)
    escalated: bool = Field(False)