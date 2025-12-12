# backend/app/routers/files.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.file_service import FileService
from app.schemas.repository import FileTreeNode, FileContentResponse

router = APIRouter(
    prefix="/repos/{repo_id}/files",
    tags=["files"]
)

@router.get("/tree", response_model=FileTreeNode)
def get_file_tree(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns the complete file tree structure for the repository.
    
    **Response Structure:**
    - Hierarchical tree with nested children
    - Directories have `children` array
    - Files have `extension` and `size` properties
    """
    try:
        return FileService.get_file_tree(repo_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file tree: {str(e)}"
        )

@router.get("/content", response_model=FileContentResponse)
def get_file_content(
    repo_id: int,
    path: str,
    db: Session = Depends(get_db)
):
    """
    Returns the content of a specific file.
    
    **Query Parameters:**
    - `path`: Relative file path from repository root (e.g., "src/main.py")
    
    **Response:**
    - File content as text
    - Language identifier for syntax highlighting
    - File metadata (size, line count)
    """
    try:
        return FileService.get_file_content(repo_id, path, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file content: {str(e)}"
        )

@router.post("/rescan")
def rescan_repository_files(
    repo_id: int,
    db: Session = Depends(get_db)
):
    """
    Rescans the repository directory and updates file metadata.
    Useful after repository updates.
    """
    try:
        from app.models import Repository
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if not repo.local_path or not os.path.exists(repo.local_path):
            raise HTTPException(
                status_code=400,
                detail="Repository local path not available"
            )
        
        files = FileService.scan_repository_files(repo_id, repo.local_path, db)
        return {
            "message": "Repository files rescanned successfully",
            "files_count": len(files)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rescan repository: {str(e)}"
        )
