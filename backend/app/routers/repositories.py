from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import traceback
import json
import os      
import shutil

from app.database import get_db
from app.models import Repository, CodeFile, ChatMessage
from app.schemas import (
    RepositoryIngestRequest,
    RepositoryIngestResponse,
    RepositoryResponse,
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    SourceReference,
    HealthCheckResponse,
    CodeSearchRequest,
    CodeChunkResponse
)
from app.services.github_service import (
    clone_repository,
    get_repo_metadata
)
from app.services.code_parser import parse_repository_files
from app.services.embedding_service import create_embeddings
from app.services.rag_service import (
    query_codebase,
    query_codebase_stream,
    search_similar_code,
    check_service_health
)
from app.services.file_service import FileService


router = APIRouter(
    prefix="/repos",
    tags=["repositories"]
)


def process_repository_ingestion(repo_id: int, github_url: str, db: Session):
    """
    Background task to process repository ingestion.
    This runs asynchronously to avoid blocking the API.
    """
    repo_path = None
    try:
        print(f"\n{'='*60}")
        print(f"Starting ingestion for repository ID: {repo_id}")
        print(f"{'='*60}\n")
        
        # Update status to processing
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        repo.status = "processing"
        db.commit()
        
        # Step 1: Clone repository
        print("🔄 Step 1: Cloning repository...")
        repo_path = clone_repository(github_url)
        repo_meta = get_repo_metadata(github_url)
        
        # Update metadata AND local_path
        repo.repo_metadata = repo_meta
        repo.local_path = repo_path
        db.commit()
        
        # Step 1.5: Scan file structure
        print("\n📂 Step 1.5: Scanning file structure...")
        FileService.scan_repository_files(repo_id, repo_path, db)
        
        # Step 2: Parse code files
        print("\n📖 Step 2: Parsing code files...")
        parsed_files = parse_repository_files(repo_path)
        
        if not parsed_files:
            raise Exception("No code files found in repository")
        
        # Step 3: Save code files to database
        print(f"\n💾 Step 3: Saving {len(parsed_files)} files to database...")
        file_id_map = {}
        for idx, file_info in enumerate(parsed_files):
            code_file = CodeFile(
                repo_id=repo_id,
                file_path=file_info['file_path'],
                content=file_info['content'],
                language=file_info['language'],
                file_metadata=file_info['metadata']
            )
            db.add(code_file)
            db.flush()
            file_id_map[idx] = code_file.id
            parsed_files[idx]['file_id'] = code_file.id

        db.commit()
        
        # Step 4: Create embeddings
        print("\n🧠 Step 4: Creating embeddings...")
        embedding_stats = create_embeddings(repo_id, parsed_files)
        
        # Update repository metadata with embedding stats
        current_metadata = repo.repo_metadata or {}
        current_metadata.update({
            "total_files": len(parsed_files),
            "embedding_stats": embedding_stats
        })
        repo.repo_metadata = current_metadata
        repo.status = "completed"
        db.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ Repository ingestion completed successfully!")
        print(f"   Repository ID: {repo_id}")
        print(f"   Files processed: {len(parsed_files)}")
        print(f"   Total chunks: {embedding_stats.get('total_chunks', 0)}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error processing repository {repo_id}: {str(e)}")
        traceback.print_exc()
        
        # Update status to failed
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                repo.status = "failed"
                current_metadata = repo.repo_metadata or {}
                current_metadata["error"] = str(e)
                repo.repo_metadata = current_metadata
                db.commit()
        except Exception as db_error:
            print(f"❌ Failed to update repository status: {str(db_error)}")


