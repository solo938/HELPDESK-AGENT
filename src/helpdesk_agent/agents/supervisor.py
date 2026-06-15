from helpdesk_agent.schemas.state import AgentState
from helpdesk_agent.schemas.tool_inputs import CreateTicketInput
from helpdesk_agent.tools.create_ticket import create_ticket
from helpdesk_agent.tools.base import StepLimitExceeded
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def check_step_limit(state: AgentState) -> AgentState:
    """
    Supervisor node that tracks step count and gracefully escalates if limit exceeded.
    
    Instead of raising an exception (which would crash the user-facing flow),
    this forces escalation to human support and creates a ticket for follow-up.
    
    Args:
        state: Current agent state with step_count and max_steps
    
    Returns:
        Modified state with escalation flags and final response set
    """
    # Increment step counter
    state.step_count += 1
    
    # Log current step count for observability
    logger.debug(
        f"Step {state.step_count}/{state.max_steps} for user {state.user_id}"
    )
    
    # Check if we've exceeded the limit
    if state.step_count >= state.max_steps:
        # Log as warning for monitoring/alerting
        logger.warning(
            f"Step limit exceeded: {state.step_count}/{state.max_steps} steps. "
            f"Escalating user {state.user_id} to human support"
        )
        
        # Signal for internal observability (not raised, just logged/marked)
        # This can be used by monitoring systems to detect runaway conversations
        try:
            # Mark that this request hit the limit (for telemetry)
            raise StepLimitExceeded(
                f"Step limit {state.max_steps} exceeded after {state.step_count} steps"
            )
        except StepLimitExceeded as e:
            # Log the exception but don't let it propagate up
            logger.info(f"Step limit signal recorded: {e}")
            # Optionally attach to state for downstream telemetry
            state.metadata["step_limit_exceeded"] = True
            state.metadata["step_limit_timestamp"] = datetime.utcnow().isoformat()
        
        # Create escalation ticket if not already escalated
        ticket_id = None
        if not state.escalated:
            try:
                ticket_input = CreateTicketInput(
                    title=f"Agent escalation required - step limit exceeded",
                    description=(
                        f"Auto-escalated conversation for user {state.user_id}.\n\n"
                        f"The agent exceeded the maximum step limit of {state.max_steps} "
                        f"while trying to resolve the issue automatically.\n\n"
                        f"Last user message: {state.messages[-1].content if state.messages else 'N/A'}\n"
                        f"Conversation ID: {state.conversation_id}\n"
                        f"Steps taken: {state.step_count}\n\n"
                        f"Please review and follow up with the user."
                    ),
                    priority="medium",  # Medium priority - needs human review but not emergency
                    requested_by="system"
                )
                
                ticket_result = create_ticket(
                    username=state.user_id, 
                    tool_input=ticket_input
                )
                
                if ticket_result.success and ticket_result.data:
                    ticket_id = ticket_result.data.get("ticket_id", "UNKNOWN")
                    logger.info(f"Escalation ticket created: {ticket_id} for user {state.user_id}")
                else:
                    logger.error(f"Failed to create escalation ticket: {ticket_result.error}")
                    
            except Exception as e:
                logger.error(f"Exception while creating escalation ticket: {str(e)}")
        
        # Set escalation flags and final response
        state.escalated = True
        
        # Create user-friendly final response
        if ticket_id:
            state.final_response = (
                f"I wasn't able to fully resolve this automatically after several attempts. "
                f"I've created a support ticket (Ticket #{ticket_id}) for you, and a human team "
                f"member will follow up shortly. Please reference the ticket number if you need "
                f"to check on the status."
            )
        else:
            # Fallback if ticket creation failed
            state.final_response = (
                f"I wasn't able to fully resolve this automatically. "
                f"I've attempted to escalate this to a human support team member, "
                f"but there was an issue creating the ticket. Please contact support "
                f"directly or try again later. I apologize for the inconvenience."
            )
        
        # Store ticket info in state for later reference
        if ticket_id:
            state.metadata["escalation_ticket_id"] = ticket_id
        
        # Optionally clear pending actions since we're escalating
        state.pending_action = None
    
    return state


# Optional: Node for checking if escalation is needed before continuing
def should_continue(state: AgentState) -> str:
    """
    Router function for graph edges - determines if we should continue or escalate.
    
    Returns:
        "continue" - keep processing
        "escalate" - go to escalation handler
    """
    if state.escalated:
        return "escalate"
    
    if state.step_count >= state.max_steps:
        return "escalate"
    
    return "continue"