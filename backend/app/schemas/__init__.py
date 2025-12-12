from pydantic import BaseModel

class HealthCheckResponse(BaseModel):
    status: str
    message: str = "Service is running"


from .repository import (
    RepositoryIngestRequest,
    RepositoryIngestResponse,
    RepositoryResponse,
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    SourceReference,
    ErrorResponse,
    CodeSearchRequest,      
    CodeChunkResponse       
)

__all__ = [
    "RepositoryIngestRequest",
    "RepositoryIngestResponse",
    "RepositoryResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatHistoryResponse",
    "SourceReference",
    "ErrorResponse",
    "CodeSearchRequest",    
    "CodeChunkResponse"     
]