from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


# Request Schemas
class RepositoryIngestRequest(BaseModel):
    """Request schema for ingesting a GitHub repository"""
    github_url: str = Field(..., description="GitHub repository URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "github_url": "https://github.com/psf/requests"
            }
        }


class ChatRequest(BaseModel):
    """Request schema for chatting with a repository"""
    question: str = Field(..., min_length=1, description="User question about the codebase")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of code chunks to retrieve")
    prompt_style: Optional[str] = Field("senior_dev", description="Prompt style: senior_dev, concise, or educational")
    include_sources: Optional[bool] = Field(True, description="Include source file references")
    include_metadata: Optional[bool] = Field(True, description="Include query metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "How does this codebase handle HTTP requests?",
                "top_k": 5,
                "prompt_style": "senior_dev",
                "include_sources": True,
                "include_metadata": True
            }
        }


# Response Schemas
class RepositoryResponse(BaseModel):
    id: int
    github_url: str
    status: str
    repo_metadata: Optional[Dict[str, Any]] = {}  # Changed back to repo_metadata
    local_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RepositoryIngestResponse(BaseModel):
    """Response schema for repository ingestion"""
    id: int
    github_url: str
    status: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "github_url": "https://github.com/psf/requests",
                "status": "pending",
                "message": "Repository ingestion started. Processing in background."
            }
        }


class SourceReference(BaseModel):
    file_path: str
    language: str
    relevance_score: float
    lines: Optional[Union[str, int]] = None  # Accept both string and int
    
    @field_validator('lines', mode='before')
    @classmethod
    def convert_lines_to_string(cls, v):
        """Convert lines to string format if it's an integer."""
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v

class ChatResponse(BaseModel):
    """Response schema for chat with repository"""
    id: int
    question: str
    answer: str
    sources: List[SourceReference]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "question": "How does authentication work?",
                "answer": "The codebase uses JWT tokens for authentication...",
                "sources": [
                    {
                        "file_path": "src/auth/jwt.py",
                        "language": "python",
                        "relevance_score": 0.92,
                        "lines": "45-67"
                    }
                ],
                "metadata": {
                    "chunks_found": 5,
                    "avg_similarity": 0.847,
                    "model": "qwen2.5-coder:7b",
                    "prompt_style": "senior_dev"
                },
                "created_at": "2025-01-15T10:30:00"
            }
        }


class ChatHistoryResponse(BaseModel):
    id: int
    repo_id: int
    question: str
    answer: str
    sources: List[SourceReference] = []
    message_metadata: Optional[Dict[str, Any]] = {}  # Changed back to message_metadata
    created_at: datetime

    class Config:
        from_attributes = True

class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    status_code: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Repository not found",
                "status_code": 404
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response for RAG service"""
    status: str
    ollama_url: str
    model: str
    embed_model: str
    embedding_dim: Optional[int] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "ollama_url": "http://localhost:11434",
                "model": "qwen2.5-coder:7b",
                "embed_model": "nomic-embed-text",
                "embedding_dim": 768
            }
        }


# File System Schemas        
class RepositoryFileBase(BaseModel):
    file_path: str
    file_name: str
    file_type: str
    is_directory: bool
    parent_path: Optional[str] = None
    size_bytes: int = 0


class RepositoryFileCreate(RepositoryFileBase):
    repo_id: int


class RepositoryFileResponse(RepositoryFileBase):
    id: int
    repo_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Tree structure for frontend
class FileTreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    extension: Optional[str] = None
    size: int = 0
    children: Optional[List['FileTreeNode']] = None


# File content response
class FileContentResponse(BaseModel):
    file_path: str
    content: str
    language: str
    size_bytes: int
    lines: int


# Search/Query specific schemas
class CodeSearchRequest(BaseModel):
    """Request schema for advanced code search"""
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(5, ge=1, le=20)
    score_threshold: Optional[float] = Field(0.3, ge=0.0, le=1.0)
    rerank: Optional[bool] = Field(True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "authentication implementation",
                "top_k": 5,
                "score_threshold": 0.3,
                "rerank": True
            }
        }


class CodeChunkResponse(BaseModel):
    """Response schema for individual code chunks"""
    id: str
    content: str
    metadata: Dict[str, Any]
    similarity: float
    original_similarity: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "chunk_123",
                "content": "def authenticate(user, password):\n    ...",
                "metadata": {
                    "file_path": "src/auth.py",
                    "language": "python",
                    "lines": "10-25"
                },
                "similarity": 0.89,
                "original_similarity": 0.85
            }
        }