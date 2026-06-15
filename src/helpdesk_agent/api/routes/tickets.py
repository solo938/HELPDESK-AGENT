import logging
from fastapi import APIRouter, HTTPException
from helpdesk_agent.schemas.api_models import TicketResponse
from helpdesk_agent.services.ticketing_service import ticketing_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tickets"], prefix="/tickets")


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str):
    """
    Get ticket details by ID.
    
    Returns 404 if ticket not found.
    """
    logger.info(f"Fetching ticket {ticket_id}")
    
    ticket = ticketing_service.get_ticket(ticket_id)
    
    if not ticket:
        logger.warning(f"Ticket {ticket_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} not found"
        )
    
    return TicketResponse(
        ticket_id=ticket["ticket_id"],
        title=ticket["title"],
        description=ticket["description"],
        status=ticket["status"],
        priority=ticket["priority"],
        created_by=ticket["created_by"],
        created_at=ticket["created_at"]
    )