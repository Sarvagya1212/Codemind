# backend/app/services/code_parser.py

import os
from typing import List, Dict, Optional
from pathlib import Path


# File extensions to language mapping
LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.r': 'r',
    '.m': 'objective-c',
    '.sql': 'sql',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.md': 'markdown',
    '.txt': 'text',
    '.vue': 'vue',
    '.dart': 'dart',
}

# Directories to ignore
IGNORE_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__', 
    '.pytest_cache', 'dist', 'build', '.next', '.nuxt',
    'target', 'bin', 'obj', '.idea', '.vscode', 'coverage',
    '.DS_Store', 'vendor', 'packages'
}

# Files to ignore
IGNORE_FILES = {
    '.gitignore', '.dockerignore', '.env', '.env.local',
    'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock',
    'LICENSE', 'CHANGELOG'
}


def detect_language(file_path: str) -> Optional[str]:
    """
    Detect programming language from file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language name or None if unknown
    """
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext)


def should_ignore(path: str, is_dir: bool = False) -> bool:
    """
    Check if a path should be ignored.
    
    Args:
        path: Path to check
        is_dir: Whether the path is a directory
        
    Returns:
        True if should be ignored
    """
    name = os.path.basename(path)
    
    if is_dir:
        return name in IGNORE_DIRS
    else:
        return name in IGNORE_FILES or name.startswith('.')


def read_file_content(file_path: str, max_size_mb: int = 1) -> Optional[str]:
    """
    Read file content safely.
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum file size in MB
        
    Returns:
        File content or None if unable to read
    """
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            print(f"⚠️  Skipping large file (>{max_size_mb}MB): {file_path}")
            return None
        
        # Try to read as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return content
            
    except Exception as e:
        print(f"⚠️  Could not read file {file_path}: {str(e)}")
        return None


def parse_repository_files(repo_path: str) -> List[Dict]:
    """
    Parse all code files in a repository.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        List of dictionaries containing file information:
        {
            'file_path': relative path,
            'content': file content,
            'language': detected language,
            'metadata': {
                'size': file size in bytes,
                'lines': number of lines
            }
        }
    """
    parsed_files = []
    total_files = 0
    skipped_files = 0
    
    print(f"📖 Parsing repository: {repo_path}")
    
    # Walk through the repository
    for root, dirs, files in os.walk(repo_path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(d, is_dir=True)]
        
        for file in files:
            total_files += 1
            
            # Skip ignored files
            if should_ignore(file):
                skipped_files += 1
                continue
            
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Detect language
            language = detect_language(file_path)
            if not language:
                skipped_files += 1
                continue
            
            # Read file content
            content = read_file_content(file_path)
            if not content:
                skipped_files += 1
                continue
            
            # Calculate metadata
            file_size = os.path.getsize(file_path)
            line_count = content.count('\n') + 1
            
            parsed_files.append({
                'file_path': relative_path,
                'content': content,
                'language': language,
                'metadata': {
                    'size': file_size,
                    'lines': line_count,
                    'extension': Path(file_path).suffix
                }
            })
            
            print(f"✅ Parsed: {relative_path} ({language})")
    
    print(f"\n📊 Parsing Summary:")
    print(f"   Total files found: {total_files}")
    print(f"   Files parsed: {len(parsed_files)}")
    print(f"   Files skipped: {skipped_files}")
    
    return parsed_files


def chunk_code(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split code content into overlapping chunks for embedding.
    
    Args:
        content: Code content to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of code chunks
    """
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks