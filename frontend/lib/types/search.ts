// frontend/lib/types/search.ts

export enum SearchMode {
  SEMANTIC = 'semantic',
  KEYWORD = 'keyword',
  HYBRID = 'hybrid',
  REGEX = 'regex',
  SYMBOL = 'symbol',
  AUTO = 'auto'
}

export enum MatchType {
  SEMANTIC = 'semantic',
  KEYWORD = 'keyword',
  SYMBOL = 'symbol',
  REGEX = 'regex',
  FILENAME = 'filename'
}

export interface SearchFilters {
  file?: string;
  lang?: string;
  branch?: string;
  symbolType?: string;
  includeTests?: boolean;
  caseSensitive?: boolean;
}

export interface SearchResultItem {
  chunkId?: number;
  fileId: number;
  filePath: string;
  snippet: string;
  highlightedSnippet: string;
  startLine: number;
  endLine: number;
  matchType: MatchType[];
  relevanceScore: number;
  semanticScore?: number;
  keywordScore?: number;
  symbolScore?: number;
  language: string;
  symbolName?: string;
  symbolType?: string;
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  totalResults: number;
  page: number;
  perPage: number;
  totalPages: number;
  results: SearchResultItem[];
  latencyMs: number;
  filtersApplied: SearchFilters;
  suggestions?: string[];
}

export interface SymbolInfo {
  id: number;
  name: string;
  qualifiedName?: string;
  symbolType: string;
  signature?: string;
  docstring?: string;
  filePath: string;
  startLine: number;
  endLine: number;
  language: string;
  scope?: string;
}

export interface IndexJobStatus {
  jobId: number;
  repoId: number;
  status: string;
  progress: number;
  filesProcessed: number;
  chunksCreated: number;
  symbolsExtracted: number;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
}