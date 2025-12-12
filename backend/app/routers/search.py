# backend/app/routers/search.py

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import time

from app.database import get_db
from app.models import Repository, SearchQuery, CodeFile, CodeChunk, Symbol, IndexJob
from app.schemas.search import (
    SearchRequest, SearchResponse, SearchResultItem,
    SymbolSearchResponse, SymbolInfo,
    IndexJobRequest, IndexJobStatus,
    SearchMode, MatchType
)
from app.services.hybrid_search_service import hybrid_search_service
from app.services.indexing_service import indexing_service

# Import ChromaDB client
try:
    from app.config.chroma import get_chroma_client
    chroma_client = get_chroma_client()
except Exception as e:
    print(f"Warning: ChromaDB client initialization failed: {e}")
    chroma_client = None

router = APIRouter(
    prefix="/repos/{repo_id}",
    tags=["search"]
)


@router.post("/index", response_model=IndexJobStatus, status_code=202)
async def start_indexing(
    repo_id: int,
    request: IndexJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start indexing/re-indexing a repository.
    
    This endpoint:
    - Clones the repository
    - Parses and chunks code files
    - Extracts symbols
    - Generates embeddings
    - Builds text index
    
    Returns immediately with job ID while processing continues in background.
    """
    # Check if repository exists
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Check if repository is ready
    if repo.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Repository must be completed before indexing. Current status: {repo.status}"
        )
    
    try:
        # Start indexing
        job_id = await indexing_service.start_indexing(
            repo_id=repo_id,
            branch=request.branch,
            force=request.force,
            incremental=request.incremental,
            db=db
        )
        
        # Get job status
        job = indexing_service.get_job_status(job_id, db)
        
        return IndexJobStatus(
            job_id=job.id,
            repo_id=job.repo_id,
            status=job.status,
            progress=job.progress,
            files_processed=job.files_processed,
            chunks_created=job.chunks_created,
            symbols_extracted=job.symbols_extracted,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start indexing: {str(e)}"
        )


@router.get("/index/status", response_model=IndexJobStatus)
async def get_index_status(
    repo_id: int,
    job_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get indexing job status.
    
    If job_id not provided, returns latest job for this repo.
    """
    if job_id:
        job = db.query(IndexJob).filter(
            IndexJob.id == job_id,
            IndexJob.repo_id == repo_id
        ).first()
    else:
        # Get latest job
        job = db.query(IndexJob).filter(
            IndexJob.repo_id == repo_id
        ).order_by(IndexJob.created_at.desc()).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="No indexing job found")
    
    return IndexJobStatus(
        job_id=job.id,
        repo_id=job.repo_id,
        status=job.status,
        progress=job.progress,
        files_processed=job.files_processed,
        chunks_created=job.chunks_created,
        symbols_extracted=job.symbols_extracted,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )


