import logging
from fastapi import APIRouter, Depends, HTTPException
from helpdesk_agent.schemas.api_models import ChatRequest, ChatResponse, ToolCallSummary
from helpdesk_agent.schemas.state import AgentState, Message
from helpdesk_agent.api.dependencies import get_graph, get_rate_limiter
from helpdesk_agent.observability.metrics import ROUTE_COUNTER

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    graph = Depends(get_graph),
    rate_limiter = Depends(get_rate_limiter)
):
    """
    Main chat endpoint for helpdesk agent.
    
    - Rate limits per user
    - Routes request to appropriate agent (RAG, Action, Escalation)
    - Returns response with metadata about what happened
    """
    # Step 1: Rate limit check
    if not rate_limiter.is_allowed(request.user_id):
        logger.warning(f"Rate limit exceeded for user {request.user_id}")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 requests per minute. Please try again later."
        )
    
    # Step 2: Construct AgentState
    state = AgentState(
        user_id=request.user_id,
        conversation_id=request.session_id,
        messages=[Message(role="user", content=request.message)],
        max_steps=10,
        step_count=0,
        escalated=False,
        current_route=None,
        final_response=None,
        tool_results=[]
    )
    
    logger.info(f"Processing chat request for user {request.user_id}, session {request.session_id}")
    
    # Step 3: Invoke graph
    try:
        result = graph.invoke(state)
        logger.info(f"Graph invocation completed for user {request.user_id}")
    except Exception as e:
        logger.error(f"Graph invocation failed for user {request.user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}"
        )
    
    # Step 4: Build tool_calls from result["tool_results"]
    tool_calls = []
    if result.get("tool_results"):
        for tool_result in result["tool_results"]:
            tool_calls.append(
                ToolCallSummary(
                    tool_name=tool_result.tool_name,
                    success=tool_result.success
                )
            )
    
    # Increment route counter for monitoring
    route = result.get("current_route")
    if route:
        ROUTE_COUNTER.labels(route=route).inc()
    
    # Step 5: Return ChatResponse
    return ChatResponse(
        session_id=request.session_id,
        response=result.get("final_response", "No response generated"),
        route_taken=route or "unknown",
        escalated=result.get("escalated", False),
        tool_calls=tool_calls
    )