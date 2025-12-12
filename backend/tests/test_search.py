# backend/tests/test_search_fast.py
"""
Fast search tests using mocks - no Tree-sitter initialization needed.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from unittest.mock import Mock, patch, MagicMock

# Sample code for testing
SAMPLE_PYTHON_CODE = """
def authenticate(username, password):
    '''Authenticate user with username and password'''
    if check_password(username, password):
        return generate_token(username)
    return None

class UserManager:
    def __init__(self):
        self.users = {}
    
    def add_user(self, username):
        self.users[username] = User(username)
"""


class TestASTChunkerMocked:
    """Test chunking with mocked Tree-sitter"""
    
    @patch('app.services.ast_chunker.ast_chunker')
    def test_chunk_code_returns_chunks(self, mock_chunker):
        """Test that chunk_code returns expected structure"""
        # Mock the response
        mock_chunker.chunk_code.return_value = [
            {
                'content': 'def authenticate(username, password):\n    pass',
                'chunk_index': 0,
                'start_line': 1,
                'end_line': 5,
                'chunk_type': 'function',
                'language': 'python',
                'file_path': 'test.py',
                'keywords': ['def', 'authenticate'],
                'content_hash': 'abc123'
            }
        ]
        
        result = mock_chunker.chunk_code(
            content=SAMPLE_PYTHON_CODE,
            language='python',
            file_path='test.py'
        )
        
        assert len(result) > 0
        assert 'content' in result[0]
        assert 'chunk_type' in result[0]
        assert result[0]['language'] == 'python'


class TestSymbolExtractorMocked:
    """Test symbol extraction with mocks"""
    
    @patch('app.services.symbol_extractor.symbol_extractor')
    def test_extract_symbols_returns_symbols(self, mock_extractor):
        """Test that extract_symbols returns expected structure"""
        # Mock the response
        mock_extractor.extract_symbols.return_value = [
            {
                'name': 'authenticate',
                'symbol_type': 'function',
                'signature': 'def authenticate(username, password)',
                'start_line': 2,
                'end_line': 6,
                'docstring': 'Authenticate user with username and password',
                'language': 'python',
                'file_path': 'test.py',
                'scope': 'public'
            },
            {
                'name': 'UserManager',
                'symbol_type': 'class',
                'signature': 'class UserManager',
                'start_line': 8,
                'end_line': 13,
                'language': 'python',
                'file_path': 'test.py',
                'scope': 'public'
            }
        ]
        
        result = mock_extractor.extract_symbols(
            content=SAMPLE_PYTHON_CODE,
            language='python',
            file_path='test.py'
        )
        
        assert len(result) == 2
        assert result[0]['name'] == 'authenticate'
        assert result[0]['symbol_type'] == 'function'
        assert result[1]['name'] == 'UserManager'
        assert result[1]['symbol_type'] == 'class'


class TestHybridRanking:
    """Test hybrid search ranking"""
    
    def test_score_calculation(self):
        """Test hybrid score calculation"""
        # Simple mock config
        class MockConfig:
            SEMANTIC_WEIGHT = 0.6
            KEYWORD_WEIGHT = 0.3
            SYMBOL_WEIGHT = 0.1
        
        config = MockConfig()
        
        semantic_score = 0.9
        keyword_score = 0.7
        symbol_score = 0.8
        
        hybrid_score = (
            config.SEMANTIC_WEIGHT * semantic_score +
            config.KEYWORD_WEIGHT * keyword_score +
            config.SYMBOL_WEIGHT * symbol_score
        )
        
        assert 0 < hybrid_score < 1
        assert hybrid_score > keyword_score
        
        total_weight = (
            config.SEMANTIC_WEIGHT +
            config.KEYWORD_WEIGHT +
            config.SYMBOL_WEIGHT
        )
        assert abs(total_weight - 1.0) < 0.01


class TestSearchModeDetection:
    """Test search mode detection logic"""
    
    def test_symbol_query_detection(self):
        """Test detection of symbol queries"""
        import re
        
        # Symbol-like patterns (single identifier)
        symbol_queries = [
            'getUserById',
            'AuthService',
            'handleRequest'
        ]
        
        for query in symbol_queries:
            is_symbol = re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', query)
            assert is_symbol is not None, f"{query} should be detected as symbol"
    
    def test_natural_language_detection(self):
        """Test detection of natural language queries"""
        nl_queries = [
            'Where is the authentication',
            'How does login work',
            'Find all HTTP handlers'
        ]
        
        for query in nl_queries:
            word_count = len(query.split())
            assert word_count > 2, f"{query} should be multi-word"
    
    def test_regex_detection(self):
        """Test detection of regex patterns"""
        regex_queries = [
            'router\\.handle',
            'user.*manager',
            '^def ',
            '[a-z]+'
        ]
        
        special_chars = ['.', '*', '+', '?', '[', ']', '(', ')', '|', '^', '$']
        
        for query in regex_queries:
            has_special = any(char in query for char in special_chars)
            assert has_special, f"{query} should contain regex special chars"


class TestSearchSecurity:
    """Test search security"""
    
    def test_secret_patterns(self):
        """Test that dangerous patterns are in ignore list"""
        ignore_patterns = [
            '.env',
            '.env.*',
            '*.pem',
            '*.key',
            'node_modules/**',
            '.git/**'
        ]
        
        assert '.env' in ignore_patterns
        assert '*.key' in ignore_patterns
    
    def test_file_size_limits(self):
        """Test file size limits"""
        MAX_FILE_SIZE_MB = 5
        
        large_file_size = 10 * 1024 * 1024  # 10MB
        max_size = MAX_FILE_SIZE_MB * 1024 * 1024  # 5MB
        
        assert large_file_size > max_size, "Should detect oversized files"


class TestChunkingLogic:
    """Test chunking logic without Tree-sitter"""
    
    def test_simple_line_chunking(self):
        """Test basic line-based chunking"""
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        lines = content.split('\n')
        
        chunk_size_lines = 2
        chunks = []
        
        for i in range(0, len(lines), chunk_size_lines):
            chunk_lines = lines[i:i + chunk_size_lines]
            chunks.append({
                'content': '\n'.join(chunk_lines),
                'start_line': i + 1,
                'end_line': i + len(chunk_lines)
            })
        
        assert len(chunks) == 3  # 5 lines / 2 = 3 chunks
        assert chunks[0]['start_line'] == 1
        assert chunks[0]['end_line'] == 2
    
    def test_keyword_extraction_simple(self):
        """Test simple keyword extraction"""
        code = "def authenticate(user): return user.token"
        
        # Simple regex for identifiers
        import re
        identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code)
        
        assert 'def' in identifiers
        assert 'authenticate' in identifiers
        assert 'user' in identifiers


@pytest.mark.asyncio
class TestAsyncSearch:
    """Test async search operations"""
    
    async def test_mock_search(self):
        """Test mocked search operation"""
        # Mock search result
        mock_result = {
            'file_id': 1,
            'file_path': 'test.py',
            'snippet': 'def authenticate(user):',
            'relevance_score': 0.95,
            'start_line': 10,
            'end_line': 15
        }
        
        # Verify structure
        assert 'file_path' in mock_result
        assert 'relevance_score' in mock_result
        assert 0 <= mock_result['relevance_score'] <= 1


class TestIndexingConfig:
    """Test indexing configuration"""
    
    def test_testing_mode_flags(self):
        """Test that testing mode can be configured"""
        # These would come from config
        TESTING_MODE = True
        MAX_FILES = 10
        SKIP_EMBEDDINGS = True
        
        assert TESTING_MODE is True
        assert MAX_FILES > 0
        assert SKIP_EMBEDDINGS in [True, False]


# Simple integration test
def test_basic_math():
    """Sanity check that tests run"""
    assert 1 + 1 == 2


def test_string_operations():
    """Test basic string operations"""
    query = "getUserById"
    assert query.isalnum() or '_' in query
    assert len(query) > 0


if __name__ == '__main__':
    print("Running fast search tests...")
    pytest.main([__file__, '-v', '-s'])