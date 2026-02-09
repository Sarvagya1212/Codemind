# backend/app/services/mmr_service.py
"""
Max Marginal Relevance (MMR) for Context Compression

MMR selects diverse, relevant chunks while minimizing redundancy.
This drastically reduces token count and improves generation speed.

Formula:
MMR = argmax[λ * Sim(chunk, query) - (1 - λ) * max(Sim(chunk, selected))]

Where:
- λ controls relevance vs diversity tradeoff (typically 0.5-0.7)
- Higher λ = more relevance, less diversity
- Lower λ = more diversity, less relevance
"""

import numpy as np
from typing import List, Dict, Optional
from sklearn.metrics.pairwise import cosine_similarity


def mmr_rerank(
    chunks: List[Dict],
    query_embedding: Optional[List[float]] = None,
    top_k: int = 5,
    lambda_param: float = 0.6
) -> List[Dict]:
    """
    Apply Max Marginal Relevance to select diverse, non-redundant chunks.
    
    Args:
        chunks: List of chunks with 'content' and optionally 'embedding'
        query_embedding: Query embedding (optional)
        top_k: Number of final chunks to return
        lambda_param: Relevance vs diversity (0.5 = balanced, 0.7 = more relevance)
    
    Returns:
        Top-k chunks selected by MMR
    """
    if not chunks or len(chunks) <= top_k:
        return chunks[:top_k]
    
    # Extract embeddings (use similarity scores as proxy if embeddings not available)
    chunk_embeddings = []
    has_embeddings = 'embedding' in chunks[0] if chunks else False
    
    if not has_embeddings:
        # Fallback: use text-based similarity
        return _mmr_text_based(chunks, top_k, lambda_param)
    
    # Get embeddings
    for chunk in chunks:
        emb = chunk.get('embedding')
        if emb is not None:
            chunk_embeddings.append(emb)
        else:
            # Skip chunks without embeddings
            continue
    
    if len(chunk_embeddings) == 0:
        return chunks[:top_k]
    
    chunk_embeddings = np.array(chunk_embeddings)
    
    # Calculate query-chunk similarities (if query embedding provided)
    if query_embedding is not None:
        query_emb = np.array(query_embedding).reshape(1, -1)
        query_similarities = cosine_similarity(query_emb, chunk_embeddings)[0]
    else:
        # Use existing similarity scores
        query_similarities = np.array([c.get('similarity', 1.0) for c in chunks])
    
    # MMR algorithm
    selected_indices = []
    remaining_indices = list(range(len(chunks)))
    
    # Select first chunk (highest similarity to query)
    first_idx = int(np.argmax(query_similarities))
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    # Select remaining chunks using MMR
    while len(selected_indices) < top_k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            # Relevance to query
            relevance = query_similarities[idx]
            
            # Max similarity to already selected chunks
            if len(selected_indices) > 0:
                selected_embs = chunk_embeddings[selected_indices]
                candidate_emb = chunk_embeddings[idx].reshape(1, -1)
                redundancy = np.max(cosine_similarity(candidate_emb, selected_embs))
            else:
                redundancy = 0
            
            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * redundancy
            mmr_scores.append((idx, mmr_score))
        
        # Select chunk with highest MMR score
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    # Return selected chunks in order of selection
    return [chunks[i] for i in selected_indices]


