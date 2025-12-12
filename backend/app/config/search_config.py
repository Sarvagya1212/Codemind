# backend/app/config/search_config.py

from typing import List

class SearchConfig:
    """Configuration for search feature"""
    
    # Ranking weights
    SEMANTIC_WEIGHT: float = 0.6  # α
    KEYWORD_WEIGHT: float = 0.3   # β
    SYMBOL_WEIGHT: float = 0.1    # γ
    
    # Search parameters
    SEMANTIC_TOP_K: int = 50
    KEYWORD_TOP_K: int = 50
    SYMBOL_TOP_K: int = 20
    FINAL_TOP_N: int = 20
    
    # Chunking parameters
    CHUNK_SIZE: int = 800        # tokens
    CHUNK_OVERLAP: int = 200     # tokens
    MAX_CHUNK_SIZE: int = 2000   # tokens
    
    # Symbol extraction
    EXTRACT_SYMBOLS: bool = True
    SYMBOL_TYPES: List[str] = [
        "function", "class", "method",
        "variable", "constant", "interface"
    ]
    
    # Performance
    CACHE_TTL: int = 3600              # 1 hour
    REGEX_TIMEOUT: int = 5             # seconds
    MAX_REGEX_MATCHES: int = 1000
    BATCH_SIZE: int = 100
    
    # Security
    IGNORE_PATTERNS: List[str] = [
        ".env", ".env.*", "*.pem", "*.key",
        "node_modules/**", ".git/**", "__pycache__/**",
        "*.pyc", "*.min.js", "*.bundle.js"
    ]
    REDACT_SECRETS: bool = True
    
    # Indexing
    MAX_FILE_SIZE_MB: int = 5
    INCREMENTAL_INDEXING: bool = True


# Global instance
search_config = SearchConfig()