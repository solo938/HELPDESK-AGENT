from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    route_token: Optional[str] = None
    escalated: bool = False
    tool_calls: Optional[list["ToolCallSummary"]] = None

class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    priority: str
    status: str
    created_by: str

class ToolCallSummary(BaseModel):
    tool_name: str
    input: dict
    output: dict
    success: bool
    error_message: Optional[str] = None


