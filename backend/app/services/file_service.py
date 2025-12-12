# backend/app/services/file_service.py

import os
from typing import List, Optional, Dict
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Repository, RepositoryFile
from app.schemas.repository import FileTreeNode, FileContentResponse
from app.services.code_parser import detect_language

class FileService:
    
    @staticmethod
    def scan_repository_files(repo_id: int, repo_path: str, db: Session) -> List[RepositoryFile]:
        """
        Scans the repository directory and stores file metadata in the database.
        Called during ingestion pipeline after cloning.
        
        Args:
            repo_id: Repository ID
            repo_path: Local path to cloned repository
            db: Database session
            
        Returns:
            List of created RepositoryFile objects
        """
        print(f"📂 Scanning file structure for repo {repo_id}...")
        
        if not os.path.exists(repo_path):
            raise Exception(f"Repository path does not exist: {repo_path}")
        
        # Delete existing file records for this repo
        db.query(RepositoryFile).filter(RepositoryFile.repo_id == repo_id).delete()
        db.commit()
        
        files_to_create = []
        repo_path_obj = Path(repo_path)
        
        # Walk through directory tree
        for root, dirs, files in os.walk(repo_path):
            # Skip .git and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__'}]
            
            root_path = Path(root)
            relative_root = root_path.relative_to(repo_path_obj)
            
            # Add directories
            for dir_name in dirs:
                dir_relative_path = str(relative_root / dir_name) if str(relative_root) != "." else dir_name
                parent = str(relative_root) if str(relative_root) != "." else None
                
                files_to_create.append(RepositoryFile(
                    repo_id=repo_id,
                    file_path=dir_relative_path,
                    file_name=dir_name,
                    file_type="directory",
                    is_directory=True,
                    parent_path=parent,
                    size_bytes=0
                ))
            
            # Add files
            for file_name in files:
                if file_name.startswith('.'):
                    continue
                    
                file_path = root_path / file_name
                file_relative_path = str(file_path.relative_to(repo_path_obj))
                parent = str(relative_root) if str(relative_root) != "." else None
                
                # Get file extension and size
                extension = file_path.suffix.lstrip('.') if file_path.suffix else "txt"
                file_size = file_path.stat().st_size if file_path.exists() else 0
                
                files_to_create.append(RepositoryFile(
                    repo_id=repo_id,
                    file_path=file_relative_path,
                    file_name=file_name,
                    file_type=extension,
                    is_directory=False,
                    parent_path=parent,
                    size_bytes=file_size
                ))
        
        # Bulk insert
        db.bulk_save_objects(files_to_create)
        db.commit()
        
        print(f"✅ Scanned {len(files_to_create)} files and directories")
        return files_to_create
    
    @staticmethod
    def get_file_tree(repo_id: int, db: Session) -> FileTreeNode:
        """
        Returns hierarchical file tree structure for the repository.
        
        Args:
            repo_id: Repository ID
            db: Database session
            
        Returns:
            Root FileTreeNode with nested children
        """
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        files = db.query(RepositoryFile).filter(
            RepositoryFile.repo_id == repo_id
        ).all()
        
        if not files:
            # Trigger file scan if not done yet
            if repo.local_path and os.path.exists(repo.local_path):
                FileService.scan_repository_files(repo_id, repo.local_path, db)
                files = db.query(RepositoryFile).filter(
                    RepositoryFile.repo_id == repo_id
                ).all()
            else:
                raise HTTPException(
                    status_code=404, 
                    detail="Repository files not found. Repository may need re-ingestion."
                )
        
        # Build tree structure
        repo_name = repo.repo_metadata.get('repo_name', 'repository') if repo.repo_metadata else 'repository'
        return FileService._build_tree(files, repo_name)
    
    @staticmethod
    def _build_tree(files: List[RepositoryFile], root_name: str) -> FileTreeNode:
        """
        Builds a hierarchical tree from flat file list.
        
        Args:
            files: List of RepositoryFile objects
            root_name: Name for the root node
            
        Returns:
            Root FileTreeNode with complete tree structure
        """
        # Create lookup dictionary
        file_dict = {}
        root = FileTreeNode(
            name=root_name,
            path="",
            type="directory",
            children=[]
        )
        file_dict[""] = root
        file_dict[None] = root  # Handle None parent_path
        
        # Sort by path depth to ensure parents are created before children
        sorted_files = sorted(files, key=lambda f: f.file_path.count('/'))
        
        for file in sorted_files:
            node = FileTreeNode(
                name=file.file_name,
                path=file.file_path,
                type="directory" if file.is_directory else "file",
                extension=file.file_type if not file.is_directory else None,
                size=file.size_bytes,
                children=[] if file.is_directory else None
            )
            
            file_dict[file.file_path] = node
            
            # Find parent and attach
            parent_path = file.parent_path if file.parent_path else None
            if parent_path in file_dict:
                file_dict[parent_path].children.append(node)
        
        return root
    
    @staticmethod
    def get_file_content(repo_id: int, file_path: str, db: Session) -> FileContentResponse:
        """
        Returns the content of a specific file.
        
        Args:
            repo_id: Repository ID
            file_path: Relative file path from repository root
            db: Database session
            
        Returns:
            FileContentResponse with file content and metadata
        """
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if not repo.local_path:
            raise HTTPException(
                status_code=400, 
                detail="Repository local path not found. Repository may need re-ingestion."
            )
        
        # Security: prevent path traversal attacks
        safe_path = Path(file_path).as_posix()
        if ".." in safe_path or safe_path.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        full_path = Path(repo.local_path) / safe_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if full_path.is_dir():
            raise HTTPException(status_code=400, detail="Cannot read directory as file")
        
        try:
            # Try UTF-8 first, fallback to latin-1 for binary-ish files
            try:
                content = full_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = full_path.read_text(encoding='latin-1')
            
            # Determine language for syntax highlighting
            language = detect_language(str(full_path)) or 'plaintext'
            
            return FileContentResponse(
                file_path=safe_path,
                content=content,
                language=language,
                size_bytes=len(content.encode('utf-8')),
                lines=len(content.splitlines())
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading file: {str(e)}"
            )
