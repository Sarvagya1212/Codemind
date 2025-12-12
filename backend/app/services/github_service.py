# backend/app/services/github_service.py
import os
import shutil
import tempfile
from typing import Dict, Optional
from git import Repo, GitCommandError
from urllib.parse import urlparse


def extract_repo_info(github_url: str) -> Dict[str, str]:
    """
    Extract repository information from GitHub URL.
    
    Args:
        github_url: GitHub repository URL
        
    Returns:
        Dictionary with owner, repo_name, and full_name
    """
    # Parse URL
    parsed = urlparse(github_url)
    path_parts = parsed.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {github_url}")
    
    owner = path_parts[0]
    repo_name = path_parts[1].replace('.git', '')
    
    return {
        "owner": owner,
        "repo_name": repo_name,
        "full_name": f"{owner}/{repo_name}"
    }


def clone_repository(github_url: str, target_dir: Optional[str] = None) -> str:
    """
    Clone a GitHub repository to a local directory.
    
    Args:
        github_url: GitHub repository URL (https://github.com/owner/repo)
        target_dir: Optional target directory. If None, creates a temp directory.
        
    Returns:
        Path to the cloned repository directory
        
    Raises:
        ValueError: If the URL is invalid
        GitCommandError: If cloning fails
    """
    try:
        # Extract repo info
        repo_info = extract_repo_info(github_url)
        
        # Create target directory
        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix=f"codemind_{repo_info['repo_name']}_")
        else:
            os.makedirs(target_dir, exist_ok=True)
        
        print(f"📥 Cloning repository: {repo_info['full_name']}")
        print(f"📂 Target directory: {target_dir}")
        
        # Clone the repository
        Repo.clone_from(
            github_url,
            target_dir,
            depth=1  # Shallow clone for faster download
        )
        
        print(f"✅ Repository cloned successfully to: {target_dir}")
        return target_dir
        
    except GitCommandError as e:
        print(f"❌ Git error while cloning: {str(e)}")
        raise Exception(f"Failed to clone repository: {str(e)}")
    except Exception as e:
        print(f"❌ Error cloning repository: {str(e)}")
        raise


def cleanup_repository(repo_path: str) -> None:
    """
    Remove a cloned repository directory.
    
    Args:
        repo_path: Path to the repository directory to remove
    """
    try:
        if os.path.exists(repo_path):
            # On Windows, we need to handle read-only files
            def handle_remove_readonly(func, path, exc):
                """Error handler for Windows readonly files"""
                import stat
                if not os.access(path, os.W_OK):
                    os.chmod(path, stat.S_IWUSR)
                    func(path)
                else:
                    raise
            
            shutil.rmtree(repo_path, onerror=handle_remove_readonly)
            print(f"🗑️  Cleaned up repository at: {repo_path}")
    except Exception as e:
        print(f"⚠️  Warning: Failed to cleanup repository at {repo_path}: {str(e)}")


def get_repo_metadata(github_url: str) -> Dict:
    """
    Get repository metadata from GitHub.
    
    Args:
        github_url: GitHub repository URL
        
    Returns:
        Dictionary with repository metadata
    """
    repo_info = extract_repo_info(github_url)
    
    # Basic metadata (can be enhanced with GitHub API later)
    metadata = {
        "owner": repo_info["owner"],
        "repo_name": repo_info["repo_name"],
        "full_name": repo_info["full_name"],
        "url": github_url
    }
    
    return metadata