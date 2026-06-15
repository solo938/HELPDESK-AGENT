from typing import Literal
import logging
from langgraph.graph import StateGraph, END

from helpdesk_agent.schemas.state import AgentState
from helpdesk_agent.graph.nodes import (
    router_node,
    rag_node,
    action_node,
    escalation_node,
    supervisor_node,
)

logger = logging.getLogger(__name__)


def route_after_router(state: AgentState) -> Literal["rag", "action", "escalation"]:
    """
    Determines which node to go to after routing.
    """
    if state.escalated:
        return "escalation"
    
    if state.current_route == "rag":
        return "rag"
    elif state.current_route == "action":
        return "action"
    else:
        return "escalation"


def build_helpdesk_graph():
    """
    Builds the complete helpdesk agent graph.
    Single-pass execution - ends after one processing cycle.
    """
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("router", router_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("action", action_node)
    workflow.add_node("escalation", escalation_node)
    
    # Define flow
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "router")
    
    # Conditional branching based on routing decision
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "rag": "rag",
            "action": "action",
            "escalation": "escalation"
        }
    )
    
    # All paths lead to END (single-pass execution)
    workflow.add_edge("rag", END)
    workflow.add_edge("action", END)
    workflow.add_edge("escalation", END)
    
    # Compile graph
    compiled_graph = workflow.compile()
    
    logger.info("Helpdesk graph compiled successfully")
    return compiled_graph