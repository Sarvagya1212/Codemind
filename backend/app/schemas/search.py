# backend/app/schemas/search.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class SearchMode(str, Enum):
    """Search mode types"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    REGEX = "regex"
    SYMBOL = "symbol"
    AUTO = "auto"  # Automatically detect


class MatchType(str, Enum):
    """How the result was matched"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    SYMBOL = "symbol"
    REGEX = "regex"
    FILENAME = "filename"


class SearchRequest(BaseModel):
    """Request for code search"""
    q: str = Field(..., description="Search query", min_length=1, max_length=1000)
    mode: SearchMode = Field(default=SearchMode.AUTO, description="Search mode")
    
    # Filters
    file: Optional[str] = Field(None, description="File path filter or glob pattern")
    lang: Optional[str] = Field(None, description="Programming language filter")
    branch: Optional[str] = Field(default="main", description="Branch to search")
    symbol_type: Optional[str] = Field(None, description="Symbol type filter")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Results per page")
    
    # Advanced options
    include_tests: bool = Field(default=True, description="Include test files")
    case_sensitive: bool = Field(default=False, description="Case sensitive search")
    
    class Config:
        schema_extra = {
            "example": {
                "q": "Where is the HTTP handler defined?",
                "mode": "hybrid",
                "lang": "python",
                "page": 1,
                "per_page": 20
            }
        }


class SearchResultItem(BaseModel):
    """Single search result"""
    # Identity
    chunk_id: Optional[str]  # Changed from int to str (it's a ChromaDB ID)
    file_id: int
    file_path: str
    
    # Content
    snippet: str = Field(..., description="Code snippet with context")
    highlighted_snippet: str = Field(..., description="Snippet with HTML highlights")
    
    # Position
    start_line: int
    end_line: int
    
    # Matching
    match_type: List[MatchType] = Field(..., description="How this result matched")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Overall relevance score")
    
    # Score breakdown
    semantic_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    keyword_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    symbol_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Metadata
    language: str
    symbol_name: Optional[str] = Field(None, description="If matched a symbol")
    symbol_type: Optional[str] = Field(None, description="function, class, etc.")
    
    # Context
    context_before: Optional[str] = Field(None, description="Lines before match")
    context_after: Optional[str] = Field(None, description="Lines after match")
    
    class Config:
        schema_extra = {
            "example": {
                "chunk_id": 42,
                "file_id": 10,
                "file_path": "src/api/handlers.py",
                "snippet": "def handle_request(req):\n    ...",
                "start_line": 15,
                "end_line": 25,
                "match_type": ["semantic", "keyword"],
                "relevance_score": 0.92,
                "language": "python"
            }
        }


class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    mode: SearchMode
    total_results: int
    page: int
    per_page: int
    total_pages: int
    
    results: List[SearchResultItem]
    
    # Performance
    latency_ms: int
    
    # Metadata
    filters_applied: Dict[str, Any]
    suggestions: Optional[List[str]] = Field(None, description="Query suggestions")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "HTTP handler",
                "mode": "hybrid",
                "total_results": 15,
                "page": 1,
                "per_page": 20,
                "total_pages": 1,
                "results": [],
                "latency_ms": 245
            }
        }


class SymbolInfo(BaseModel):
    """Symbol information"""
    id: int
    name: str
    qualified_name: Optional[str]
    symbol_type: str
    signature: Optional[str]
    docstring: Optional[str]
    
    file_path: str
    start_line: int
    end_line: int
    
    language: str
    scope: Optional[str]
    
    # If nested
    parent_symbol: Optional[str]


class SymbolSearchResponse(BaseModel):
    """Symbol search results"""
    query: str
    total_results: int
    symbols: List[SymbolInfo]
    latency_ms: int


class IndexJobRequest(BaseModel):
    """Request to start indexing"""
    branch: Optional[str] = Field(default="main", description="Branch to index")
    force: bool = Field(default=False, description="Force re-index even if up-to-date")
    incremental: bool = Field(default=True, description="Use incremental indexing")


class IndexJobStatus(BaseModel):
    """Index job status"""
    job_id: int
    repo_id: int
    status: str
    progress: float  # 0.0 to 1.0
    
    files_processed: int
    chunks_created: int
    symbols_extracted: int
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    error_message: Optional[str]