@router.get("/search", response_model=SearchResponse)
async def search_code(
    repo_id: int,
    q: str = Query(..., description="Search query", min_length=1),
    mode: SearchMode = Query(default=SearchMode.AUTO, description="Search mode"),
    file: Optional[str] = Query(None, description="File path filter (glob)"),
    lang: Optional[str] = Query(None, description="Language filter"),
    branch: str = Query(default="main", description="Branch to search"),
    symbol_type: Optional[str] = Query(None, description="Symbol type filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=20, ge=1, le=100, description="Results per page"),
    include_tests: bool = Query(default=True, description="Include test files"),
    case_sensitive: bool = Query(default=False, description="Case sensitive search"),
    db: Session = Depends(get_db)
):
    """
    Search code in repository.
    
    Supports multiple search modes:
    - **semantic**: Natural language queries (e.g., "Where is the HTTP handler?")
    - **keyword**: Exact keyword matching
    - **symbol**: Search for functions, classes, etc.
    - **regex**: Regular expression search
    - **hybrid**: Combines semantic + keyword + symbol (recommended)
    - **auto**: Automatically detects best mode
    
    Examples:
    - `?q=getUserById&mode=symbol` - Find symbol
    - `?q=Where is authentication&mode=semantic` - Natural language
    - `?q=router\.handle&mode=regex` - Regex search
    - `?q=HTTP handler&mode=hybrid` - Best results
    """
    start_time = time.time()
    
    # Check repository exists
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Build filters
    filters = {
        'file': file,
        'lang': lang,
        'branch': branch,
        'symbol_type': symbol_type,
        'include_tests': include_tests,
        'case_sensitive': case_sensitive
    }
    
    try:
        # Perform search
        results, total_results = await hybrid_search_service.search(
            repo_id=repo_id,
            query=q,
            mode=mode,
            filters=filters,
            db=db
        )
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]
        
        # Format results
        formatted_results = []
        for result in paginated_results:
            # Highlight snippet
            highlighted_snippet = hybrid_search_service._highlight_snippet(
                result['snippet'], q
            )
            
            formatted_results.append(SearchResultItem(
                chunk_id=result.get('chunk_id'),
                file_id=result['file_id'],
                file_path=result['file_path'],
                snippet=result['snippet'],
                highlighted_snippet=highlighted_snippet,
                start_line=result['start_line'],
                end_line=result['end_line'],
                match_type=result['match_type'],
                relevance_score=result['relevance_score'],
                semantic_score=result.get('semantic_score'),
                keyword_score=result.get('keyword_score'),
                symbol_score=result.get('symbol_score'),
                language=result['language'],
                symbol_name=result.get('symbol_name'),
                symbol_type=result.get('symbol_type'),
                context_before=None,  # Can be fetched separately
                context_after=None
            ))
        
        # Calculate total pages
        total_pages = (total_results + per_page - 1) // per_page
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Log search query
        search_query = SearchQuery(
            repo_id=repo_id,
            query_text=q,
            query_mode=mode.value,
            results_count=total_results,
            top_result_score=formatted_results[0].relevance_score if formatted_results else None,
            latency_ms=latency_ms
        )
        db.add(search_query)
        db.commit()
        
        return SearchResponse(
            query=q,
            mode=mode,
            total_results=total_results,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            results=formatted_results,
            latency_ms=latency_ms,
            filters_applied=filters,
            suggestions=None  # Can implement query suggestions
        )
        
    except ValueError as e:
        # Invalid regex or other validation error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/symbols", response_model=SymbolSearchResponse)
