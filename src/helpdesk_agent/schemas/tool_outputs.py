from pydantic import BaseModel
from typing import Optional, Any

class ToolResult(BaseModel):
    success: bool = True
    tool_name: str
    data: Optional[Any] = None
    error: Optional[str] = None


class ToolError(BaseModel):
    success: bool = False
    tool_name: str
    error_type: str
    message: str