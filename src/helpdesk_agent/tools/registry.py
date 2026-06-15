# tools/registry.py

from helpdesk_agent.tools.reset_password import reset_password
from helpdesk_agent.tools.check_license import check_license
from helpdesk_agent.tools.search_kb import search_kb  # FIXED: import tool-layer version
from helpdesk_agent.tools.create_ticket import create_ticket
from helpdesk_agent.schemas.tool_inputs import (
    ResetPasswordInput,
    CheckLicenseInput,
    SearchKBInput,
    CreateTicketInput
)


TOOL_REGISTRY = {
    "reset_password": {
        "function": reset_password,
        "input_schema": ResetPasswordInput,
        "description": "Reset a user's password to a temporary random value. Use this ONLY when a user explicitly requests a password reset or cannot access their account due to forgotten credentials. NOT for license issues, MFA problems, or general account lockouts from failed attempts.",
        "category": "user_management",
    },
    "check_license": {
        "function": check_license,
        "input_schema": CheckLicenseInput,
        "description": "Check the license status for a user's software. Returns active, expired, trial, or none.",
        "category": "licensing",
    },
    "search_kb": {
        "function": search_kb,
        "input_schema": SearchKBInput,
        "description": "Search the knowledge base for documentation, troubleshooting guides, and FAQs. Use this to find answers to user questions about software, policies, or common issues.",
        "category": "knowledge_base",
    },
    "create_ticket": {
        "function": create_ticket,
        "input_schema": CreateTicketInput,
        "description": "Create a new helpdesk ticket for issues that require human intervention, follow-up, or cannot be resolved immediately. This is the universal fallback for ANY issue the agent cannot resolve with other tools.",
        "category": "ticketing",
    },
}


def get_tool(tool_name: str):
    """Helper function to safely retrieve a tool from the registry."""
    return TOOL_REGISTRY.get(tool_name)


def list_available_tools() -> list:
    """Helper function to get all available tool names."""
    return list(TOOL_REGISTRY.keys())