@router.post("/ingest", response_model=RepositoryIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_repository(
    request: RepositoryIngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest a GitHub repository for processing.
    
    This endpoint triggers a background task to:
    1. Clone the repository
    2. Parse code files
    3. Create embeddings
    4. Store everything in the database
    
    Returns immediately with repository ID while processing continues in background.
    """
    try:
        # Check if repository already exists
        existing_repo = db.query(Repository).filter(
            Repository.github_url == request.github_url
        ).first()
        
        if existing_repo:
            if existing_repo.status == "completed":
                return RepositoryIngestResponse(
                    id=existing_repo.id,
                    github_url=existing_repo.github_url,
                    status=existing_repo.status,
                    message="Repository already ingested and ready to use."
                )
            elif existing_repo.status == "processing":
                return RepositoryIngestResponse(
                    id=existing_repo.id,
                    github_url=existing_repo.github_url,
                    status=existing_repo.status,
                    message="Repository is currently being processed."
                )
            else:
                # If failed or pending, restart processing
                existing_repo.status = "pending"
                db.commit()
                
                background_tasks.add_task(
                    process_repository_ingestion,
                    existing_repo.id,
                    request.github_url,
                    db
                )
                
                return RepositoryIngestResponse(
                    id=existing_repo.id,
                    github_url=existing_repo.github_url,
                    status="pending",
                    message="Repository ingestion restarted. Processing in background."
                )
        
        # Create new repository record
        new_repo = Repository(
            github_url=request.github_url,
            status="pending",
            metadata={}
        )
        db.add(new_repo)
        db.commit()
        db.refresh(new_repo)
        
        # Start background processing
        background_tasks.add_task(
            process_repository_ingestion,
            new_repo.id,
            request.github_url,
            db
        )
        
        return RepositoryIngestResponse(
            id=new_repo.id,
            github_url=new_repo.github_url,
            status=new_repo.status,
            message="Repository ingestion started. Processing in background."
        )
        
    except Exception as e:
        print(f"❌ Error in ingest endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start repository ingestion: {str(e)}"
        )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository_status(repo_id: int, db: Session = Depends(get_db)):
    """
    Get the status and details of a repository.
    
    Status can be:
    - pending: Waiting to be processed
    - processing: Currently being ingested
    - completed: Ready to use
    - failed: Ingestion failed
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repo_id} not found"
        )
    
    return repo


@router.post("/{repo_id}/chat", response_model=ChatResponse)
async def chat_with_repository(
    repo_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with a repository using RAG.
    
    This endpoint:
    1. Retrieves relevant code chunks from the vector database
    2. Generates an answer using Ollama LLM
    3. Saves the conversation to the database
    4. Returns the answer with source references
    
    Supports customization via:
    - top_k: Number of code chunks to retrieve (1-20)
    - prompt_style: Response style (senior_dev, concise, educational)
    - include_sources: Whether to return source references
    - include_metadata: Whether to return query metadata
    """
    try:
        # Check if repository exists and is ready
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found"
            )
        
        if repo.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repository is not ready for chat. Current status: {repo.status}"
            )
        
        # Get chat history for context (last 3 messages)
        recent_messages = db.query(ChatMessage)\
            .filter(ChatMessage.repo_id == repo_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(3)\
            .all()
        
        chat_history = [
            {"question": msg.question, "answer": msg.answer}
            for msg in reversed(recent_messages)
        ]
        
        # Query the codebase using RAG with all parameters
        print(f"💬 Processing chat request for repo {repo_id}: {request.question}")
        print(f"   Settings: top_k={request.top_k}, style={request.prompt_style}")
        
        rag_result = query_codebase(
            repo_id=repo_id,
            query=request.question,
            top_k=request.top_k,
            include_sources=request.include_sources,
            chat_history=chat_history,
            prompt_style=request.prompt_style,
            include_metadata=request.include_metadata
        )
        
        # Convert sources to schema format with type safety
        sources = []
        for src in rag_result.get("sources", []):
            # Ensure lines is a string
            lines_value = src.get("lines")
            if lines_value is not None:
                if isinstance(lines_value, int):
                    lines_str = str(lines_value)
                else:
                    lines_str = str(lines_value)
            else:
                lines_str = None
            
            sources.append(
                SourceReference(
                    file_path=src["file_path"],
                    language=src["language"],
                    relevance_score=src["relevance_score"],
                    lines=lines_str
                )
            )
        
        # Save chat message to database
        chat_message = ChatMessage(
            repo_id=repo_id,
            question=request.question,
            answer=rag_result["answer"],
            sources=[src.dict() for src in sources],
            metadata=rag_result.get("metadata")
        )
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        
        print(f"✅ Chat response saved with ID: {chat_message.id}")
        
        return ChatResponse(
            id=chat_message.id,
            question=chat_message.question,
            answer=chat_message.answer,
            sources=sources,
            metadata=chat_message.metadata,
            created_at=chat_message.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.post("/{repo_id}/chat/stream")
async def chat_with_repository_stream(
    repo_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Streaming version of chat endpoint.
    
    Returns a Server-Sent Events (SSE) stream for real-time response generation.
    The stream includes both the answer text and source references at the end.
    """
    try:
        # Check if repository exists and is ready
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found"
            )
        
        if repo.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repository is not ready for chat. Current status: {repo.status}"
            )
        
        # Get chat history for context
        recent_messages = db.query(ChatMessage)\
            .filter(ChatMessage.repo_id == repo_id)\
            .order_by(ChatMessage.created_at.desc())\
            .limit(3)\
            .all()
        
        chat_history = [
            {"question": msg.question, "answer": msg.answer}
            for msg in reversed(recent_messages)
        ]
        
        print(f"💬 Streaming chat request for repo {repo_id}: {request.question}")
        
        async def generate():
            full_answer = ""
            sources_data = []
            
            try:
                for chunk in query_codebase_stream(
                    repo_id=repo_id,
                    query=request.question,
                    top_k=request.top_k,
                    chat_history=chat_history,
                    prompt_style=request.prompt_style
                ):
                    # Check if this is the sources marker
                    if "[SOURCES]" in chunk and "[/SOURCES]" in chunk:
                        # Extract and parse sources
                        start = chunk.find("[SOURCES]") + len("[SOURCES]")
                        end = chunk.find("[/SOURCES]")
                        sources_json = chunk[start:end]
                        sources_data = json.loads(sources_json)
                        # Don't yield the marker to client
                        continue
                    
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                
                # Send sources as separate event
                if sources_data:
                    yield f"data: {json.dumps({'type': 'sources', 'content': sources_data})}\n\n"
                
                # Save to database after streaming completes
                sources = [
                    SourceReference(
                        file_path=src["file_path"],
                        language=src["language"],
                        relevance_score=src["relevance_score"]
                    )
                    for src in sources_data
                ]
                
                chat_message = ChatMessage(
                    repo_id=repo_id,
                    question=request.question,
                    answer=full_answer,
                    sources=[src.dict() for src in sources],
                    metadata={"streaming": True, "prompt_style": request.prompt_style}
                )
                db.add(chat_message)
                db.commit()
                
                yield f"data: {json.dumps({'type': 'done', 'message_id': chat_message.id})}\n\n"
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in streaming chat endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process streaming chat request: {str(e)}"
        )


