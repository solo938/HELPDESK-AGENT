import logging
from typing import List, Dict, Any
from helpdesk_agent.schemas.tool_inputs import SearchKBInput
from helpdesk_agent.tools.base import ToolResult, safe_execute
from helpdesk_agent.memory.cache import get_cached_kb_result, set_cached_kb_result

logger = logging.getLogger(__name__)


# Mock knowledge base for development
# In production, replace with actual vector database (Pinecone, Weaviate, etc.)
MOCK_KB = {
    "password policy": {
        "filename": "security_policies.md",
        "content": "Password Policy:\n- Minimum 12 characters\n- Must include uppercase, lowercase, number, and special character\n- Must be changed every 90 days\n- Cannot reuse last 5 passwords"
    },
    "vpn setup": {
        "filename": "vpn_setup_guide.md", 
        "content": "VPN Setup Instructions:\n1. Download Cisco AnyConnect from internal portal\n2. Install the client\n3. Enter vpn.company.com as server address\n4. Use your corporate credentials\n5. Complete MFA verification"
    },
    "software installation": {
        "filename": "software_installation.md",
        "content": "Software Installation:\n- Approved software can be installed via Company Portal\n- Admin rights required for certain applications\n- Submit IT ticket for enterprise software requests"
    }
}


def perform_search(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """
    Perform actual knowledge base search.
    In production, this would query a vector database.
    
    Args:
        query: Search query string
        top_k: Number of results to return
    
    Returns:
        List of document dicts with filename and content
    """
    results = []
    query_lower = query.lower()
    
    # Simple keyword matching for mock KB
    for keyword, doc in MOCK_KB.items():
        if keyword in query_lower:
            results.append({
                "filename": doc["filename"],
                "content": doc["content"]
            })
            if len(results) >= top_k:
                break
    
    # If no matches, return default fallback
    if not results:
        results.append({
            "filename": "general_help.md",
            "content": "For general assistance, please contact IT support or submit a ticket through the helpdesk portal."
        })
    
    return results


@safe_execute
def search_kb(username: str, tool_input: SearchKBInput) -> ToolResult:
    """
    Search the knowledge base for relevant documents.
    
    Features:
    - Redis caching for repeated queries (5 minute TTL)
    - Graceful degradation if Redis unavailable
    - Keyword matching (mock) - replace with vector search in production
    
    Args:
        username: User making the request
        tool_input: SearchKBInput with query and top_k
    
    Returns:
        ToolResult with search results in data["results"]
    """
    query = tool_input.query
    top_k = tool_input.top_k
    
    logger.info(f"Searching KB for user {username}: {query[:50]}...")
    
    # Step 1: Check cache first (optimization, not a hard dependency)
    cached_results = get_cached_kb_result(query)
    if cached_results is not None:
        logger.info(f"Cache hit for query: {query[:50]}...")
        return ToolResult(
            success=True,
            tool_name="search_kb",
            data={"results": cached_results[:top_k]},
            error=None
        )
    
    logger.debug(f"Cache miss for query: {query[:50]}...")
    
    # Step 2: Perform actual search
    try:
        results = perform_search(query, top_k)
        
        # Step 3: Cache results for future queries (5 minute TTL)
        set_cached_kb_result(query, results, ttl=300)
        
        return ToolResult(
            success=True,
            tool_name="search_kb",
            data={"results": results},
            error=None
        )
        
    except Exception as e:
        logger.error(f"KB search failed: {str(e)}", exc_info=True)
        return ToolResult(
            success=False,
            tool_name="search_kb",
            data={},
            error=f"Knowledge base search failed: {str(e)}"
        )


# Optional: Function to invalidate cache when KB is updated
def invalidate_kb_cache(query: str = None) -> None:
    """
    Invalidate knowledge base cache.
    
    Args:
        query: Specific query to invalidate, or None for all
    """
    from helpdesk_agent.memory.cache import clear_cache_for_query, clear_all_kb_cache
    
    if query:
        clear_cache_for_query(query)
        logger.info(f"Invalidated cache for query: {query}")
    else:
        clear_all_kb_cache()
        logger.info("Invalidated all KB cache")