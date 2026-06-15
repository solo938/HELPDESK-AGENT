import json
import logging
from typing import List, Optional
from redis import RedisError
from helpdesk_agent.schemas.state import Message
from helpdesk_agent.memory.cache import redis_client

logger = logging.getLogger(__name__)


def _serialize_message(message: Message) -> dict:
    """Convert Message object to dict for storage."""
    return {
        "role": message.role,
        "content": message.content
    }


def _deserialize_message(data: dict) -> Message:
    """Convert dict back to Message object."""
    return Message(role=data["role"], content=data["content"])


def get_session_messages(session_id: str) -> List[Message]:
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        List of Message objects, empty if no history found
    """
    if not session_id:
        return []
    
    if not redis_client:
        logger.debug("Redis unavailable, returning empty history")
        return []
    
    try:
        cache_key = f"session:{session_id}"
        cached = redis_client.get(cache_key)
        
        if cached:
            messages_data = json.loads(cached)
            messages = [_deserialize_message(msg) for msg in messages_data]
            logger.debug(f"Loaded {len(messages)} messages for session {session_id}")
            return messages
        else:
            logger.debug(f"No history found for session {session_id}")
            return []
            
    except RedisError as e:
        logger.error(f"Redis error in get_session_messages: {e}")
        return []
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to deserialize session messages: {e}")
        return []


def save_session_messages(session_id: str, messages: List[Message], ttl: int = 3600) -> bool:
    """
    Save conversation history for a session.
    
    Args:
        session_id: Unique session identifier
        messages: List of Message objects to save
        ttl: Time to live in seconds (default 1 hour)
    
    Returns:
        True if saved successfully, False otherwise
    """
    if not session_id:
        return False
    
    if not redis_client:
        logger.debug("Redis unavailable, skipping session save")
        return False
    
    try:
        cache_key = f"session:{session_id}"
        messages_data = [_serialize_message(msg) for msg in messages]
        redis_client.set(cache_key, json.dumps(messages_data), ex=ttl)
        logger.debug(f"Saved {len(messages)} messages for session {session_id} (TTL: {ttl}s)")
        return True
        
    except RedisError as e:
        logger.error(f"Redis error in save_session_messages: {e}")
        return False
    except json.JSONEncodeError as e:
        logger.error(f"Failed to serialize session messages: {e}")
        return False


def append_to_session(session_id: str, message: Message, ttl: int = 3600) -> bool:
    """
    Append a single message to session history.
    
    Args:
        session_id: Unique session identifier
        message: Message to append
        ttl: Time to live in seconds
    
    Returns:
        True if appended successfully, False otherwise
    """
    if not session_id:
        return False
    
    current_messages = get_session_messages(session_id)
    current_messages.append(message)
    return save_session_messages(session_id, current_messages, ttl)


def clear_session(session_id: str) -> bool:
    """
    Clear conversation history for a session.
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        True if cleared successfully, False otherwise
    """
    if not session_id or not redis_client:
        return False
    
    try:
        cache_key = f"session:{session_id}"
        redis_client.delete(cache_key)
        logger.info(f"Cleared session history for {session_id}")
        return True
    except RedisError as e:
        logger.error(f"Failed to clear session: {e}")
        return False


def get_session_stats(session_id: str) -> dict:
    """
    Get statistics about a session.
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        Dictionary with session stats
    """
    messages = get_session_messages(session_id)
    
    return {
        "session_id": session_id,
        "message_count": len(messages),
        "user_messages": sum(1 for m in messages if m.role == "user"),
        "assistant_messages": sum(1 for m in messages if m.role == "assistant"),
        "has_history": len(messages) > 0
    }