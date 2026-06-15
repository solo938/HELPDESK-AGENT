import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_action_grounding(message: str, target_username: str, requester_id: str) -> bool:
    """
    Validate that a target username is grounded in the original user message.
    
    Self-targeted actions (target == requester) are always grounded since the
    username is injected by the system, not extracted by LLM. For other targets,
    the username must appear in the message to prevent hallucination.
    
    Args:
        message: Original user message
        target_username: Username the action targets (from LLM extraction)
        requester_id: ID of the user making the request (from state.user_id)
    
    Returns:
        True if grounded (self-targeted or username appears in message),
        False if LLM likely hallucinated a non-existent username
    
    Examples:
        >>> # Self-targeted - always grounded
        >>> validate_action_grounding("Reset my password", "alice", "alice")
        True
        
        >>> # Target appears in message - grounded
        >>> validate_action_grounding("Reset bob's password", "bob", "alice")
        True
        
        >>> # Target doesn't appear in message - hallucination
        >>> validate_action_grounding("Reset my password", "charlie", "alice")
        False
    """
    if not message or not target_username or not requester_id:
        logger.warning(f"Missing required params: message={bool(message)}, target={bool(target_username)}, requester={bool(requester_id)}")
        return False
    
    # Self-targeted action (requester is the target)
    if target_username == requester_id:
        logger.debug(f"Self-targeted action for {requester_id} - skipping grounding check")
        return True
    
    # Target username must appear in original message
    if target_username.lower() in message.lower():
        logger.debug(f"Found target '{target_username}' in message")
        return True
    
    # No grounding found - likely LLM hallucination
    logger.warning(
        f"Hallucination detected: target '{target_username}' not found in message '{message[:100]}...'"
    )
    return False


def validate_and_get_error_message(message: str, target_username: str, requester_id: str) -> Optional[str]:
    """
    Validate grounding and return an error message if validation fails.
    
    Args:
        message: Original user message
        target_username: Username the action targets
        requester_id: ID of the user making the request
    
    Returns:
        None if validation passes, otherwise an error message string
    """
    is_valid = validate_action_grounding(message, target_username, requester_id)
    
    if is_valid:
        return None
    
    return (
        f"I couldn't find '{target_username}' mentioned in your message. "
        f"Please specify the username clearly when requesting actions for other users. "
        f"To reset your own password, say 'my password' or 'reset my password'."
    )


def is_self_targeted_action(target_username: str, requester_id: str) -> bool:
    """Quick check if an action targets the requester themselves."""
    return target_username == requester_id