from typing import Literal, Optional
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from helpdesk_agent.tools.registry import TOOL_REGISTRY
from helpdesk_agent.schemas.tool_inputs import (
    ResetPasswordInput, CheckLicenseInput, CreateTicketInput
)
from helpdesk_agent.schemas.state import AgentState
from helpdesk_agent.tools.base import ToolResult
from helpdesk_agent.config.prompts.action_agent_prompt import action_prompt
from helpdesk_agent.guardrails.output_validator import validate_action_grounding
import logging

logger = logging.getLogger(__name__)


class ActionDecision(BaseModel):
    """LLM decision about which action to take."""
    tool_name: Literal["reset_password", "check_license", "create_ticket"]
    target_username: Optional[str] = None
    software_name: Optional[str] = None
    ticket_title: Optional[str] = None
    ticket_description: Optional[str] = None


def execute_action(message: str, state: AgentState) -> ToolResult:
    """
    Parse user message, decide which tool to use, and execute it.
    Creates its own LLM instance internally.
    
    Includes grounding validation to prevent LLM hallucination of usernames.
    """
    # Create LLM instance internally
    llm = ChatAnthropic(model="claude-3-sonnet-20241022", temperature=0)
    
    # Step 1: Get LLM decision with structured output
    structured_llm = llm.with_structured_output(ActionDecision)
    
    try:
        decision = structured_llm.invoke(
            action_prompt.format_messages(message=message)
        )
        logger.debug(f"Action decision: {decision.tool_name}, fields: {decision.model_dump(exclude={'tool_name'})}")
    except Exception as e:
        logger.error(f"Failed to parse action decision: {str(e)}")
        return ToolResult(
            success=False,
            tool_name="unknown",
            data={},
            error=f"Failed to parse action decision: {str(e)}"
        )
    
    # Step 2: GROUNDING VALIDATION - Check if target username is hallucinated
    if decision.tool_name == "reset_password" and decision.target_username:
        if not validate_action_grounding(
            message=message,
            target_username=decision.target_username,
            requester_id=state.user_id
        ):
            error_msg = (
                f"I couldn't find '{decision.target_username}' mentioned in your message. "
                f"Please specify the username clearly when requesting password resets for other users. "
                f"To reset your own password, say 'my password' or 'reset my password'."
            )
            logger.warning(f"Hallucination detected: target '{decision.target_username}' not in message")
            return ToolResult(
                success=False,
                tool_name=decision.tool_name,
                data={},
                error=error_msg
            )
    
    # Step 3: Get tool info from registry
    tool_info = TOOL_REGISTRY.get(decision.tool_name)
    if not tool_info:
        logger.error(f"Unknown tool: {decision.tool_name}")
        return ToolResult(
            success=False,
            tool_name=decision.tool_name,
            data={},
            error=f"Unknown tool: {decision.tool_name}"
        )
    
    # Step 4: Extract fields relevant to this tool's schema
    input_schema = tool_info["input_schema"]
    schema_fields = set(input_schema.model_fields.keys())
    
    # Build kwargs from decision fields that match the schema
    decision_dict = decision.model_dump(exclude={"tool_name"})
    filtered_kwargs = {
        k: v for k, v in decision_dict.items() 
        if v is not None and k in schema_fields
    }
    
    # Step 5: Inject system fields (requested_by)
    filtered_kwargs["requested_by"] = state.user_id
    
    try:
        # Step 6: Construct tool input and execute
        tool_input = input_schema(**filtered_kwargs)
        logger.info(f"Executing {decision.tool_name} for user {state.user_id}")
        result = tool_info["function"](username=state.user_id, tool_input=tool_input)
        return result
    except Exception as e:
        logger.error(f"Failed to execute {decision.tool_name}: {str(e)}", exc_info=True)
        return ToolResult(
            success=False,
            tool_name=decision.tool_name,
            data={},
            error=f"Failed to execute {decision.tool_name}: {str(e)}"
        )


# Optional: Split version for more granular control (if needed in action_node)
def decide_action(message: str, state: AgentState) -> ActionDecision:
    """
    Only decide which action to take without executing.
    
    Useful when you need to validate before execution.
    """
    llm = ChatAnthropic(model="claude-3-sonnet-20241022", temperature=0)
    structured_llm = llm.with_structured_output(ActionDecision)
    
    try:
        decision = structured_llm.invoke(
            action_prompt.format_messages(message=message)
        )
        return decision
    except Exception as e:
        logger.error(f"Failed to parse action decision: {str(e)}")
        raise


def execute_decided_action(decision: ActionDecision, state: AgentState) -> ToolResult:
    """
    Execute a previously decided action.
    
    Useful when you need to validate between decision and execution.
    """
    # Get tool info from registry
    tool_info = TOOL_REGISTRY.get(decision.tool_name)
    if not tool_info:
        return ToolResult(
            success=False,
            tool_name=decision.tool_name,
            data={},
            error=f"Unknown tool: {decision.tool_name}"
        )
    
    # Extract fields relevant to this tool's schema
    input_schema = tool_info["input_schema"]
    schema_fields = set(input_schema.model_fields.keys())
    
    # Build kwargs from decision fields that match the schema
    decision_dict = decision.model_dump(exclude={"tool_name"})
    filtered_kwargs = {
        k: v for k, v in decision_dict.items() 
        if v is not None and k in schema_fields
    }
    
    # Inject system fields (requested_by)
    filtered_kwargs["requested_by"] = state.user_id
    
    try:
        # Construct tool input and execute
        tool_input = input_schema(**filtered_kwargs)
        result = tool_info["function"](username=state.user_id, tool_input=tool_input)
        return result
    except Exception as e:
        logger.error(f"Failed to execute {decision.tool_name}: {str(e)}", exc_info=True)
        return ToolResult(
            success=False,
            tool_name=decision.tool_name,
            data={},
            error=f"Failed to execute {decision.tool_name}: {str(e)}"
        )