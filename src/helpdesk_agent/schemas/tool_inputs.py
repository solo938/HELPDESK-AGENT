from pydantic import BaseModel, Field
from typing import Optional, Literal


class ResetPasswordInput(BaseModel):
    username: str = Field(..., description="The username whose password is to be reset.")
    requested_by: str = Field(..., description="The ID of the user/system requesting the reset.")


class CheckLicenseInput(BaseModel):
    username: str = Field(..., description="The username whose license is to be checked.")
    software_name: str = Field(..., description="The name of the software to check.")


class SearchKBInput(BaseModel):
    query: str = Field(..., description="The search query.")
    top_k: int = Field(3, description="Number of top results to return.")


class CreateTicketInput(BaseModel):
    title: str = Field(..., description="The title of the support ticket.")
    description: str = Field(..., description="A detailed description of the issue.")
    priority: Literal["low", "medium", "high"] = Field("medium", description="Priority level.")
    requested_by: str = Field(..., description="The ID of the user the ticket is filed on behalf of.")