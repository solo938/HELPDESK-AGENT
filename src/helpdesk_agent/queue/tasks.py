import logging
from helpdesk_agent.queue.celery_app import celery_app
from helpdesk_agent.services.ticketing_service import create_ticket  # ← Fixed import

logger = logging.getLogger(__name__)


@celery_app.task(
    name="create_escalation_ticket",
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def create_escalation_ticket_async(
    self,
    title: str,
    description: str,
    priority: str,
    created_by: str
) -> str:
    """
    Create an escalation ticket asynchronously.
    
    This runs in the background, allowing the chat endpoint to return
    immediately while the ticket is being created.
    """
    logger.info(f"Creating escalation ticket: {title} (priority: {priority})")
    
    try:
        # Call the function directly (not ticketing_service.create_ticket)
        ticket = create_ticket(
            title=title,
            description=description,
            priority=priority,
            requested_by=created_by
        )
        
        ticket_id = ticket["ticket_id"] if isinstance(ticket, dict) else ticket
        logger.info(f"Ticket created successfully: {ticket_id}")
        
        return ticket_id
        
    except Exception as e:
        logger.error(f"Failed to create ticket: {str(e)}")
        raise self.retry(exc=e, countdown=5 ** self.request.retries)