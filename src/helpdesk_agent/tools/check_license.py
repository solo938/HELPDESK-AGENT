from helpdesk_agent.tools.base import safe_execute
from helpdesk_agent.schemas.tool_inputs import CheckLicenseInput
from helpdesk_agent.services.license_db import get_license_status


@safe_execute(required_permission="view_license_status")
def check_license(tool_input: CheckLicenseInput) -> dict:
    """
    Check the license status for a user's software.
    
    Args:
        tool_input: CheckLicenseInput containing username and software_name
    
    Returns:
        dict with keys:
            - username: The user who owns the license
            - software_name: The software being checked
            - status: License status (e.g., "active", "expired", "none", "trial")
    """
    status = get_license_status(tool_input.username, tool_input.software_name)
    
    return {
        "username": tool_input.username,
        "software_name": tool_input.software_name,
        "status": status,
    }