async def search_symbols(
    repo_id: int,
    q: str = Query(..., description="Symbol name query"),
    lang: Optional[str] = Query(None, description="Language filter"),
    symbol_type: Optional[str] = Query(None, description="Symbol type filter"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Search for symbols (functions, classes, variables, etc.)
    
    Examples:
    - `?q=get` - Find all symbols containing "get"
    - `?q=getUserById` - Find specific symbol
    - `?q=User&symbol_type=class` - Find classes containing "User"
    """
    start_time = time.time()
    
    from sqlalchemy import or_, and_
    
    # Build query
    query_filter = and_(
        Symbol.repo_id == repo_id,
        or_(
            Symbol.name.ilike(f"%{q}%"),
            Symbol.qualified_name.ilike(f"%{q}%")
        )
    )
    
    if lang:
        query_filter = and_(query_filter, Symbol.language == lang)
    
    if symbol_type:
        query_filter = and_(query_filter, Symbol.symbol_type == symbol_type)
    
    # Execute query
    symbols = db.query(Symbol).filter(query_filter).limit(limit).all()
    
    # Format results
    symbol_results = []
    for symbol in symbols:
        symbol_results.append(SymbolInfo(
            id=symbol.id,
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            symbol_type=symbol.symbol_type,
            signature=symbol.signature,
            docstring=symbol.docstring,
            file_path=symbol.file.file_path if symbol.file else "unknown",
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            language=symbol.language,
            scope=symbol.scope,
            parent_symbol=None  # Can populate if needed
        ))
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    return SymbolSearchResponse(
        query=q,
        total_results=len(symbol_results),
        symbols=symbol_results,
        latency_ms=latency_ms
    )


@router.get("/file/{file_id}/content")
async def get_file_content(
    repo_id: int,
    file_id: int,
    start: Optional[int] = Query(None, description="Start line (1-indexed)"),
    end: Optional[int] = Query(None, description="End line (1-indexed)"),
    context: int = Query(default=5, description="Context lines around selection"),
    db: Session = Depends(get_db)
):
    """
    Get file content with optional line range.
    
    Useful for:
    - Opening a file from search results
    - Jumping to specific lines
    - Getting context around a match
    """
    file = db.query(CodeFile).filter(
        CodeFile.id == file_id,
        CodeFile.repo_id == repo_id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    lines = file.content.split('\n')
    total_lines = len(lines)
    
    # If start/end specified, extract range with context
    if start is not None and end is not None:
        context_start = max(1, start - context)
        context_end = min(total_lines, end + context)
        
        selected_lines = lines[context_start-1:context_end]
        content = '\n'.join(selected_lines)
        
        return {
            'file_id': file.id,
            'file_path': file.file_path,
            'language': file.language,
            'content': content,
            'start_line': context_start,
            'end_line': context_end,
            'total_lines': total_lines,
            'metadata': file.file_metadata
        }
    else:
        # Return entire file
        return {
            'file_id': file.id,
            'file_path': file.file_path,
            'language': file.language,
            'content': file.content,
            'start_line': 1,
            'end_line': total_lines,
            'total_lines': total_lines,
            'metadata': file.file_metadata
        }


@router.post("/search/preview")
async def preview_search_results(
    repo_id: int,
    chunk_ids: List[str],
    context_lines: int = Query(default=5, description="Context lines"),
    db: Session = Depends(get_db)
):
    """
    Get full snippets with context for specific chunk IDs.
    
    Useful for:
    - Re-ranking results
    - Fetching more context on demand
    - Preview before opening file
    """
    previews = []
    
    for chunk_id in chunk_ids:
        # Parse chunk_id format: chunk_{repo_id}_{file_id}_{chunk_index}
        parts = chunk_id.split('_')
        if len(parts) != 4:
            continue
        
        file_id = int(parts[2])
        chunk_index = int(parts[3])
        
        chunk = db.query(CodeChunk).filter(
            CodeChunk.repo_id == repo_id,
            CodeChunk.file_id == file_id,
            CodeChunk.chunk_index == chunk_index
        ).first()
        
        if chunk:
            # Get context
            context = await hybrid_search_service.get_context(
                file_id=chunk.file_id,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                context_lines=context_lines,
                db=db
            )
            
            previews.append({
                'chunk_id': chunk_id,
                'file_path': context['file_path'],
                'language': context['language'],
                'content': context['content'],
                'start_line': context['start_line'],
                'end_line': context['end_line']
            })
    
    return {'previews': previews}


@router.delete("/index", status_code=200)
async def clear_index(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    Clear all indexing data for a repository.
    Use this before re-indexing if you want to start fresh.
    """
    try:
        # Get counts before deleting
        chunks_count = db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).count()
        symbols_count = db.query(Symbol).filter(Symbol.repo_id == repo_id).count()
        files_count = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).count()
        
        # Delete chunks
        db.query(CodeChunk).filter(
            CodeChunk.repo_id == repo_id
        ).delete(synchronize_session=False)
        
        # Delete symbols
        db.query(Symbol).filter(
            Symbol.repo_id == repo_id
        ).delete(synchronize_session=False)
        
        # Delete code files
        db.query(CodeFile).filter(
            CodeFile.repo_id == repo_id
        ).delete(synchronize_session=False)
        
        # Mark all index jobs as cancelled
        db.query(IndexJob).filter(
            IndexJob.repo_id == repo_id,
            IndexJob.status.in_(['pending', 'running'])
        ).update({'status': 'cancelled'}, synchronize_session=False)
        
        db.commit()
        
        # Delete ChromaDB collection
        if chroma_client:
            collection_name = f"repo_{repo_id}_chunks"
            try:
                chroma_client.delete_collection(name=collection_name)
                print(f"✅ Deleted ChromaDB collection: {collection_name}")
            except Exception as e:
                print(f"ℹ️  No ChromaDB collection to delete: {e}")
        
        return {
            "message": "Index cleared successfully",
            "files_deleted": files_count,
            "chunks_deleted": chunks_count,
            "symbols_deleted": symbols_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear index: {str(e)}"
        )


