# backend/app/services/ast_chunker.py
import hashlib
import re
from typing import List, Dict

from app.config.search_config import search_config

class ASTChunker:
    """
    Simple line-based code chunker.
    """
    
    def __init__(self):
        print("⚙️  AST Chunker initialized (line-based chunking)")
    
    def chunk_code(self, content: str, language: str, file_path: str) -> List[Dict]:
        """
        Chunk code into overlapping segments for better semantic search.
        
        New approach: Use fixed line-based chunking (30 lines per chunk, 10 line overlap)
        This creates multiple chunks per file for better granularity.
        """
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Fixed chunk size: 30 lines per chunk with 10 line overlap
        # This handles most function/class definitions well
        chunk_size_lines = 30
        overlap_lines = 10  # 33% overlap for context continuity
        
        chunks = []
        chunk_index = 0
        
        print(f"  Chunking {file_path}: {total_lines} lines")
        
        # Slide window across file
        start = 0
        while start < total_lines:
            end = min(start + chunk_size_lines, total_lines)
            chunk_lines = lines[start:end]
            chunk_content = '\n'.join(chunk_lines)
            
            # Skip empty chunks
            if not chunk_content.strip():
                start += chunk_size_lines - overlap_lines
                continue
            
            # Calculate content hash for incremental indexing
            content_hash = hashlib.sha256(
                chunk_content.encode('utf-8')
            ).hexdigest()
            
            # Extract keywords for text search
            keywords = self._extract_keywords(chunk_content, language)
            
            chunks.append({
                'content': chunk_content,
                'chunk_index': chunk_index,
                'start_line': start + 1,  # 1-indexed for display
                'end_line': end,
                'chunk_type': 'block',
                'language': language,
                'file_path': file_path,
                'keywords': keywords,
                'content_hash': content_hash
            })
            
            chunk_index += 1
            
            # Slide window with overlap (move forward by chunk_size - overlap)
            start += chunk_size_lines - overlap_lines
        
        print(f"  ✓ Created {len(chunks)} chunks for {file_path}")
        return chunks 
    def _extract_keywords(self, content: str, language: str) -> List[str]:
        """Extract keywords from code"""
        LANGUAGE_KEYWORDS = {
            'python': ['def', 'class', 'import', 'from', 'async', 'await'],
            'javascript': ['function', 'class', 'const', 'let', 'import', 'export'],
            'typescript': ['function', 'class', 'interface', 'type', 'const', 'let'],
            'java': ['class', 'interface', 'public', 'private', 'static'],
            'go': ['func', 'type', 'struct', 'interface', 'var', 'const'],
            'php': ['function', 'class', 'public', 'private', 'protected'],
            'css': ['class', 'id', 'style'],
            'sql': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE']
        }
        
        keywords = []
        
        # Extract language keywords
        lang_keywords = LANGUAGE_KEYWORDS.get(language, [])
        for keyword in lang_keywords:
            if keyword in content:
                keywords.append(keyword)
        
        # Extract identifiers
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content)
        
        # Filter and limit
        common_words = {'the', 'and', 'or', 'if', 'else', 'for', 'while', 'do', 'return'}
        unique_identifiers = set(
            id for id in identifiers
            if id not in common_words and len(id) > 2
        )
        
        keywords.extend(list(unique_identifiers)[:20])
        
        return keywords


# Singleton instance
ast_chunker = ASTChunker()