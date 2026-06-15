from langchain_anthropic import ChatAnthropic
from helpdesk_agent.tools.search_kb import search_kb
from helpdesk_agent.schemas.tool_inputs import SearchKBInput
from helpdesk_agent.config.prompts.rag_agent_prompt import rag_prompt
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class RAGResponse(BaseModel):
    """Optional structured response for the RAG agent."""
    answer: str
    source_documents: List[str]
    found: bool
    error: Optional[str] = None


def answer_from_kb(query: str, username: str) -> dict:
    """
    Answer a question using RAG from the knowledge base.
    
    Args:
        query: User's question
        username: Username of the requester (used for permissions)
    
    Returns:
        dict with keys:
            - answer (str): The generated answer or error message
            - sources (list[str]): List of source document filenames
            - found (bool): Whether relevant documents were found in KB
    
    Examples:
        >>> result = answer_from_kb("How to reset VPN password?", "alice")
        >>> print(result["answer"])
        >>> print(result["sources"])
        >>> print(result["found"])
    """
    # Validate input
    if not query or not query.strip():
        logger.warning(f"Empty query received for user {username}")
        return {
            "answer": "I couldn't process your question as it appears to be empty. Please provide more details.",
            "sources": [],
            "found": False
        }
    
    # Step 1: Search knowledge base
    try:
        logger.info(f"Searching KB for user {username}: {query[:50]}...")
        result = search_kb(
            username=username, 
            tool_input=SearchKBInput(query=query.strip(), top_k=3)
        )
    except Exception as e:
        logger.error(f"KB search failed for user {username}: {str(e)}", exc_info=True)
        return {
            "answer": "I encountered an error while searching the knowledge base. Please try again later or contact support if the issue persists.",
            "sources": [],
            "found": False
        }
    
    # Step 2: Check if we found any relevant documents
    if not result.success:
        logger.warning(f"KB search unsuccessful for user {username}: {result.error}")
        return {
            "answer": "I couldn't access the knowledge base at this time. Please try again later.",
            "sources": [],
            "found": False
        }
    
    if not result.data or not result.data.get("results"):
        logger.info(f"No KB results found for query: {query[:50]}...")
        return {
            "answer": "I don't have information on this in my knowledge base. Please rephrase your question or contact support for assistance.",
            "sources": [],
            "found": False
        }
    
    # Step 3: Format retrieved chunks into context string
    context_parts = []
    filenames = []
    
    for idx, doc in enumerate(result.data["results"], 1):
        filename = doc.get("filename", "unknown")
        content = doc.get("content", "").strip()
        
        if not content:
            logger.warning(f"Empty content for document: {filename}")
            continue
            
        context_parts.append(f"<document source='{filename}'>\n{content}\n</document>")
        filenames.append(filename)
    
    # Handle case where all documents had empty content
    if not context_parts:
        logger.warning(f"All retrieved documents had empty content for query: {query[:50]}...")
        return {
            "answer": "I found some documents but they appear to be empty. Please try rephrasing your question.",
            "sources": list(set(filenames)),
            "found": False
        }
    
    context_string = "\n\n".join(context_parts)
    unique_sources = list(set(filenames))
    
    logger.info(f"Formatted context with {len(context_parts)} chunks from {len(unique_sources)} sources")
    
    # Step 4: Generate answer with LLM
    try:
        # Create LLM instance internally (not injected)
        llm = ChatAnthropic(
            model="claude-3-sonnet-20241022",
            temperature=0,  # Deterministic responses for consistency
            max_tokens=1000
        )
        
        chain = rag_prompt | llm
        response = chain.invoke({
            "context": context_string,
            "question": query
        })
        
        answer_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"Successfully generated RAG response for user {username} using sources: {unique_sources}")
        
    except Exception as e:
        logger.error(f"LLM generation failed for query '{query[:50]}...': {str(e)}", exc_info=True)
        
        # Check for specific error types
        error_msg = str(e).lower()
        if "credit balance" in error_msg:
            return {
                "answer": "The knowledge base service is temporarily unavailable due to billing issues. Please contact your system administrator.",
                "sources": unique_sources,
                "found": True  # We found docs, just couldn't generate response
            }
        elif "rate limit" in error_msg:
            return {
                "answer": "The service is currently experiencing high demand. Please wait a moment and try again.",
                "sources": unique_sources,
                "found": True
            }
        else:
            return {
                "answer": "I found relevant information but encountered an error generating a response. Please try again in a moment.",
                "sources": unique_sources,
                "found": True
            }
    
    # Step 5: Return final response
    return {
        "answer": answer_text,
        "sources": unique_sources,
        "found": True
    }


def answer_from_kb_structured(query: str, username: str) -> RAGResponse:
    """
    Same as answer_from_kb but returns a Pydantic model for type safety.
    
    Useful when integrating with other components that expect structured output.
    
    Args:
        query: User's question
        username: Username of the requester
    
    Returns:
        RAGResponse object with typed fields
    """
    result = answer_from_kb(query, username)
    
    return RAGResponse(
        answer=result["answer"],
        source_documents=result["sources"],
        found=result["found"],
        error=None if result["found"] else "No relevant documents found"
    )


# Optional: Async version for concurrent requests
async def answer_from_kb_async(query: str, username: str) -> dict:
    """
    Async version of answer_from_kb for concurrent processing.
    
    Args:
        query: User's question
        username: Username of the requester
    
    Returns:
        Same dict structure as answer_from_kb
    """
    import asyncio
    
    # Run sync function in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, 
        answer_from_kb, 
        query, 
        username
    )
    
    return result