def _mmr_text_based(chunks: List[Dict], top_k: int, lambda_param: float) -> List[Dict]:
    """
    Fallback MMR using text-based similarity when embeddings aren't available.
    Uses Jaccard similarity on word sets.
    """
    if len(chunks) <= top_k:
        return chunks[:top_k]
    
    # Tokenize chunks
    chunk_words = []
    for chunk in chunks:
        content = chunk.get('content', '')
        words = set(content.lower().split())
        chunk_words.append(words)
    
    # Get initial similarities
    similarities = [chunk.get('similarity', 1.0) for chunk in chunks]
    
    selected_indices = []
    remaining_indices = list(range(len(chunks)))
    
    # Select first chunk
    first_idx = int(np.argmax(similarities))
    selected_indices.append(first_idx)
    remaining_indices.remove(first_idx)
    
    # Select remaining using MMR with Jaccard similarity
    while len(selected_indices) < top_k and remaining_indices:
        mmr_scores = []
        
        for idx in remaining_indices:
            relevance = similarities[idx]
            
            # Calculate redundancy using Jaccard similarity
            if len(selected_indices) > 0:
                max_redundancy = 0
                for sel_idx in selected_indices:
                    intersection = len(chunk_words[idx] & chunk_words[sel_idx])
                    union = len(chunk_words[idx] | chunk_words[sel_idx])
                    jaccard = intersection / union if union > 0 else 0
                    max_redundancy = max(max_redundancy, jaccard)
                redundancy = max_redundancy
            else:
                redundancy = 0
            
            mmr_score = lambda_param * relevance - (1 - lambda_param) * redundancy
            mmr_scores.append((idx, mmr_score))
        
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
    
    return [chunks[i] for i in selected_indices]


def compress_chunks_mmr(
    chunks: List[Dict],
    top_k: int = 5,
    lambda_param: float = 0.6
) -> List[Dict]:
    """
    Wrapper function for easy integration.
    
    Args:
        chunks: Chunks from retrieval (with 'content', 'similarity', optionally 'embedding')
        top_k: Target number of chunks
        lambda_param: MMR parameter (0.5-0.7 recommended)
    
    Returns:
        Compressed list of diverse chunks
    """
    if not chunks:
        return []
    
    return mmr_rerank(chunks, top_k=top_k, lambda_param=lambda_param)


# =============================================================================
# Token Counting Utilities
# =============================================================================

def estimate_token_count(text: str) -> int:
    """
    Estimate token count (rough approximation: 1 token ≈ 4 characters).
    For production, use tiktoken or model-specific tokenizer.
    """
    return len(text) // 4


def truncate_chunks_to_token_limit(
    chunks: List[Dict],
    max_tokens: int = 10000
) -> tuple[List[Dict], int]:
    """
    Truncate chunk list to fit within token budget.
    
    Returns:
        (truncated_chunks, actual_token_count)
    """
    if not chunks:
        return [], 0
    
    selected_chunks = []
    total_tokens = 0
    
    for chunk in chunks:
        content = chunk.get('content', '')
        chunk_tokens = estimate_token_count(content)
        
        if total_tokens + chunk_tokens <= max_tokens:
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        else:
            # Stop if we'd exceed the limit
            break
    
    print(f"📊 Token budget: {total_tokens}/{max_tokens} tokens ({len(selected_chunks)}/{len(chunks)} chunks)")
    
    return selected_chunks, total_tokens


def compress_context(
    chunks: List[Dict],
    max_tokens: int = 10000,
    mmr_top_k: int = 8,
    use_mmr: bool = True
) -> tuple[List[Dict], Dict]:
    """
    Full context compression pipeline:
    1. MMR to remove redundancy
    2. Token limit enforcement
    
    Args:
        chunks: Initial retrieval results
        max_tokens: Hard token limit
        mmr_top_k: How many chunks to keep after MMR
        use_mmr: Whether to apply MMR (recommended)
    
    Returns:
        (compressed_chunks, metadata)
    """
    original_count = len(chunks)
    
    # Step 1: MMR compression
    if use_mmr and len(chunks) > mmr_top_k:
        chunks = compress_chunks_mmr(chunks, top_k=mmr_top_k, lambda_param=0.6)
        print(f"✂️  MMR: {original_count} → {len(chunks)} chunks")
    
    # Step 2: Token limit enforcement
    compressed, token_count = truncate_chunks_to_token_limit(chunks, max_tokens)
    
    metadata = {
        "original_chunks": original_count,
        "after_mmr": len(chunks),
        "final_chunks": len(compressed),
        "tokens_used": token_count,
        "tokens_limit": max_tokens,
        "compression_ratio": len(compressed) / original_count if original_count > 0 else 1.0
    }
    
    return compressed, metadata