@router.post("/{repo_id}/search", response_model=List[CodeChunkResponse])
async def search_code(
    repo_id: int,
    request: CodeSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Advanced code search endpoint.
    
    Returns raw code chunks without generating an answer.
    Useful for exploring the codebase or building custom interfaces.
    """
    try:
        # Check if repository exists and is ready
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found"
            )
        
        if repo.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repository is not ready. Current status: {repo.status}"
            )
        
        # Search for similar code
        chunks = search_similar_code(
            repo_id=repo_id,
            query=request.query,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            rerank=request.rerank
        )
        
        # Convert to response format
        response = [
            CodeChunkResponse(
                id=chunk["id"],
                content=chunk["content"],
                metadata=chunk["metadata"],
                similarity=chunk["similarity"],
                original_similarity=chunk.get("original_similarity")
            )
            for chunk in chunks
        ]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in search endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search code: {str(e)}"
        )


@router.get("/{repo_id}/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(
    repo_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get chat history for a repository.
    
    Returns the most recent chat messages, ordered by creation time (newest first).
    """
    # Check if repository exists
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repo_id} not found"
        )
    
    # Get chat history
    chat_history = db.query(ChatMessage)\
        .filter(ChatMessage.repo_id == repo_id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(limit)\
        .all()
    
    return chat_history


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(repo_id: int, db: Session = Depends(get_db)):
    """Delete a repository and all associated data."""
    from app.models import CodeChunk, Symbol, IndexJob, SearchQuery, RepositoryFile  # Import all models
    
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID {repo_id} not found"
        )
    
    try:
        print(f"\n🗑️  Starting deletion of repository {repo_id}...")
        
        # 1. Delete ChromaDB collection
        from app.services.embedding_service import chroma_client
        try:
            collection_name = f"repo_{repo_id}"
            chroma_client.delete_collection(name=collection_name)
            print(f"✅ Deleted ChromaDB collection: {collection_name}")
        except ValueError:
            print(f"ℹ️  ChromaDB collection doesn't exist (already deleted)")
        except Exception as e:
            print(f"⚠️  Warning: Could not delete ChromaDB collection: {str(e)}")
        
        # 2. Delete local cloned files
        if repo.local_path and os.path.exists(repo.local_path):
            try:
                shutil.rmtree(repo.local_path, ignore_errors=True)
                print(f"✅ Deleted local files: {repo.local_path}")
            except Exception as e:
                print(f"⚠️  Warning: Could not delete local files: {str(e)}")
        
        # 3. Delete all related records in order (to respect foreign keys)
        
        # Delete search queries
        search_count = db.query(SearchQuery).filter(SearchQuery.repo_id == repo_id).count()
        db.query(SearchQuery).filter(SearchQuery.repo_id == repo_id).delete()
        print(f"✅ Deleted {search_count} search queries")
        
        # Delete index jobs
        job_count = db.query(IndexJob).filter(IndexJob.repo_id == repo_id).count()
        db.query(IndexJob).filter(IndexJob.repo_id == repo_id).delete()
        print(f"✅ Deleted {job_count} index jobs")
        
        # Delete symbols (references code_files)
        symbol_count = db.query(Symbol).filter(Symbol.repo_id == repo_id).count()
        db.query(Symbol).filter(Symbol.repo_id == repo_id).delete()
        print(f"✅ Deleted {symbol_count} symbols")
        
        # Delete code chunks (references code_files)
        chunk_count = db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).count()
        db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).delete()
        print(f"✅ Deleted {chunk_count} code chunks")
        
        # Delete repository files
        repo_file_count = db.query(RepositoryFile).filter(RepositoryFile.repo_id == repo_id).count()
        db.query(RepositoryFile).filter(RepositoryFile.repo_id == repo_id).delete()
        print(f"✅ Deleted {repo_file_count} repository files")
        
        # Get counts for code_files and chat_messages (these will cascade)
        file_count = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).count()
        chat_count = db.query(ChatMessage).filter(ChatMessage.repo_id == repo_id).count()
        
        # 4. Delete repository (cascade will handle code_files and chat_messages)
        db.delete(repo)
        db.commit()
        
        print(f"✅ Deleted repository {repo_id}")
        print(f"   - {search_count} search queries")
        print(f"   - {job_count} index jobs")
        print(f"   - {symbol_count} symbols")
        print(f"   - {chunk_count} code chunks")
        print(f"   - {repo_file_count} repository files")
        print(f"   - {file_count} code files")
        print(f"   - {chat_count} chat messages")
        print(f"{'='*60}\n")
        
        return None  # 204 No Content
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting repository: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete repository: {str(e)}"
        )


