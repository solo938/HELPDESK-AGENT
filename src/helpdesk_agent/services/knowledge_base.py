# services/knowledge_base.py

import pathlib
import re
from typing import List, Dict, Set

KB_DIR = pathlib.Path("data/kb_documents")


def load_kb_documents() -> List[Dict[str, str]]:
    """Load all .md files from KB_DIR and return as list of dicts with filename and content."""
    documents = []

    if not KB_DIR.exists():
        return documents
    
    for file_path in KB_DIR.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            documents.append({
                "filename": file_path.name,
                "content": content
            })
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    return documents


def tokenize(text: str) -> Set[str]:
    """Convert text to lowercase and split into words using regex. Returns a set of unique tokens."""
    tokens = re.findall(r'\b\w+\b', text.lower())
    return set(tokens)


def search_kb(query: str, top_k: int = 3) -> List[Dict[str, object]]:
    """
    Search the knowledge base for documents matching the query using Jaccard similarity.
    
    Args:
        query: Search query string
        top_k: Number of top results to return
    
    Returns:
        List of dicts with keys: filename, content, score
    """
    # Load all documents
    documents = load_kb_documents()
    
    if not documents:
        return []
    
    # Tokenize the query
    query_tokens = tokenize(query)
    
    if not query_tokens:
        return []
    
    # Calculate Jaccard similarity scores for each document
    results = []
    for doc in documents:
        # Tokenize document content
        doc_tokens = tokenize(doc["content"])
        
        # Jaccard similarity = intersection / union
        intersection = query_tokens & doc_tokens
        union = query_tokens | doc_tokens
        union_score = len(union)
        
        # Calculate Jaccard score (normalized for document length)
        score = len(intersection) / union_score if union_score > 0 else 0
        
        # Only include documents with at least one match
        if score > 0:
            results.append({
                "filename": doc["filename"],
                "content": doc["content"],
                "score": score
            })
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top_k results
    return results[:top_k]