from typing import Dict, Any
import logging
from helpdesk_agent.schemas.state import AgentState, Message
from helpdesk_agent.guardrails.injection_filter import detect_injection
from helpdesk_agent.guardrails.pii_scrubber import scrub_pii, contains_pii
from helpdesk_agent.agents.router_agent import route_request
from helpdesk_agent.agents.rag_agent import answer_from_kb
from helpdesk_agent.agents.action_agent import execute_action
from helpdesk_agent.agents.escalation_agent import escalate
from helpdesk_agent.agents.supervisor import check_step_limit

logger = logging.getLogger(__name__)


def router_node(state: AgentState) -> Dict[str, Any]:
    """
    Routes the user's request to the appropriate handler.
    Includes security guardrails (injection detection and PII scrubbing).
    """
    try:
        # Get the latest user message
        if not state.messages:
            logger.warning(f"No messages in state for user {state.user_id}")
            return {"current_route": "escalation"}
        
        # Find the most recent user message
        user_messages = [m for m in state.messages if m.role == "user"]
        if not user_messages:
            logger.warning(f"No user message found in state for {state.user_id}")
            return {"current_route": "escalation"}
        
        last_user_message = user_messages[-1]
        raw_query = last_user_message.content
        
        # SECURITY GUARDRAIL: Check for prompt injection
        if detect_injection(raw_query):
            logger.warning(f"Prompt injection blocked for user {state.user_id}: {raw_query[:100]}...")
            # Create security response message
            security_message = Message(
                role="assistant",
                content="SECURITY: Prompt injection attempt detected and blocked. Please ask your question without attempting to override system instructions."
            )
            return {
                "messages": state.messages + [security_message],
                "final_response": security_message.content,
                "current_route": "escalation"
            }
        
        # SECURITY GUARDRAIL: Scrub PII from query
        safe_query = scrub_pii(raw_query)
        if contains_pii(raw_query):
            logger.info(f"PII scrubbed from user {state.user_id}'s query")
        
        # Call router with sanitized query
        result = route_request(message=safe_query)
        
        logger.info(f"Routed user {state.user_id} to {result.route}: {safe_query[:50]}...")
        
        return {"current_route": result.route}
        
    except Exception as e:
        logger.error(f"Router node failed for user {state.user_id}: {str(e)}", exc_info=True)
        return {"current_route": "escalation"}


def rag_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles RAG requests using knowledge base.
    """
    try:
        # Get the latest user message
        user_messages = [m for m in state.messages if m.role == "user"]
        if not user_messages:
            raise ValueError("No user message found")
        
        raw_query = user_messages[-1].content
        
        # Apply PII scrubbing to query (injection already caught in router)
        safe_query = scrub_pii(raw_query)
        
        # Call RAG agent
        result = answer_from_kb(query=safe_query, username=state.user_id)
        
        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=result["answer"]
        )
        
        logger.info(f"RAG responded to user {state.user_id} with {len(result['sources'])} sources")
        
        return {
            "messages": state.messages + [assistant_message],
            "final_response": result["answer"],
            "current_route": None
        }
        
    except Exception as e:
        logger.error(f"RAG node failed for user {state.user_id}: {str(e)}", exc_info=True)
        
        error_message = Message(
            role="assistant",
            content="I encountered an error while searching the knowledge base. Please try again."
        )
        
        return {
            "messages": state.messages + [error_message],
            "final_response": error_message.content,
            "current_route": None
        }


def action_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles action requests (password reset, license check, ticket creation).
    """
    try:
        # Get the latest user message
        user_messages = [m for m in state.messages if m.role == "user"]
        if not user_messages:
            raise ValueError("No user message found")
        
        raw_query = user_messages[-1].content
        
        # Apply PII scrubbing to query (injection already caught in router)
        safe_query = scrub_pii(raw_query)
        
        # Call action agent
        result = execute_action(message=safe_query, state=state)
        
        # Build response content based on result
        if result.success:
            # Handle different tool output structures
            if "temporary_password" in result.data:
                response_content = f"Password reset successfully. Temporary password: {result.data['temporary_password']}"
            elif "status" in result.data:
                response_content = f"License status: {result.data['status']}"
            elif "ticket_id" in result.data:
                response_content = f"Ticket created successfully. Ticket ID: {result.data['ticket_id']}"
            else:
                response_content = "Action completed successfully."
            
            logger.info(f"Action succeeded for user {state.user_id}")
        else:
            # Keep technical error message as-is per single-pass decision
            response_content = f"Action failed: {result.error}"
            logger.warning(f"Action failed for user {state.user_id}: {result.error}")
        
        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response_content
        )
        
        # Update tool results
        tool_results = state.tool_results.copy() if state.tool_results else []
        tool_results.append(result)
        
        return {
            "messages": state.messages + [assistant_message],
            "final_response": response_content,
            "tool_results": tool_results,
            "current_route": None
        }
        
    except Exception as e:
        logger.error(f"Action node failed for user {state.user_id}: {str(e)}", exc_info=True)
        
        error_message = Message(
            role="assistant",
            content="I encountered an error while trying to perform that action. Please try again."
        )
        
        return {
            "messages": state.messages + [error_message],
            "final_response": error_message.content,
            "current_route": None
        }


def escalation_node(state: AgentState) -> Dict[str, Any]:
    """
    Handles escalation by creating a support ticket.
    """
    try:
        # Get the latest user message
        user_messages = [m for m in state.messages if m.role == "user"]
        raw_query = user_messages[-1].content if user_messages else ""
        
        # Apply PII scrubbing to query
        safe_query = scrub_pii(raw_query)
        
        # Call escalation agent
        result = escalate(message=safe_query, state=state)
        
        # Build response based on result
        if result.success:
            ticket_id = result.data.get("ticket_id", "unknown")
            response_content = (
                f"I've escalated this issue to our human support team. "
                f"Your ticket number is {ticket_id}. A team member will follow up shortly."
            )
            logger.info(f"Escalation created ticket {ticket_id} for user {state.user_id}")
        else:
            response_content = (
                "I attempted to escalate this issue but encountered an error. "
                "Please contact support directly or try again later."
            )
            logger.error(f"Escalation failed for user {state.user_id}: {result.error}")
        
        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=response_content
        )
        
        return {
            "messages": state.messages + [assistant_message],
            "final_response": response_content,
            "escalated": True,
            "current_route": None
        }
        
    except Exception as e:
        logger.error(f"Escalation node failed for user {state.user_id}: {str(e)}", exc_info=True)
        
        error_message = Message(
            role="assistant",
            content="I'm having trouble escalating this issue. Please contact support directly."
        )
        
        return {
            "messages": state.messages + [error_message],
            "final_response": error_message.content,
            "escalated": True,
            "current_route": None
        }


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor node that checks step limits.
    """
    try:
        updated_state = check_step_limit(state)
        
        # Build updates dict
        updates = {
            "step_count": updated_state.step_count,
            "escalated": updated_state.escalated,
        }
        
        # Only include final_response if it changed
        if updated_state.final_response != state.final_response:
            updates["final_response"] = updated_state.final_response
        
        logger.debug(f"Supervisor: step {updated_state.step_count}/{updated_state.max_steps} for user {state.user_id}")
        
        return updates
        
    except Exception as e:
        logger.error(f"Supervisor node failed for user {state.user_id}: {str(e)}", exc_info=True)
        # Critical failure - force escalation
        return {
            "escalated": True,
            "final_response": "System error detected. This conversation has been flagged for human review."
        }