from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Repository(Base):
    """Repository model to store GitHub repository information."""
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    github_url = Column(String(500), unique=True, nullable=False, index=True)
    status = Column(String(50), default="pending")
    
    # Use repo_metadata (same as database column)
    repo_metadata = Column(JSON, default={})
    
    local_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    code_files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="repository", cascade="all, delete-orphan")
    repository_files = relationship("RepositoryFile", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository(id={self.id}, url={self.github_url}, status={self.status})>"


class RepositoryFile(Base):
    """RepositoryFile model to store file tree structure."""
    __tablename__ = "repository_files"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_path = Column(String(2000), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    is_directory = Column(Boolean, default=False)
    parent_path = Column(String(2000), nullable=True)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    repository = relationship("Repository", back_populates="repository_files")
    
    def __repr__(self):
        return f"<RepositoryFile(id={self.id}, path={self.file_path}, type={self.file_type})>"


class CodeFile(Base):
    """CodeFile model to store parsed code files from repositories."""
    __tablename__ = "code_files"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(String(50), nullable=False, index=True)
    
    # Use file_metadata (same as database column)
    file_metadata = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    repository = relationship("Repository", back_populates="code_files")
    
    def __repr__(self):
        return f"<CodeFile(id={self.id}, path={self.file_path}, language={self.language})>"


class ChatMessage(Base):
    """ChatMessage model to store chat history and RAG responses."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, default=[])
    
    # Use message_metadata (same as database column)
    message_metadata = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    repository = relationship("Repository", back_populates="chat_messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, repo_id={self.repo_id})>"


class CodeChunk(Base):
    """Represents a chunk of code for semantic search."""
    __tablename__ = "code_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    language = Column(String(50), nullable=False, index=True)
    chunk_type = Column(String(50))
    vector_id = Column(String(200))
    keywords = Column(JSON, default=[])
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    repository = relationship("Repository")
    file = relationship("CodeFile")
    
    __table_args__ = (
        Index('idx_repo_file_chunk', 'repo_id', 'file_id', 'chunk_index'),
    )


class Symbol(Base):
    """Represents a code symbol (function, class, variable, etc.)"""
    __tablename__ = "symbols"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    file_id = Column(Integer, ForeignKey("code_files.id"), nullable=False, index=True)
    name = Column(String(500), nullable=False, index=True)
    qualified_name = Column(String(1000))
    symbol_type = Column(String(50), nullable=False, index=True)
    signature = Column(Text)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    start_column = Column(Integer)
    end_column = Column(Integer)
    docstring = Column(Text)
    comment = Column(Text)
    language = Column(String(50), nullable=False, index=True)
    scope = Column(String(50))
    parent_symbol_id = Column(Integer, ForeignKey("symbols.id"))
    search_vector = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    repository = relationship("Repository")
    file = relationship("CodeFile")
    parent = relationship("Symbol", remote_side=[id])
    
    __table_args__ = (
        Index('idx_symbol_name', 'name', 'symbol_type'),
        Index('idx_repo_symbol', 'repo_id', 'name'),
        Index('idx_file_symbol', 'file_id', 'start_line'),
    )


class IndexJob(Base):
    """Tracks indexing jobs for repositories."""
    __tablename__ = "index_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    branch = Column(String(200), default="main")
    commit_hash = Column(String(64))
    job_type = Column(String(50), default="full")
    status = Column(String(50), default="pending", index=True)
    progress = Column(Float, default=0.0)
    files_processed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)
    symbols_extracted = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)
    
    repository = relationship("Repository")


class SearchQuery(Base):
    """Logs search queries for analytics and improvement."""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_mode = Column(String(50))
    results_count = Column(Integer)
    top_result_score = Column(Float)
    latency_ms = Column(Integer)
    clicked_result_id = Column(Integer)
    user_rating = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    repository = relationship("Repository")
