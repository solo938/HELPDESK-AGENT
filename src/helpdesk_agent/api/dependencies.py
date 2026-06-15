"""
FastAPI dependencies for shared resources and request handling.

This module provides singleton instances and dependency injection functions
for route handlers to access shared resources like the compiled LangGraph.
"""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status

from helpdesk_agent.graph.build_graph import build_helpdesk_graph
from helpdesk_agent.schemas.state import AgentState, Message

logger = logging.getLogger(__name__)

# ============================================================================
# Singleton: Compiled LangGraph instance
# ============================================================================
# Build the graph once when the module loads, not per request
_graph = None

def get_graph():
    """
    Dependency function that returns the singleton LangGraph instance.
    
    Usage:
        @app.post("/chat")
        async def chat(request: ChatRequest, graph=Depends(get_graph)):
            result = graph.invoke(state)
            return {"response": result["final_response"]}
    
    Returns:
        Compiled StateGraph instance
    """
    global _graph
    if _graph is None:
        logger.info("Building LangGraph instance (first request)")
        _graph = build_helpdesk_graph()
        logger.info("LangGraph built successfully")
    return _graph


# ============================================================================
# User ID extraction (placeholder for future auth)
# ============================================================================
def get_user_id(request: Request, body: Optional[dict] = None) -> str:
    """
    Extract user ID from request.
    
    This is a placeholder - in production, you'd extract from:
    - JWT token in Authorization header
    - Session cookie
    - API key
    - OAuth2 token
    
    For now, reads from:
    1. Request body's 'user_id' field
    2. Header 'X-User-ID' 
    3. Default to 'anonymous'
    
    Args:
        request: FastAPI Request object
        body: Parsed request body (optional, to avoid double parsing)
    
    Returns:
        User ID string
    """
    # Try header first (more secure for programmatic access)
    user_id = request.headers.get("X-User-ID")
    if user_id:
        logger.debug(f"User ID from header: {user_id}")
        return user_id
    
    # Try query parameter
    user_id = request.query_params.get("user_id")
    if user_id:
        logger.debug(f"User ID from query: {user_id}")
        return user_id
    
    # Try request body (for simple testing)
    if body and "user_id" in body:
        user_id = body["user_id"]
        logger.debug(f"User ID from body: {user_id}")
        return user_id
    
    # Default fallback
    logger.warning("No user ID found in request, using 'anonymous'")
    return "anonymous"


async def get_user_id_dependency(request: Request) -> str:
    """
    FastAPI dependency for extracting user ID.
    
    Usage:
        @app.post("/chat")
        async def chat(
            request: ChatRequest,
            user_id: str = Depends(get_user_id_dependency),
            graph=Depends(get_graph)
        ):
            state = AgentState(user_id=user_id, ...)
            ...
    
    Note: Since FastAPI doesn't allow body access in dependencies easily,
    this reads from headers/query only. For body access, use middleware
    or read from the request body in the route handler directly.
    """
    return get_user_id(request, body=None)


# ============================================================================
# Rate limiter dependency (if you want to inject instead of direct import)
# ============================================================================
from helpdesk_agent.reliability.rate_limiter import rate_limiter

def get_rate_limiter():
    """
    Dependency that returns the rate limiter singleton.
    
    Usage:
        @app.post("/chat")
        async def chat(rate_limiter=Depends(get_rate_limiter)):
            if not rate_limiter.is_allowed(user_id):
                raise HTTPException(status_code=429)
    """
    return rate_limiter


# ============================================================================
# Circuit breaker dependency
# ============================================================================
from helpdesk_agent.reliability.circuit_breaker import circuit_breaker

def get_circuit_breaker():
    """
    Dependency that returns the circuit breaker singleton.
    
    Usage:
        @app.get("/admin/circuit/{tool_name}")
        async def get_circuit_state(tool_name: str, cb=Depends(get_circuit_breaker)):
            return cb.get_state(tool_name)
    """
    return circuit_breaker


# ============================================================================
# Request context middleware helper (for PII scrubbing)
# ============================================================================
from helpdesk_agent.guardrails.pii_scrubber import scrub_pii

def sanitize_request_body(body: dict) -> dict:
    """
    Sanitize request body by scrubbing PII from string fields.
    
    Use this before logging or processing sensitive data.
    
    Args:
        body: Request body dictionary
    
    Returns:
        Sanitized copy of the body with PII redacted
    """
    if not body:
        return body
    
    sanitized = body.copy()
    for key, value in sanitized.items():
        if isinstance(value, str):
            sanitized[key] = scrub_pii(value)
    return sanitized


# ============================================================================
# Health check dependencies (for monitoring)
# ============================================================================
def get_health_status():
    """
    Return health status of all components.
    
    Usage:
        @app.get("/health")
        async def health(health=Depends(get_health_status)):
            return health
    """
    from helpdesk_agent.tools.registry import TOOL_REGISTRY
    
    # Check graph is built
    graph = get_graph()
    
    # Check tool registry
    tool_count = len(TOOL_REGISTRY)
    tool_names = list(TOOL_REGISTRY.keys())
    
    # Check circuit breaker status for all tools
    circuit_states = {}
    for tool_name in tool_names:
        circuit_states[tool_name] = circuit_breaker.get_state(tool_name)
    
    return {
        "status": "healthy" if graph else "unhealthy",
        "graph_built": graph is not None,
        "tool_count": tool_count,
        "tools": tool_names,
        "circuit_states": circuit_states,
        "rate_limiter": {
            "max_per_minute": rate_limiter.max_per_minute
        }
    }


# ============================================================================
# Convenience: Combined dependencies for chat endpoint
# ============================================================================
from fastapi import Depends
from typing import Tuple

async def get_chat_dependencies(
    request: Request,
) -> Tuple[AgentState, callable]:
    """
    Combined dependency that returns everything needed for chat endpoint.
    
    Returns:
        Tuple of (user_id, graph, rate_limiter)
    
    Usage:
        @app.post("/chat")
        async def chat(
            chat_request: ChatRequest,
            deps: Tuple = Depends(get_chat_dependencies)
        ):
            user_id, graph, rate_limiter = deps
            # ... use deps
    """
    user_id = await get_user_id_dependency(request)
    graph = get_graph()
    limiter = get_rate_limiter()
    return (user_id, graph, limiter)