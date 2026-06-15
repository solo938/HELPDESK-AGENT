# tools/reset_password_tool.py

from helpdesk_agent.tools.base import safe_execute
from helpdesk_agent.schemas.tool_inputs import ResetPasswordInput
from helpdesk_agent.services.user_db import reset_user_password, get_user
import hashlib
import secrets
import string


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure random password.
    
    Includes uppercase, lowercase, digits, and avoids ambiguous characters.
    """
    # Avoid ambiguous characters: 0O, 1l, etc.
    alphabet = string.ascii_letters + string.digits
    # Remove ambiguous characters for better user experience
    ambiguous = '0O1l'
    alphabet = ''.join(c for c in alphabet if c not in ambiguous)
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@safe_execute(required_permission="reset_password")
def reset_password(tool_input: ResetPasswordInput) -> dict:
    """
    Reset a user's password to a temporary random value.
    
    This generates a secure temporary password, hashes it (simulated with SHA256),
    updates the user database, and returns the temporary password so it can be
    displayed to the user or sent via email.
    
    Args:
        tool_input: ResetPasswordInput containing username to reset
    
    Returns:
        dict with keys:
            - username: The user whose password was reset
            - status: Confirmation message
            - temporary_password: The new temporary password (plain text)
    
    Raises:
        ValueError: If user is not found in the database
    """
    
    # Validate user exists
    user = get_user(tool_input.username)
    if user is None:
        raise ValueError(f"User '{tool_input.username}' not found in the database")
    
    # Generate temporary password
    temporary_password = generate_secure_password()
    
    # Create hash (in production: use bcrypt, argon2, or PBKDF2)
    # This is a simulation for the helpdesk agent demonstration
    password_hash = hashlib.sha256(temporary_password.encode()).hexdigest()
    
    # Update database
    reset_user_password(tool_input.username, password_hash)
    
    # Return the temporary password so the agent can communicate it to the user
    return {
        "username": tool_input.username,
        "status": "password reset successful",
        "temporary_password": temporary_password
    }