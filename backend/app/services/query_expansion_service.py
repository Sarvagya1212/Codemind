# backend/app/services/query_expansion_service.py
"""
Query Expansion Service

Uses a small, fast LLM to expand queries with related terms.
This boosts recall without changing embeddings.

Example:
    Input: "Where is auth handled?"
    Expanded: ["authentication", "security", "jwt filter", "Spring Security", "auth middleware"]
    
Then search with BOTH original + expanded terms for better coverage.
"""

from typing import List, Optional
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os


# Use fastest model for expansion (speed > quality)
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "qwen2.5-coder:3b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_expansion_llm():
    """Get LLM for query expansion (fast, small model)."""
    return ChatOllama(
        model=EXPANSION_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,  # Some creativity for synonyms
        num_predict=100,  # Short output - just keywords
        keep_alive="5m"
    )


EXPANSION_PROMPT = ChatPromptTemplate.from_template("""You are a search query expander for code search.

Given a user query, generate 5-8 related technical terms, synonyms, or alternative phrasings that would help find relevant code.

Rules:
- Output ONLY comma-separated keywords/phrases
- Include technical synonyms
- Include common abbreviations
- Include framework-specific terms
- Keep it concise
- NO explanations, ONLY keywords

Examples:

Query: "Where is auth handled?"
Output: authentication, security config, jwt filter, spring security, auth middleware, login handler, authorization

Query: "How does the database connection work?"
Output: database, connection pool, jdbc, datasource, SQL, repository, orm, hibernate, jpa

Query: "Where are API endpoints defined?"
Output: rest controller, api routes, endpoints, request mapping, http handlers, route config, controller

Now expand this query:

Query: {query}
Output:""")


def expand_query(query: str, max_terms: int = 8) -> List[str]:
    """
    Expand query with related terms using LLM.
    
    Args:
        query: Original user query
        max_terms: Maximum number of expansion terms
    
    Returns:
        List of expansion terms (excluding original query)
    """
    try:
        llm = get_expansion_llm()
        chain = EXPANSION_PROMPT | llm | StrOutputParser()
        
        # Generate expansions
        result = chain.invoke({"query": query})
        
        # Parse comma-separated terms
        expansions = [term.strip() for term in result.split(',')]
        expansions = [term for term in expansions if term and len(term) > 2]
        
        # Remove duplicates and limit
        expansions = list(dict.fromkeys(expansions))[:max_terms]
        
        print(f"🔍 Query expansion: '{query}' → {expansions}")
        return expansions
        
    except Exception as e:
        print(f"⚠️  Query expansion failed: {e}")
        return []


def expand_and_merge_query(query: str, max_terms: int = 5) -> str:
    """
    Expand query and merge with original for enhanced search.
    
    Args:
        query: Original query
        max_terms: Max expansion terms to add
    
    Returns:
        Enhanced query string
    """
    expansions = expand_query(query, max_terms=max_terms)
    
    if not expansions:
        return query
    
    # Merge: original query + top expansion terms
    enhanced = f"{query} {' '.join(expansions[:max_terms])}"
    return enhanced


def multi_query_search(
    query: str,
    search_func,
    use_expansion: bool = True,
    **search_kwargs
) -> List:
    """
    Perform multi-query search with query expansion.
    
    Searches with:
    1. Original query
    2. Each expanded term individually
    
    Then merges and deduplicates results.
    
    Args:
        query: Original query
        search_func: Search function to call (e.g., hybrid_search)
        use_expansion: Whether to use query expansion
        **search_kwargs: Additional kwargs for search_func
    
    Returns:
        Merged and deduplicated results
    """
    if not use_expansion:
        return search_func(query=query, **search_kwargs)
    
    # Get expansions
    expansions = expand_query(query, max_terms=3)
    
    # Search with original
    print(f"🔍 Searching with original: '{query}'")
    results_original = search_func(query=query, **search_kwargs)
    
    # Search with each expansion
    all_results = list(results_original)
    seen_ids = {r.get('id') for r in results_original}
    
    for expansion in expansions[:2]:  # Use top 2 expansions
        print(f"🔍 Searching with expansion: '{expansion}'")
        results_exp = search_func(query=expansion, **search_kwargs)
        
        # Add new results
        for r in results_exp:
            if r.get('id') not in seen_ids:
                all_results.append(r)
                seen_ids.add(r.get('id'))
    
    print(f"📊 Multi-query: {len(results_original)} original + {len(all_results) - len(results_original)} from expansions = {len(all_results)} total")
    
    # Re-sort by score
    all_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    
    return all_results
