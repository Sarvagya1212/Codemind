# backend/app/services/symbol_extractor.py

import re
from typing import List, Dict


class SymbolExtractor:
    """
    Simple regex-based symbol extractor.
    Tree-sitter disabled for simplicity and reliability.
    """
    
    def __init__(self):
        print("⚙️  Symbol Extractor initialized (regex-based)")
    
    def extract_symbols(
        self,
        content: str,
        language: str,
        file_path: str
    ) -> List[Dict]:
        """Extract symbols using regex patterns"""
        
        if language == 'python':
            return self._extract_python_symbols(content, file_path)
        elif language in ['javascript', 'typescript']:
            return self._extract_js_symbols(content, file_path)
        elif language == 'java':
            return self._extract_java_symbols(content, file_path)
        elif language == 'go':
            return self._extract_go_symbols(content, file_path)
        else:
            return []
    
    def _extract_python_symbols(self, content: str, file_path: str) -> List[Dict]:
        """Extract Python functions and classes"""
        symbols = []
        lines = content.split('\n')
        
        func_pattern = r'^\s*def\s+(\w+)\s*\('
        class_pattern = r'^\s*class\s+(\w+)'
        
        for i, line in enumerate(lines):
            # Functions
            func_match = re.match(func_pattern, line)
            if func_match:
                symbols.append({
                    'name': func_match.group(1),
                    'symbol_type': 'function',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'python',
                    'file_path': file_path
                })
            
            # Classes
            class_match = re.match(class_pattern, line)
            if class_match:
                symbols.append({
                    'name': class_match.group(1),
                    'symbol_type': 'class',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'python',
                    'file_path': file_path
                })
        
        return symbols
    
    def _extract_js_symbols(self, content: str, file_path: str) -> List[Dict]:
        """Extract JavaScript/TypeScript functions and classes"""
        symbols = []
        lines = content.split('\n')
        
        func_pattern = r'function\s+(\w+)\s*\('
        class_pattern = r'class\s+(\w+)'
        const_func_pattern = r'const\s+(\w+)\s*=\s*(?:async\s*)?\(?'
        arrow_func_pattern = r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
        
        for i, line in enumerate(lines):
            # Regular functions
            func_match = re.search(func_pattern, line)
            if func_match:
                symbols.append({
                    'name': func_match.group(1),
                    'symbol_type': 'function',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'javascript',
                    'file_path': file_path
                })
            
            # Classes
            class_match = re.search(class_pattern, line)
            if class_match:
                symbols.append({
                    'name': class_match.group(1),
                    'symbol_type': 'class',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'javascript',
                    'file_path': file_path
                })
            
            # Arrow functions
            arrow_match = re.search(arrow_func_pattern, line)
            if arrow_match:
                symbols.append({
                    'name': arrow_match.group(1),
                    'symbol_type': 'function',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'javascript',
                    'file_path': file_path
                })
        
        return symbols
    
    def _extract_java_symbols(self, content: str, file_path: str) -> List[Dict]:
        """Extract Java classes and methods"""
        symbols = []
        lines = content.split('\n')
        
        class_pattern = r'class\s+(\w+)'
        method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\('
        
        for i, line in enumerate(lines):
            # Classes
            class_match = re.search(class_pattern, line)
            if class_match:
                symbols.append({
                    'name': class_match.group(1),
                    'symbol_type': 'class',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'java',
                    'file_path': file_path
                })
            
            # Methods
            method_match = re.search(method_pattern, line)
            if method_match and 'class' not in line:
                symbols.append({
                    'name': method_match.group(1),
                    'symbol_type': 'method',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'java',
                    'file_path': file_path
                })
        
        return symbols
    
    def _extract_go_symbols(self, content: str, file_path: str) -> List[Dict]:
        """Extract Go functions and types"""
        symbols = []
        lines = content.split('\n')
        
        func_pattern = r'func\s+(\w+)\s*\('
        type_pattern = r'type\s+(\w+)\s+(?:struct|interface)'
        
        for i, line in enumerate(lines):
            # Functions
            func_match = re.search(func_pattern, line)
            if func_match:
                symbols.append({
                    'name': func_match.group(1),
                    'symbol_type': 'function',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'go',
                    'file_path': file_path
                })
            
            # Types
            type_match = re.search(type_pattern, line)
            if type_match:
                symbols.append({
                    'name': type_match.group(1),
                    'symbol_type': 'type',
                    'signature': line.strip(),
                    'start_line': i + 1,
                    'end_line': i + 1,
                    'language': 'go',
                    'file_path': file_path
                })
        
        return symbols


# Singleton instance
symbol_extractor = SymbolExtractor()