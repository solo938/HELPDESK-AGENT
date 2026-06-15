from typing import Literal, Optional
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from helpdesk_agent.schemas.tool_inputs import CreateTicketInput
from helpdesk_agent.schemas.state import AgentState
from helpdesk_agent.tools.base import ToolResult
from helpdesk_agent.config.prompts.escalation_prompt import escalation_prompt
from helpdesk_agent.queue.tasks import create_escalation_ticket_async
import logging

logger = logging.getLogger(__name__)


class TicketDraft(BaseModel):
    """LLM-generated ticket draft for escalation."""
    title: str
    description: str
    priority: Literal["low", "medium", "high"]


def escalate(message: str, state: AgentState, async_mode: bool = True) -> ToolResult:
    """
    Escalate an issue by creating a support ticket from conversation context.
    
    Supports two modes:
    - async_mode=True: Creates ticket in background via Celery, returns immediately
    - async_mode=False: Creates ticket synchronously (blocks until complete)
    
    Args:
        message: The user's message that triggered escalation
        state: Current agent state with conversation history
        async_mode: If True, use async task queue; if False, create ticket synchronously
    
    Returns:
        ToolResult with ticket creation outcome
    
    Example:
        >>> state = AgentState(user_id="alice", messages=[...])
        >>> result = escalate("I need help with VPN", state)
        >>> print(result.success)  # True even if ticket still creating
    """
    
    # Step 1: Generate ticket draft from conversation
    # This still happens synchronously because we need the ticket content
    llm = ChatAnthropic(
        model="claude-3-sonnet-20241022",
        temperature=0,
        max_tokens=500
    )
    
    structured_llm = llm.with_structured_output(TicketDraft)
    
    # Format conversation context (last 5 messages for relevance)
    context_str = "\n".join([
        f"{msg.role.upper()}: {msg.content}" 
        for msg in state.messages[-5:]
    ])
    
    logger.info(f"Escalating issue for user {state.user_id}: {message[:50]}...")
    
    try:
        # Generate ticket draft using LLM
        draft = structured_llm.invoke(
            escalation_prompt.format_messages(
                message=message,
                context=context_str
            )
        )
        
        logger.info(f"Generated ticket draft: {draft.title} (priority: {draft.priority})")
        
        # Step 2: Create ticket (sync or async)
        if async_mode:
            # ASYNC: Queue ticket creation in background
            logger.info(f"Queueing async ticket creation for user {state.user_id}")
            
            # Start async task (doesn't block)
            task = create_escalation_ticket_async.delay(
                title=draft.title,
                description=f"{draft.description}\n\n---\nOriginal user message: {message}",
                priority=draft.priority,
                created_by=state.user_id
            )
            
            # Return immediately with task ID
            return ToolResult(
                success=True,
                tool_name="create_ticket",
                data={
                    "task_id": task.id,
                    "status": "pending",
                    "message": "Ticket creation queued. You will be notified when complete."
                },
                error=None
            )
        else:
            # SYNC: Create ticket synchronously (original behavior)
            from helpdesk_agent.services.ticketing_service import ticketing_service
            
            ticket = ticketing_service.create_ticket(
                title=draft.title,
                description=f"{draft.description}\n\n---\nOriginal user message: {message}",
                priority=draft.priority,
                requested_by=state.user_id
            )
            
            return ToolResult(
                success=True,
                tool_name="create_ticket",
                data={
                    "ticket_id": ticket["ticket_id"],
                    "status": ticket["status"],
                    "created_at": ticket["created_at"]
                },
                error=None
            )
        
    except Exception as e:
        logger.error(f"Escalation failed for user {state.user_id}: {str(e)}", exc_info=True)
        
        # Return properly formatted ToolResult with required tool_name field
        return ToolResult(
            success=False,
            tool_name="create_ticket",
            data={},
            error=f"Failed to create escalation ticket: {str(e)}"
        )


# Convenience function for sync mode (backward compatible)
def escalate_sync(message: str, state: AgentState) -> ToolResult:
    """
    Synchronous version of escalate (blocks until ticket created).
    Use this when you need the ticket ID immediately.
    """
    return escalate(message, state, async_mode=False)


# Convenience function for async mode (explicit)
def escalate_async_task(message: str, state: AgentState) -> ToolResult:
    """
    Async version using Celery task queue.
    Returns immediately with task ID, ticket created in background.
    """
    return escalate(message, state, async_mode=True)


# Original async wrapper for concurrent execution (kept for compatibility)
async def escalate_async(message: str, state: AgentState) -> ToolResult:
    """
    Async wrapper for concurrent execution within the same process.
    Not to be confused with Celery async task queue.
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, escalate, message, state, False)
    return result


# Function to check task status
def get_escalation_status(task_id: str) -> Optional[dict]:
    """
    Check the status of an async escalation task.
    
    Args:
        task_id: The task ID returned from escalate()
    
    Returns:
        Dict with task status or None if task not found
    """
    from celery.result import AsyncResult
    from helpdesk_agent.queue.celery_app import celery_app
    
    try:
        task = AsyncResult(task_id, app=celery_app)
        
        if task.ready():
            if task.successful():
                return {
                    "status": "completed",
                    "result": task.result,  # ticket_id
                    "success": True
                }
            else:
                return {
                    "status": "failed",
                    "error": str(task.info),
                    "success": False
                }
        else:
            return {
                "status": "pending",
                "task_id": task_id,
                "success": None
            }
    except Exception as e:
        logger.error(f"Failed to check task status: {e}")
        return None