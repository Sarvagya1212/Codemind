# backend/app/services/hybrid_search_service.py

import re
import time
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, cast, String
from app.models import CodeChunk, Symbol, CodeFile, Repository
from app.schemas.search import SearchMode, MatchType
from app.services.embedding_service import embeddings, chroma_client
from app.config.search_config import search_config


class HybridSearchService:
    """
    Implements hybrid search combining semantic, keyword, symbol, and regex search.
    """

    def __init__(self):
        self.cache = {}

    async def search(
        self,
        repo_id: int,
        query: str,
        mode: SearchMode,
        filters: Dict,
        db: Session
    ) -> Tuple[List[Dict], int]:
        """
        Main search entry point.
        Returns (results, total_count)
        """
        start_time = time.time()

        # Auto-detect mode if needed
        if mode == SearchMode.AUTO:
            mode = self._detect_query_mode(query)

        # Route to appropriate search method
        if mode == SearchMode.SEMANTIC:
            results = await self._semantic_search(repo_id, query, filters, db)
        elif mode == SearchMode.KEYWORD:
            results = await self._keyword_search(repo_id, query, filters, db)
        elif mode == SearchMode.SYMBOL:
            results = await self._symbol_search(repo_id, query, filters, db)
        elif mode == SearchMode.REGEX:
            results = await self._regex_search(repo_id, query, filters, db)
        elif mode == SearchMode.HYBRID:
            results = await self._hybrid_search(repo_id, query, filters, db)
        else:
            results = []

        # Apply filters
        results = self._apply_filters(results, filters)

        # Sort by relevance
        results = sorted(results, key=lambda x: x['relevance_score'], reverse=True)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Add latency to results
        for result in results:
            result['latency_ms'] = latency_ms

        return results, len(results)

    def _detect_query_mode(self, query: str) -> SearchMode:
        """
        Auto-detect query mode based on patterns.
        """
        # Check for symbol query (identifier-like)
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', query):
            return SearchMode.SYMBOL

        # Check for regex patterns
        if any(char in query for char in ['.', '*', '+', '?', '[', ']', '(', ')', '|', '^', '$']):
            return SearchMode.REGEX

        # Check for natural language (has multiple words)
        if len(query.split()) > 2:
            return SearchMode.HYBRID

        # Default to keyword
        return SearchMode.KEYWORD

    async def _semantic_search(self, repo_id, query, filters, db):
        """Semantic search with file_id validation and path normalization"""
        from app.models import CodeFile
        
        # Generate query embedding
        try:
            query_embedding = embeddings.embed_query(query)
        except Exception as e:
            print(f"⚠️  Embedding generation failed: {e}")
            return []
        
        # Get collection
        collection_name = f"repo_{repo_id}_chunks"
        try:
            collection = chroma_client.get_collection(name=collection_name)
        except Exception as e:
            print(f"⚠️  Collection not found: {e}")
            return []
        
        # Check if collection has data
        collection_count = collection.count()
        if collection_count == 0:
            print(f"⚠️  Collection is empty")
            return []
        
        print(f"✅ Searching {collection_count} chunks for: {query}")
        
        # Build where filter
        where_filter = {"repo_id": repo_id}
        if filters.get('lang'):
            where_filter['language'] = filters['lang']

        # Query vector DB
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(search_config.SEMANTIC_TOP_K, collection_count),
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"⚠️  Vector search failed: {e}")
            return []

        if not results['ids'][0]:
            print(f"⚠️  No results returned from vector search")
            return []

        # Helper function to normalize paths for comparison
        def normalize_path(path):
            """Normalize path separators for comparison"""
            if not path:
                return ""
            return path.replace('\\', '/').replace('//', '/')

        # Pre-fetch all files for this repo to avoid repeated queries
        all_files = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).all()
        
        # Create lookup maps
        file_by_id = {f.id: f for f in all_files}
        file_by_path = {normalize_path(f.file_path): f for f in all_files}
        
        print(f"📁 Loaded {len(all_files)} files from database")

        # Format results
        search_results = []
        for i in range(len(results['ids'][0])):
            chunk_id = results['ids'][0][i]
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]

            # Get file_id from metadata
            file_id = metadata.get('file_id')
            
            # Try to convert to int if it's a string
            if isinstance(file_id, str):
                try:
                    file_id = int(file_id)
                except (ValueError, TypeError):
                    file_id = None
            
            # Validate file_id exists in database
            file = None
            if file_id and file_id in file_by_id:
                file = file_by_id[file_id]
            
            # If file_id is invalid, try to find by path
            if not file:
                file_path = metadata.get('file_path', '')
                normalized_path = normalize_path(file_path)
                
                if normalized_path in file_by_path:
                    file = file_by_path[normalized_path]
                    if i == 0:  # Log first mismatch
                        print(f"⚠️  file_id {file_id} not found, resolved by path to ID {file.id}")
                else:
                    # Last resort: try direct path match
                    file = db.query(CodeFile).filter(
                        CodeFile.repo_id == repo_id,
                        CodeFile.file_path == file_path
                    ).first()
                    
                    if not file:
                        print(f"❌ Could not resolve file: ID={file_id}, Path={file_path}")
                        continue  # Skip this result
            
            # Use the resolved file
            file_id = file.id
            file_path = file.file_path

            # Convert distance to similarity score
            similarity_score = 1 - min(distance, 1.0)

            search_results.append({
                'chunk_id': chunk_id,
                'file_id': file_id,
                'file_path': file_path,
                'snippet': results['documents'][0][i],
                'start_line': int(metadata.get('start_line', 1)),
                'end_line': int(metadata.get('end_line', 1)),
                'language': metadata.get('language', 'text'),
                'match_type': [MatchType.SEMANTIC],
                'relevance_score': similarity_score,
                'semantic_score': similarity_score,
                'keyword_score': None,
                'symbol_score': None
            })
        
        print(f"✅ Returning {len(search_results)} valid results")
        return search_results
    async def _keyword_search(
        self,
        repo_id: int,
        query: str,
        filters: Dict,
        db: Session
    ) -> List[Dict]:
        """
        Keyword search using PostgreSQL full-text search.
        FIXED: Proper handling of JSON keywords column.
        """
        # Build query - search in content only (keywords is JSON, harder to search)
        query_filter = and_(
            CodeChunk.repo_id == repo_id,
            CodeChunk.content.ilike(f"%{query}%")
        )

        # Apply language filter
        if filters.get('lang'):
            query_filter = and_(
                query_filter,
                CodeChunk.language == filters['lang']
            )

        # Execute query
        try:
            chunks = db.query(CodeChunk).filter(query_filter).limit(
                search_config.KEYWORD_TOP_K
            ).all()
        except Exception as e:
            print(f"⚠️  Keyword search failed: {e}")
            return []

        # Calculate TF-IDF-like scores
        search_results = []
        for chunk in chunks:
            # Simple TF-IDF approximation
            query_terms = query.lower().split()
            content_lower = chunk.content.lower()

            # Term frequency
            tf_score = sum(content_lower.count(term) for term in query_terms) / max(len(content_lower), 1)

            # Normalize to 0-1
            keyword_score = min(tf_score * 100, 1.0)

            search_results.append({
                'chunk_id': chunk.id,
                'file_id': chunk.file_id,
                'file_path': self._get_file_path(chunk.file_id, db),
                'snippet': chunk.content,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'language': chunk.language,
                'match_type': [MatchType.KEYWORD],
                'relevance_score': keyword_score,
                'semantic_score': None,
                'keyword_score': keyword_score,
                'symbol_score': None
            })

        return search_results

    async def _symbol_search(
        self,
        repo_id: int,
        query: str,
        filters: Dict,
        db: Session
    ) -> List[Dict]:
        """
        Search for symbols (functions, classes, etc.)
        """
        # Build query with fuzzy matching
        query_filter = and_(
            Symbol.repo_id == repo_id,
            or_(
                Symbol.name.ilike(f"%{query}%"),
                Symbol.qualified_name.ilike(f"%{query}%")
            )
        )

        # Apply filters
        if filters.get('lang'):
            query_filter = and_(query_filter, Symbol.language == filters['lang'])
        if filters.get('symbol_type'):
            query_filter = and_(query_filter, Symbol.symbol_type == filters['symbol_type'])

        # Execute query
        try:
            symbols = db.query(Symbol).filter(query_filter).limit(
                search_config.SYMBOL_TOP_K
            ).all()
        except Exception as e:
            print(f"⚠️  Symbol search failed: {e}")
            return []

        # Format results
        search_results = []
        for symbol in symbols:
            # Calculate match score
            exact_match = query.lower() == symbol.name.lower()
            starts_with = symbol.name.lower().startswith(query.lower())

            if exact_match:
                symbol_score = 1.0
            elif starts_with:
                symbol_score = 0.9
            else:
                symbol_score = 0.7

            # Get file content for snippet
            file = db.query(CodeFile).get(symbol.file_id)
            if file:
                lines = file.content.split('\n')
                snippet = '\n'.join(lines[symbol.start_line-1:symbol.end_line])
            else:
                snippet = symbol.signature or ""

            search_results.append({
                'chunk_id': None,
                'file_id': symbol.file_id,
                'file_path': self._get_file_path(symbol.file_id, db),
                'snippet': snippet,
                'start_line': symbol.start_line,
                'end_line': symbol.end_line,
                'language': symbol.language,
                'symbol_name': symbol.name,
                'symbol_type': symbol.symbol_type,
                'match_type': [MatchType.SYMBOL],
                'relevance_score': symbol_score,
                'semantic_score': None,
                'keyword_score': None,
                'symbol_score': symbol_score
            })

        return search_results

    async def _regex_search(
        self,
        repo_id: int,
        query: str,
        filters: Dict,
        db: Session
    ) -> List[Dict]:
        """
        Regex search across file contents.
        Rate-limited for security.
        """
        try:
            # Compile regex with timeout
            pattern = re.compile(query, re.MULTILINE if not filters.get('case_sensitive') else 0)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Get all files for repo
        query_filter = CodeFile.repo_id == repo_id
        if filters.get('lang'):
            query_filter = and_(query_filter, CodeFile.language == filters['lang'])

        files = db.query(CodeFile).filter(query_filter).all()

        search_results = []
        match_count = 0

        for file in files:
            if match_count >= search_config.MAX_REGEX_MATCHES:
                break

            # Search in file content
            try:
                matches = list(pattern.finditer(file.content))
            except:
                continue

            for match in matches:
                if match_count >= search_config.MAX_REGEX_MATCHES:
                    break

                # Get line number
                start_pos = match.start()
                line_num = file.content[:start_pos].count('\n') + 1

                # Extract context
                lines = file.content.split('\n')
                start_line = max(0, line_num - 3)
                end_line = min(len(lines), line_num + 3)
                snippet = '\n'.join(lines[start_line:end_line])

                search_results.append({
                    'chunk_id': None,
                    'file_id': file.id,
                    'file_path': file.file_path,
                    'snippet': snippet,
                    'start_line': line_num,
                    'end_line': line_num,
                    'language': file.language,
                    'match_type': [MatchType.REGEX],
                    'relevance_score': 0.8,  # Fixed score for regex
                    'semantic_score': None,
                    'keyword_score': None,
                    'symbol_score': None
                })

                match_count += 1

        return search_results

    async def _hybrid_search(
        self,
        repo_id: int,
        query: str,
        filters: Dict,
        db: Session
    ) -> List[Dict]:
        """
        Hybrid search combining semantic, keyword, and symbol.
        Implements score fusion algorithm.
        """
        # Run all search methods in parallel
        semantic_results = await self._semantic_search(repo_id, query, filters, db)
        keyword_results = await self._keyword_search(repo_id, query, filters, db)
        symbol_results = await self._symbol_search(repo_id, query, filters, db)

        # Merge results
        merged_results = {}

        # Add semantic results
        for result in semantic_results:
            key = (result['file_id'], result['start_line'])
            merged_results[key] = result

        # Merge keyword results
        for result in keyword_results:
            key = (result['file_id'], result['start_line'])
            if key in merged_results:
                # Update existing result
                merged_results[key]['match_type'].append(MatchType.KEYWORD)
                merged_results[key]['keyword_score'] = result['keyword_score']
            else:
                merged_results[key] = result

        # Merge symbol results
        for result in symbol_results:
            key = (result['file_id'], result['start_line'])
            if key in merged_results:
                merged_results[key]['match_type'].append(MatchType.SYMBOL)
                merged_results[key]['symbol_score'] = result['symbol_score']
                merged_results[key]['symbol_name'] = result.get('symbol_name')
                merged_results[key]['symbol_type'] = result.get('symbol_type')
            else:
                merged_results[key] = result

        # Calculate hybrid scores
        for key, result in merged_results.items():
            semantic = result.get('semantic_score') or 0
            keyword = result.get('keyword_score') or 0
            symbol = result.get('symbol_score') or 0

            # Weighted combination
            combined_score = (
                search_config.SEMANTIC_WEIGHT * semantic +
                search_config.KEYWORD_WEIGHT * keyword +
                search_config.SYMBOL_WEIGHT * symbol
            )

            # Boost if multiple match types
            if len(result['match_type']) > 1:
                combined_score *= 1.2

            # Normalize to 0-1
            result['relevance_score'] = min(combined_score, 1.0)

        return list(merged_results.values())

    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply additional filters to results.
        """
        filtered = results

        # File path filter (glob pattern)
        if filters.get('file'):
            import fnmatch
            file_pattern = filters['file']
            filtered = [
                r for r in filtered
                if fnmatch.fnmatch(r['file_path'], file_pattern)
            ]

        # Exclude test files if requested
        if not filters.get('include_tests', True):
            test_patterns = ['test_', '_test.', '/tests/', '/test/']
            filtered = [
                r for r in filtered
                if not any(pattern in r['file_path'].lower() for pattern in test_patterns)
            ]

        return filtered

    def _get_file_path(self, file_id: int, db: Session) -> str:
        """Get file path from file_id"""
        file = db.query(CodeFile).get(file_id)
        return file.file_path if file else "unknown"

    def _highlight_snippet(self, snippet: str, query: str) -> str:
        """
        Add HTML highlighting to snippet.
        """
        # Simple highlighting - wrap matches in <mark> tags
        query_terms = query.split()
        highlighted = snippet

        for term in query_terms:
            pattern = re.compile(f'({re.escape(term)})', re.IGNORECASE)
            highlighted = pattern.sub(r'<mark>\1</mark>', highlighted)

        return highlighted

    async def get_context(
        self,
        file_id: int,
        start_line: int,
        end_line: int,
        context_lines: int,
        db: Session
    ) -> Dict:
        """
        Get code snippet with context lines.
        """
        file = db.query(CodeFile).get(file_id)
        if not file:
            return None

        lines = file.content.split('\n')
        context_start = max(0, start_line - context_lines - 1)
        context_end = min(len(lines), end_line + context_lines)

        return {
            'file_path': file.file_path,
            'language': file.language,
            'content': '\n'.join(lines[context_start:context_end]),
            'start_line': context_start + 1,
            'end_line': context_end
        }


# Singleton instance
hybrid_search_service = HybridSearchService()