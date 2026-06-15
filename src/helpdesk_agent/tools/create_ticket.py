# tools/create_ticket.py

from helpdesk_agent.tools.base import safe_execute
from helpdesk_agent.schemas.tool_inputs import CreateTicketInput
from helpdesk_agent.services.ticketing_service import create_ticket as create_ticket_in_db


@safe_execute(required_permission=None)
def create_ticket(tool_input: CreateTicketInput) -> dict:
    ticket_id = create_ticket_in_db(
        title=tool_input.title,
        description=tool_input.description,
        priority=tool_input.priority,
        created_by=tool_input.requested_by,
    )
    return {
        "ticket_id": ticket_id,
        "title": tool_input.title,
        "priority": tool_input.priority,
        "status": "open",
    }