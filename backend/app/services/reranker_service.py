# backend/app/services/reranker_service.py
"""
Cross-Encoder Reranking Service

Uses a cross-encoder model to rerank retrieved code chunks for improved precision.
Cross-encoders jointly encode query+document pairs, providing more accurate 
relevance scores than bi-encoder similarity alone.

Model: ms-marco-MiniLM-L-6-v2 (22M params, optimized for reranking)
"""

import os
from typing import List, Dict, Optional, Tuple
from functools import lru_cache

# Lazy load to avoid startup overhead
_reranker_instance = None


def get_reranker():
    """
    Get or create reranker instance (singleton with lazy loading).
    
    Uses sentence-transformers CrossEncoder for efficient reranking.
    Falls back to no-op if model loading fails.
    """
    global _reranker_instance
    
    if _reranker_instance is not None:
        return _reranker_instance
    
    try:
        from sentence_transformers import CrossEncoder
        
        # Model options (ordered by speed):
        # - ms-marco-MiniLM-L-6-v2: Fastest, good quality (22M params)
        # - ms-marco-MiniLM-L-12-v2: Better quality, slower (33M params)
        # - cross-encoder/ms-marco-electra-base: Best quality, slowest (110M params)
        model_name = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        print(f"🔄 Loading cross-encoder reranker: {model_name}")
        _reranker_instance = CrossEncoder(model_name, max_length=512)
        print(f"✅ Cross-encoder reranker loaded successfully")
        
        return _reranker_instance
        
    except ImportError:
        print("⚠️  sentence-transformers not installed. Reranking disabled.")
        print("   Install with: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"⚠️  Failed to load reranker model: {e}")
        return None


def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_k: int = 5,
    return_scores: bool = True
) -> List[Dict]:
    """
    Rerank code chunks using cross-encoder for improved relevance.
    
    Args:
        query: The user's search query
        chunks: List of chunks from initial retrieval (each has 'content' key)
        top_k: Number of top results to return after reranking
        return_scores: If True, add 'rerank_score' to each chunk
    
    Returns:
        List of reranked chunks (top_k results)
    """
    if not chunks:
        return []
    
    reranker = get_reranker()
    
    if reranker is None:
        # Fallback: return original order (no reranking)
        print("⚠️  Reranker not available, using original ranking")
        return chunks[:top_k]
    
    try:
        # Prepare query-document pairs for cross-encoder
        # Format: [(query, doc1), (query, doc2), ...]
        pairs = []
        for chunk in chunks:
            # Use content for reranking, truncate if too long
            content = chunk.get('content', '')
            # Truncate content to avoid exceeding model's max length
            # Leave room for query (~100 tokens) + special tokens
            max_content_len = 400  # chars, conservative estimate
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."
            
            pairs.append((query, content))
        
        print(f"🔄 Reranking {len(chunks)} chunks with cross-encoder...")
        
        # Get reranking scores
        scores = reranker.predict(pairs)
        
        # Add scores to chunks and sort
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_copy = chunk.copy()
            if return_scores:
                chunk_copy['rerank_score'] = float(scores[i])
                chunk_copy['original_rank'] = i + 1
            scored_chunks.append((float(scores[i]), chunk_copy))
        
        # Sort by rerank score (descending)
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Extract chunks and update similarity with rerank score
        reranked = []
        for rank, (score, chunk) in enumerate(scored_chunks[:top_k], 1):
            # Normalize score to 0-1 range (cross-encoder scores can be negative)
            # Use sigmoid-like normalization
            normalized_score = 1 / (1 + pow(2.718, -score))
            
            chunk['rerank_score'] = score
            chunk['rerank_normalized'] = normalized_score
            chunk['final_rank'] = rank
            
            # Optionally blend with original similarity
            original_sim = chunk.get('similarity', 0.5)
            # 70% rerank, 30% original (can be tuned)
            chunk['blended_score'] = 0.7 * normalized_score + 0.3 * original_sim
            
            reranked.append(chunk)
            print(f"   [{rank}] score={score:.3f} → {normalized_score:.3f} | {chunk.get('metadata', {}).get('file_path', 'unknown')[:40]}")
        
        print(f"✅ Reranking complete. Top {len(reranked)} results selected.")
        return reranked
        
    except Exception as e:
        print(f"❌ Reranking failed: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to original order
        return chunks[:top_k]


def is_reranker_available() -> bool:
    """Check if reranker is available without loading it."""
    try:
        from sentence_transformers import CrossEncoder
        return True
    except ImportError:
        return False


# Preload hint for faster first query (optional)
def preload_reranker():
    """Preload the reranker model in background."""
    get_reranker()
