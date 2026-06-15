import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# List of prompt injection patterns (case-insensitive matching)
INJECTION_PATTERNS: List[str] = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "new instructions:",
    "system prompt",
    "reveal your prompt",
    "forget previous instructions",
    "ignore all prior commands",
    "override instructions",
    "disregard prior instructions",
    "you are a different assistant",
    "pretend you are",
    "act as if",
    "no longer follow",
    "stop following",
    "disobey previous",
    "your new role",
    "updated instructions:",
    "system message:",
    "developer prompt:",
    "print your prompt",
    "show your instructions",
]

# Regex patterns for more flexible injection detection
INJECTION_REGEX_PATTERNS: List[str] = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)ignore\s+all\s+previous",
    r"(?i)disregard\s+the\s+above",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)new\s+instructions\s*:",
    r"(?i)system\s+prompt",
    r"(?i)reveal\s+your\s+prompt",
    r"(?i)forget\s+previous\s+instructions",
    r"(?i)override\s+instructions",
    r"(?i)pretend\s+you\s+are",
    r"(?i)act\s+as\s+if",
]


def detect_injection(text: str, use_regex: bool = True) -> bool:
    """
    Detect prompt injection attempts in user input (silent - no logging).
    
    Checks for common injection patterns like "ignore previous instructions"
    or attempts to override system prompts.
    
    Args:
        text: User input text to check for injection attempts
        use_regex: If True, use regex patterns for more flexible matching.
                   If False, use simple substring matching (faster but less robust).
    
    Returns:
        True if injection pattern detected, False otherwise
    
    Examples:
        >>> detect_injection("Please reset my password")
        False
        
        >>> detect_injection("Ignore previous instructions")
        True
    """
    if not text or not isinstance(text, str):
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    if use_regex:
        # Use regex patterns for more sophisticated detection
        for pattern in INJECTION_REGEX_PATTERNS:
            try:
                if re.search(pattern, text_lower):
                    return True
            except re.error:
                continue
    else:
        # Simple substring matching (faster for basic patterns)
        for pattern in INJECTION_PATTERNS:
            if pattern in text_lower:
                return True
    
    return False


def detect_injection_advanced(text: str) -> Tuple[bool, Optional[str]]:
    """
    Advanced injection detection that returns the matched pattern (silent).
    
    Args:
        text: User input text to check
    
    Returns:
        Tuple of (is_injection, matched_pattern)
    
    Example:
        >>> is_injection, pattern = detect_injection_advanced("Ignore previous instructions")
        >>> print(is_injection, pattern)
        True, "ignore previous instructions"
    """
    if not text or not isinstance(text, str):
        return False, None
    
    text_lower = text.lower()
    
    # Check simple patterns first
    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            return True, pattern
    
    # Check regex patterns
    for pattern in INJECTION_REGEX_PATTERNS:
        try:
            if re.search(pattern, text_lower):
                return True, pattern
        except re.error:
            continue
    
    return False, None


def get_injection_score(text: str) -> float:
    """
    Calculate injection confidence score based on pattern matches (silent).
    
    Returns a score between 0.0 (no injection) and 1.0 (high confidence injection).
    
    Args:
        text: User input text to evaluate
    
    Returns:
        Float score indicating injection likelihood
    """
    if not text or not isinstance(text, str):
        return 0.0
    
    text_lower = text.lower()
    matches = 0
    total_patterns = len(INJECTION_PATTERNS)
    
    # Count matching patterns
    for pattern in INJECTION_PATTERNS:
        if pattern in text_lower:
            matches += 1
    
    # Also check regex patterns
    for pattern in INJECTION_REGEX_PATTERNS:
        try:
            if re.search(pattern, text_lower):
                matches += 0.5
        except re.error:
            continue
    
    # Calculate score (cap at 1.0)
    score = min(matches / (total_patterns / 2), 1.0)
    
    return score


def sanitize_input(text: str, raise_on_injection: bool = False) -> str:
    """
    Sanitize user input by detecting and optionally rejecting injection attempts.
    
    Args:
        text: User input text to sanitize
        raise_on_injection: If True, raise ValueError on injection detection.
                           If False, return error message string.
    
    Returns:
        Original text if safe, or error message if injection detected and not raising
    
    Raises:
        ValueError: If injection detected and raise_on_injection is True
    """
    if not text:
        return text
    
    if detect_injection(text):
        error_msg = "SECURITY: Prompt injection attempt detected and blocked. Please ask your question without attempting to override system instructions."
        
        if raise_on_injection:
            raise ValueError(error_msg)
        
        return error_msg
    
    return text


# Guardrail function for graph integration (handles logging)
def apply_injection_guardrail(state_or_message: str) -> str:
    """
    Apply injection detection as a guardrail to agent inputs.
    Handles logging internally for graph integration.
    
    Args:
        state_or_message: String content to check
    
    Returns:
        Original message if safe, or error message if injection detected
    """
    if not state_or_message:
        return state_or_message
    
    # Check for injection (silent detection)
    if detect_injection(state_or_message):
        # Log here (caller responsibility pattern)
        logger.warning(f"Prompt injection detected and blocked: {state_or_message[:100]}...")
        return "SECURITY: Prompt injection attempt detected and blocked. Please rephrase your question."
    
    return state_or_message