@router.get("/", response_model=List[RepositoryResponse])
async def list_repositories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all repositories with pagination.
    """
    repositories = db.query(Repository)\
        .order_by(Repository.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return repositories


# Health check endpoint
@router.get("/health/rag", response_model=HealthCheckResponse)
async def check_rag_health():
    """
    Check the health of the RAG service components.
    
    This verifies:
    - Ollama connection
    - Embeddings model availability
    - LLM availability
    """
    try:
        health_status = check_service_health()
        return HealthCheckResponse(**health_status)
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG service is unhealthy: {str(e)}"
        )
        
@router.post("/{repo_id}/reingest", response_model=RepositoryIngestResponse)
async def reingest_repository(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Re-ingest an existing repository.
    
    This will:
    1. Delete old embeddings and code files
    2. Re-clone the repository
    3. Re-parse and re-embed everything
    
    Useful when repository code has been updated.
    """
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repo_id} not found"
            )
        
        # Check if already processing
        if repo.status in ["pending", "processing"]:
            return RepositoryIngestResponse(
                id=repo.id,
                github_url=repo.github_url,
                status=repo.status,
                message="Repository is already being processed."
            )
        
        # Delete old data
        from app.models import CodeChunk, Symbol, RepositoryFile
        from app.services.embedding_service import chroma_client
        
        print(f"\n🔄 Re-ingesting repository {repo_id}...")
        
        # Delete ChromaDB collection
        try:
            chroma_client.delete_collection(name=f"repo_{repo_id}")
            print(f"✅ Deleted old embeddings")
        except:
            pass
        
        # Delete related records
        db.query(Symbol).filter(Symbol.repo_id == repo_id).delete()
        db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).delete()
        db.query(RepositoryFile).filter(RepositoryFile.repo_id == repo_id).delete()
        db.query(CodeFile).filter(CodeFile.repo_id == repo_id).delete()
        db.query(ChatMessage).filter(ChatMessage.repo_id == repo_id).delete()
        
        # Delete local files
        if repo.local_path and os.path.exists(repo.local_path):
            try:
                shutil.rmtree(repo.local_path, ignore_errors=True)
            except:
                pass
        
        # Reset repository status
        repo.status = "pending"
        repo.repo_metadata = {"re_ingest": True}
        repo.local_path = None
        db.commit()
        
        print(f"✅ Cleaned old data for repository {repo_id}")
        
        # Start background processing
        background_tasks.add_task(
            process_repository_ingestion,
            repo.id,
            repo.github_url,
            db
        )
        
        return RepositoryIngestResponse(
            id=repo.id,
            github_url=repo.github_url,
            status="pending",
            message="Repository re-ingestion started. Processing in background."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in reingest endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start re-ingestion: {str(e)}"
        )