@router.get("/index/stats")
async def get_index_stats(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    Get statistics about the current index.
    """
    files_count = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).count()
    chunks_count = db.query(CodeChunk).filter(CodeChunk.repo_id == repo_id).count()
    symbols_count = db.query(Symbol).filter(Symbol.repo_id == repo_id).count()
    
    # Get latest index job
    latest_job = db.query(IndexJob).filter(
        IndexJob.repo_id == repo_id
    ).order_by(IndexJob.created_at.desc()).first()
    
    # Check ChromaDB
    collection_name = f"repo_{repo_id}_chunks"
    collection_exists = False
    collection_count = 0
    
    if chroma_client:
        try:
            collection = chroma_client.get_collection(name=collection_name)
            collection_exists = True
            collection_count = collection.count()
        except Exception:
            pass
    
    return {
        "repo_id": repo_id,
        "files_indexed": files_count,
        "chunks_created": chunks_count,
        "symbols_extracted": symbols_count,
        "embeddings_count": collection_count,
        "is_indexed": files_count > 0 and chunks_count > 0,
        "has_embeddings": collection_exists and collection_count > 0,
        "last_indexed_at": latest_job.completed_at if latest_job else None,
        "last_index_status": latest_job.status if latest_job else None
    }
    

@router.get("/repo/{id}/file/{file_id}/content")
async def get_file_content_by_id(
    repo_id: int,
    file_id: int,
    start: Optional[int] = Query(None, description="Start line (1-indexed)"),
    end: Optional[int] = Query(None, description="End line (1-indexed)"),
    context: int = Query(default=5, description="Context lines around selection"),
    db: Session = Depends(get_db)
):
    """
    Get file content by file ID.
    
    Args:
        repo_id: Repository ID
        file_id: File ID (from database)
        start: Optional start line
        end: Optional end line
        context: Context lines to include
    
    Returns:
        File content with metadata
    """
    # Get the file
    file = db.query(CodeFile).filter(
        CodeFile.id == file_id,
        CodeFile.repo_id == repo_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=404, 
            detail=f"File with ID {file_id} not found in repository {repo_id}"
        )
    
    # If no line range specified, return entire file
    if start is None and end is None:
        return {
            "file_id": file.id,
            "file_path": file.file_path,
            "language": file.language,
            "content": file.content,
            "start_line": 1,
            "end_line": len(file.content.split('\n')),
            "total_lines": len(file.content.split('\n')),
            "metadata": file.file_metadata
        }
    
    # Extract line range with context
    lines = file.content.split('\n')
    total_lines = len(lines)
    
    # Add context lines
    actual_start = max(1, (start or 1) - context)
    actual_end = min(total_lines, (end or total_lines) + context)
    
    # Extract lines (convert to 0-indexed)
    selected_lines = lines[actual_start - 1:actual_end]
    content_with_context = '\n'.join(selected_lines)
    
    return {
        "file_id": file.id,
        "file_path": file.file_path,
        "language": file.language,
        "content": content_with_context,
        "start_line": actual_start,
        "end_line": actual_end,
        "total_lines": total_lines,
        "metadata": file.file_metadata,
        "highlight_start": start,
        "highlight_end": end
    }