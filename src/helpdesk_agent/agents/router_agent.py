from typing import Literal

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic

from helpdesk_agent.config.prompts.router_prompt import router_prompt


class RouteDecision(BaseModel):
    route: Literal["rag", "action", "escalation"] = Field(
        description="The destination route for the helpdesk request"
    )
    reasoning: str = Field(
        description="Brief explanation for why this route was selected"
    )


def route_request(message: str) -> RouteDecision:
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    structured_llm = llm.with_structured_output(RouteDecision)

    chain = router_prompt | structured_llm

    result = chain.invoke({"message": message})
    return result