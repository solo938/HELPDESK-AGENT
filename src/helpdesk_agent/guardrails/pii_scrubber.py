import re
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# PII patterns dictionary mapping type names to regex patterns
PII_PATTERNS: Dict[str, str] = {
    "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "PHONE": r"\b\d{10}\b",  # US/Canada 10-digit phone numbers
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",  # 13-16 digit credit card numbers
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",  # US Social Security Number format
    "IP_ADDRESS": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",  # IPv4 addresses
    "USERNAME": r"@[a-zA-Z0-9_]{3,20}\b",  # Social media/mentions style usernames
    "API_KEY": r"[a-zA-Z0-9]{32,40}\b",  # Common API key patterns
}


def scrub_pii(text: str, patterns: Dict[str, str] = None) -> str:
    """
    Scrub personally identifiable information (PII) from text.
    
    Replaces all detected PII patterns with redaction markers like [REDACTED_EMAIL].
    
    Args:
        text: The input text to scrub
        patterns: Optional custom patterns dict (uses PII_PATTERNS if not provided)
    
    Returns:
        Scrubber text with PII replaced by redaction markers
    
    Examples:
        >>> scrub_pii("Email me at john.doe@example.com or call 5551234567")
        'Email me at [REDACTED_EMAIL] or call [REDACTED_PHONE]'
        
        >>> scrub_pii("SSN: 123-45-6789 and IP: 192.168.1.1")
        'SSN: [REDACTED_SSN] and IP: [REDACTED_IP_ADDRESS]'
    """
    if not text or not isinstance(text, str):
        logger.warning(f"Invalid input to scrub_pii: {type(text)}")
        return text if text else ""
    
    original_text = text
    patterns_to_use = patterns if patterns is not None else PII_PATTERNS
    
    redacted_count = 0
    scrubbed_text = text
    
    for pii_type, pattern in patterns_to_use.items():
        try:
            # Find all matches before replacement for logging
            matches = re.findall(pattern, scrubbed_text)
            if matches:
                redacted_count += len(matches)
                logger.debug(f"Redacting {len(matches)} {pii_type} pattern(s)")
            
            # Replace with redaction marker
            scrubbed_text = re.sub(pattern, f"[REDACTED_{pii_type}]", scrubbed_text)
            
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pii_type}: {pattern} - {str(e)}")
            continue
    
    if redacted_count > 0:
        logger.info(f"Scrubbed {redacted_count} PII instances from text (original length: {len(original_text)})")
    
    return scrubbed_text


def contains_pii(text: str, patterns: Dict[str, str] = None) -> bool:
    """
    Check if text contains any PII patterns.
    
    Args:
        text: The input text to check
        patterns: Optional custom patterns dict (uses PII_PATTERNS if not provided)
    
    Returns:
        True if any PII pattern matches, False otherwise
    
    Examples:
        >>> contains_pii("My email is user@example.com")
        True
        
        >>> contains_pii("Just a normal sentence with no PII")
        False
    """
    if not text or not isinstance(text, str):
        return False
    
    patterns_to_use = patterns if patterns is not None else PII_PATTERNS
    
    for pii_type, pattern in patterns_to_use.items():
        try:
            if re.search(pattern, text):
                logger.debug(f"Found {pii_type} pattern in text")
                return True
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pii_type}: {pattern} - {str(e)}")
            continue
    
    return False


def get_pii_types(text: str, patterns: Dict[str, str] = None) -> List[str]:
    """
    Get list of PII types found in text without modifying it.
    
    Args:
        text: The input text to analyze
        patterns: Optional custom patterns dict (uses PII_PATTERNS if not provided)
    
    Returns:
        List of PII type names found in the text
    
    Examples:
        >>> get_pii_types("Email: user@test.com, Phone: 5551234567")
        ['EMAIL', 'PHONE']
    """
    if not text or not isinstance(text, str):
        return []
    
    found_types = []
    patterns_to_use = patterns if patterns is not None else PII_PATTERNS
    
    for pii_type, pattern in patterns_to_use.items():
        try:
            if re.search(pattern, text):
                found_types.append(pii_type)
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pii_type}: {pattern} - {str(e)}")
            continue
    
    return found_types


def scrub_pii_with_mapping(text: str, patterns: Dict[str, str] = None) -> Tuple[str, Dict[str, List[str]]]:
    """
    Scrub PII and return mapping of redacted values.
    
    This is useful for logging or audit trails where you need to know
    what was redacted without storing the actual PII.
    
    Args:
        text: The input text to scrub
        patterns: Optional custom patterns dict (uses PII_PATTERNS if not provided)
    
    Returns:
        Tuple of (scrubbed_text, redacted_mapping) where redacted_mapping maps
        redaction markers to lists of original values
    
    Example:
        >>> scrubbed, mapping = scrub_pii_with_mapping("Email user@test.com")
        >>> scrubbed
        'Email [REDACTED_EMAIL]'
        >>> mapping
        {'[REDACTED_EMAIL]': ['user@test.com']}
    """
    if not text or not isinstance(text, str):
        return text if text else "", {}
    
    redacted_mapping = {}
    scrubbed_text = text
    patterns_to_use = patterns if patterns is not None else PII_PATTERNS
    
    for pii_type, pattern in patterns_to_use.items():
        try:
            # Find all matches
            matches = re.findall(pattern, scrubbed_text)
            
            if matches:
                redaction_marker = f"[REDACTED_{pii_type}]"
                
                # Store mapping (handle multiple matches)
                if redaction_marker not in redacted_mapping:
                    redacted_mapping[redaction_marker] = []
                redacted_mapping[redaction_marker].extend(matches)
                
                # Perform replacement
                scrubbed_text = re.sub(pattern, redaction_marker, scrubbed_text)
                
        except re.error as e:
            logger.error(f"Invalid regex pattern for {pii_type}: {pattern} - {str(e)}")
            continue
    
    return scrubbed_text, redacted_mapping


# Convenience function for guardrail integration
def apply_pii_guardrail(state_or_message: str) -> str:
    """
    Apply PII scrubbing as a guardrail to agent inputs/outputs.
    
    This is designed to be used as a pre/post-processing step
    in the agent graph to ensure PII never reaches the LLM or logs.
    
    Args:
        state_or_message: String content to scrub
    
    Returns:
        Scrubber string safe for LLM processing
    
    Example:
        >>> # In graph node:
        >>> user_message = apply_pii_guardrail(raw_user_input)
    """
    if not state_or_message:
        return state_or_message
    
    # Scrub the message
    scrubbed = scrub_pii(state_or_message)
    
    # Log if PII was found (without exposing the actual PII)
    if scrubbed != state_or_message:
        logger.info("PII detected and redacted from message")
    
    return scrubbed