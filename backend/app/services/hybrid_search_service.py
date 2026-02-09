# backend/app/services/hybrid_search_service.py
"""
Hybrid Search Service

Combines BM25 (keyword) + Dense (semantic) search using Reciprocal Rank Fusion (RRF).
This is the same pattern used by production search systems.

Flow:
1. BM25 retrieves top-k by keyword matching
2. Dense retrieves top-k by embedding similarity
3. RRF fuses both lists for final ranking

RRF Formula: score(d) = Σ 1 / (k + rank(d))
Where k is typically 60
"""

import os
import pickle
import hashlib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi
import re


# BM25 index cache directory
BM25_INDEX_DIR = Path(os.getenv("BM25_INDEX_DIR", "./bm25_indexes"))
BM25_INDEX_DIR.mkdir(exist_ok=True)


@dataclass
class SearchResult:
    """A single search result with metadata."""
    id: str
    content: str
    metadata: Dict
    score: float
    source: str  # "bm25", "dense", or "hybrid"
    bm25_rank: Optional[int] = None
    dense_rank: Optional[int] = None


class HybridSearchService:
    """
    Hybrid search combining BM25 + Dense vectors with RRF fusion.
    
    Usage:
        service = HybridSearchService(repo_id=1, db=session)
        results = service.search(query="authentication", top_k=10)
    """
    
    def __init__(self, repo_id: int, db=None):
        self.repo_id = repo_id
        self.db = db
        self.bm25_index = None
        self.corpus = []
        self.doc_ids = []
        self.doc_metadata = []
        
        # RRF constant (standard value is 60)
        self.rrf_k = 60
        
        # Load or build BM25 index
        self._load_or_build_index()
    
    def _get_index_path(self) -> Path:
        """Get path for cached BM25 index."""
        return BM25_INDEX_DIR / f"repo_{self.repo_id}_bm25.pkl"
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing."""
        # Simple tokenization: lowercase, split on non-alphanumeric
        text = text.lower()
        # Keep underscores for code identifiers
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
        # Filter very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        return tokens
    
    def _load_or_build_index(self):
        """Load existing BM25 index or build from database."""
        index_path = self._get_index_path()
        
        # Try to load cached index
        if index_path.exists():
            try:
                with open(index_path, 'rb') as f:
                    cache = pickle.load(f)
                    self.bm25_index = cache['bm25']
                    self.corpus = cache['corpus']
                    self.doc_ids = cache['doc_ids']
                    self.doc_metadata = cache['doc_metadata']
                print(f"✅ Loaded BM25 index for repo_{self.repo_id} ({len(self.corpus)} docs)")
                return
            except Exception as e:
                print(f"⚠️  Failed to load BM25 cache: {e}")
        
        # Build index from database
        self._build_index_from_db()
    
    def _build_index_from_db(self):
        """Build BM25 index from database chunks."""
        if self.db is None:
            print("⚠️  No database session provided, using empty index")
            return
        
        from app.models import CodeChunk
        
        print(f"🔨 Building BM25 index for repo_{self.repo_id}...")
        
        # Load all chunks for this repo
        chunks = self.db.query(CodeChunk).filter(
            CodeChunk.repo_id == self.repo_id
        ).all()
        
        if not chunks:
            print(f"⚠️  No chunks found for repo_{self.repo_id}")
            return
        
        self.corpus = []
        self.doc_ids = []
        self.doc_metadata = []
        tokenized_corpus = []
        
        for chunk in chunks:
            content = chunk.content or ""
            tokens = self._tokenize(content)
            
            if tokens:  # Skip empty documents
                tokenized_corpus.append(tokens)
                self.corpus.append(content)
                self.doc_ids.append(str(chunk.id))
                self.doc_metadata.append({
                    "file_path": chunk.file_path,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "file_id": chunk.file_id
                })
        
        if tokenized_corpus:
            self.bm25_index = BM25Okapi(tokenized_corpus)
            
            # Cache the index
            try:
                cache = {
                    'bm25': self.bm25_index,
                    'corpus': self.corpus,
                    'doc_ids': self.doc_ids,
                    'doc_metadata': self.doc_metadata
                }
                with open(self._get_index_path(), 'wb') as f:
                    pickle.dump(cache, f)
                print(f"✅ Built and cached BM25 index ({len(self.corpus)} docs)")
            except Exception as e:
                print(f"⚠️  Failed to cache BM25 index: {e}")
        else:
            print(f"⚠️  No valid documents for BM25 index")
    
    def rebuild_index(self):
        """Force rebuild of BM25 index."""
        index_path = self._get_index_path()
        if index_path.exists():
            index_path.unlink()
        self._build_index_from_db()
    
    def bm25_search(self, query: str, top_k: int = 50) -> List[SearchResult]:
        """Search using BM25 keyword matching."""
        if self.bm25_index is None or not self.corpus:
            return []
        
        tokens = self._tokenize(query)
        if not tokens:
            return []
        
        scores = self.bm25_index.get_scores(tokens)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for rank, idx in enumerate(top_indices, 1):
            if scores[idx] > 0:  # Only include non-zero scores
                results.append(SearchResult(
                    id=self.doc_ids[idx],
                    content=self.corpus[idx],
                    metadata=self.doc_metadata[idx],
                    score=float(scores[idx]),
                    source="bm25",
                    bm25_rank=rank
                ))
        
        return results
    
    def dense_search(self, query: str, top_k: int = 50) -> List[SearchResult]:
        """Search using dense embedding similarity (ChromaDB)."""
        from app.services.rag_service import search_similar_code
        
        chunks = search_similar_code(
            repo_id=self.repo_id,
            query=query,
            top_k=top_k,
            use_reranker=False,  # No reranking at this stage
            score_threshold=0.0  # Get all results
        )
        
        results = []
        for rank, chunk in enumerate(chunks, 1):
            results.append(SearchResult(
                id=chunk.get("id", ""),
                content=chunk.get("content", ""),
                metadata=chunk.get("metadata", {}),
                score=chunk.get("similarity", 0),
                source="dense",
                dense_rank=rank
            ))
        
        return results
    
    def reciprocal_rank_fusion(
        self,
        bm25_results: List[SearchResult],
        dense_results: List[SearchResult],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Fuse BM25 and dense results using Reciprocal Rank Fusion.
        
        RRF score = Σ 1 / (k + rank)
        
        This is a simple but powerful fusion method that:
        - Doesn't require score normalization
        - Works well with different scoring scales
        - Robust to outliers
        """
        # Create a map of doc_id -> RRF score
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, SearchResult] = {}
        
        # Add BM25 contributions
        for result in bm25_results:
            doc_id = result.id
            rrf_score = 1.0 / (self.rrf_k + result.bm25_rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
            
            if doc_id not in doc_map:
                doc_map[doc_id] = result
            else:
                # Merge ranks
                doc_map[doc_id].bm25_rank = result.bm25_rank
        
        # Add dense contributions
        for result in dense_results:
            doc_id = result.id
            rrf_score = 1.0 / (self.rrf_k + result.dense_rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
            
            if doc_id not in doc_map:
                doc_map[doc_id] = result
            else:
                doc_map[doc_id].dense_rank = result.dense_rank
        
        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Build final results
        results = []
        for doc_id in sorted_ids[:top_k]:
            result = doc_map[doc_id]
            result.score = rrf_scores[doc_id]
            result.source = "hybrid"
            results.append(result)
        
        return results
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
        retrieve_k: int = 50  # Candidates from each source
    ) -> List[SearchResult]:
        """
        Hybrid search combining BM25 + Dense with RRF fusion.
        
        Args:
            query: Search query
            top_k: Final number of results
            bm25_weight: Not used in RRF (kept for API compatibility)
            dense_weight: Not used in RRF (kept for API compatibility)
            retrieve_k: Number of candidates to retrieve from each source
        
        Returns:
            List of SearchResult with hybrid ranking
        """
        print(f"\n🔍 Hybrid Search: '{query[:50]}...'")
        
        # Stage 1: BM25 retrieval
        bm25_results = self.bm25_search(query, top_k=retrieve_k)
        print(f"   📗 BM25: {len(bm25_results)} results")
        
        # Stage 2: Dense retrieval
        dense_results = self.dense_search(query, top_k=retrieve_k)
        print(f"   📘 Dense: {len(dense_results)} results")
        
        # Stage 3: RRF fusion
        hybrid_results = self.reciprocal_rank_fusion(
            bm25_results=bm25_results,
            dense_results=dense_results,
            top_k=top_k
        )
        print(f"   🔀 Hybrid (RRF): {len(hybrid_results)} results")
        
        return hybrid_results
    
    def search_with_rerank(
        self,
        query: str,
        final_top_k: int = 8,
        retrieve_k: int = 50
    ) -> List[SearchResult]:
        """
        Full pipeline: Hybrid retrieval → Cross-encoder reranking.
        
        This is the recommended method for best quality.
        """
        from app.services.reranker_service import rerank_chunks
        
        # Stage 1-3: Hybrid retrieval
        hybrid_results = self.search(
            query=query,
            top_k=retrieve_k,  # Get more candidates for reranking
            retrieve_k=retrieve_k
        )
        
        # Stage 4: Cross-encoder reranking
        if hybrid_results:
            # Convert to format expected by reranker
            chunks = [
                {
                    "id": r.id,
                    "content": r.content,
                    "metadata": r.metadata,
                    "similarity": r.score
                }
                for r in hybrid_results
            ]
            
            print(f"   🎯 Reranking {len(chunks)} candidates...")
            reranked = rerank_chunks(
                query=query,
                chunks=chunks,
                top_k=final_top_k
            )
            
            # Convert back to SearchResult
            results = []
            for r in reranked:
                results.append(SearchResult(
                    id=r.get("id", ""),
                    content=r.get("content", ""),
                    metadata=r.get("metadata", {}),
                    score=r.get("rerank_score", r.get("similarity", 0)),
                    source="hybrid+rerank"
                ))
            
            return results
        
        return hybrid_results


# =============================================================================
# Convenience functions
# =============================================================================

_hybrid_services: Dict[int, HybridSearchService] = {}


def get_hybrid_service(repo_id: int, db=None) -> HybridSearchService:
    """Get or create a HybridSearchService for a repository."""
    if repo_id not in _hybrid_services:
        _hybrid_services[repo_id] = HybridSearchService(repo_id, db)
    return _hybrid_services[repo_id]


def hybrid_search(
    repo_id: int,
    query: str,
    top_k: int = 8,
    use_rerank: bool = True,
    db=None
) -> List[Dict]:
    """
    Main hybrid search function.
    
    Returns results in the same format as search_similar_code for compatibility.
    """
    service = get_hybrid_service(repo_id, db)
    
    if use_rerank:
        results = service.search_with_rerank(query, final_top_k=top_k)
    else:
        results = service.search(query, top_k=top_k)
    
    # Convert to dict format for compatibility
    return [
        {
            "id": r.id,
            "content": r.content,
            "metadata": r.metadata,
            "similarity": r.score,
            "source": r.source,
            "bm25_rank": r.bm25_rank,
            "dense_rank": r.dense_rank
        }
        for r in results
    ]


def rebuild_bm25_index(repo_id: int, db=None):
    """Rebuild BM25 index for a repository."""
    service = get_hybrid_service(repo_id, db)
    service.rebuild_index()