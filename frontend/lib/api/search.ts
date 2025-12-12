// frontend/lib/api/search.ts
import { api } from '../api';
import {
  SearchMode,
  SearchFilters,
  SearchResponse,
  SearchResultItem,
  SymbolInfo,
  IndexJobStatus
} from '../types/search';

// Helper to transform API response to camelCase with null safety and debugging
function transformSearchResult(apiResult: any): SearchResultItem {
  // DEBUG: Log the raw API result to see what we're getting
  console.log('Raw API result:', apiResult);
  console.log('file_id type:', typeof apiResult.file_id, 'value:', apiResult.file_id);
  
  // Ensure file_id is a valid number
  let fileId = apiResult.file_id;
  if (typeof fileId === 'string') {
    fileId = parseInt(fileId, 10);
  }
  
  if (isNaN(fileId) || fileId === null || fileId === undefined) {
    console.error('INVALID FILE_ID in API response:', apiResult);
    fileId = 0; // Fallback to prevent NaN
  }
  
  return {
    chunkId: apiResult.chunk_id ?? undefined,
    fileId: fileId,
    filePath: apiResult.file_path || '',
    snippet: apiResult.snippet || '',
    highlightedSnippet: apiResult.highlighted_snippet || apiResult.snippet || '',
    startLine: apiResult.start_line || 0,
    endLine: apiResult.end_line || 0,
    matchType: Array.isArray(apiResult.match_type) ? apiResult.match_type : [],
    relevanceScore: apiResult.relevance_score || 0,
    semanticScore: apiResult.semantic_score ?? undefined,
    keywordScore: apiResult.keyword_score ?? undefined,
    symbolScore: apiResult.symbol_score ?? undefined,
    language: apiResult.language || 'text',
    symbolName: apiResult.symbol_name ?? undefined,
    symbolType: apiResult.symbol_type ?? undefined
  };
}

export const searchApi = {
  /**
   * Start indexing a repository
   */
  startIndexing: async (
    repoId: number,
    options: {
      branch?: string;
      force?: boolean;
      incremental?: boolean;
    } = {}
  ): Promise<IndexJobStatus> => {
    const response = await api.post(`/repos/${repoId}/index`, {
      branch: options.branch || 'main',
      force: options.force || false,
      incremental: options.incremental !== false
    });
    return response.data;
  },

  /**
   * Get indexing job status
   */
  getIndexStatus: async (
    repoId: number,
    jobId?: number
  ): Promise<IndexJobStatus> => {
    const params = jobId ? { job_id: jobId } : {};
    const response = await api.get(`/repos/${repoId}/index/status`, { params });
    return response.data;
  },

  /**
   * Search code - WITH PROPER DATA TRANSFORMATION
   */
  search: async (
    repoId: number,
    query: string,
    options: {
      mode?: SearchMode;
      filters?: SearchFilters;
      page?: number;
      perPage?: number;
    } = {}
  ): Promise<SearchResponse> => {
    const params = {
      q: query,
      mode: options.mode || SearchMode.AUTO,
      page: options.page || 1,
      per_page: options.perPage || 20,
      ...options.filters
    };

    const response = await api.get(`/repos/${repoId}/search`, { params });
    
    // Transform API response to camelCase
    const apiData = response.data;
    
    return {
      query: apiData.query,
      mode: apiData.mode,
      totalResults: apiData.total_results,
      page: apiData.page,
      perPage: apiData.per_page,
      totalPages: apiData.total_pages,
      results: apiData.results.map(transformSearchResult), // Transform each result
      latencyMs: apiData.latency_ms,
      filtersApplied: apiData.filters_applied,
      suggestions: apiData.suggestions
    };
  },

  /**
   * Search symbols
   */
  searchSymbols: async (
    repoId: number,
    query: string,
    options: {
      lang?: string;
      symbolType?: string;
      limit?: number;
    } = {}
  ): Promise<{ symbols: SymbolInfo[]; totalResults: number; latencyMs: number }> => {
    const params = {
      q: query,
      ...options
    };
    const response = await api.get(`/repos/${repoId}/symbols`, { params });
    return response.data;
  },

  /**
   * Get file content
   */
  getFileContent: async (
    repoId: number,
    fileId: number,
    options: {
      start?: number;
      end?: number;
      context?: number;
    } = {}
  ): Promise<{
    fileId: number;
    filePath: string;
    language: string;
    content: string;
    startLine: number;
    endLine: number;
    totalLines: number;
  }> => {
    const response = await api.get(
      `/repos/${repoId}/file/${fileId}/content`,
      { params: options }
    );
    return response.data;
  },

  /**
   * Get search preview
   */
  getPreview: async (
    repoId: number,
    chunkIds: string[],
    contextLines: number = 5
  ): Promise<{ previews: any[] }> => {
    const response = await api.post(`/repos/${repoId}/search/preview`, {
      chunk_ids: chunkIds,
      context_lines: contextLines
    });
    return response.data;
  },

  /**
   * Get index stats
   */
  getIndexStats: async (repoId: number) => {
    const response = await api.get(`/repos/${repoId}/index/stats`);
    return response.data;
  },

  /**
   * Clear index
   */
  clearIndex: async (repoId: number) => {
    const response = await api.delete(`/repos/${repoId}/index`);
    return response.data;
  }
};

// DEBUG HELPER - Add this to your search page to see what's happening:
/*
const handleResultClick = (result: SearchResultItem) => {
  console.log('=== DEBUG CLICK ===');
  console.log('Result object:', result);
  console.log('fileId:', result.fileId);
  console.log('startLine:', result.startLine);
  console.log('repoId:', repoId);
  
  const url = `/repo/${repoId}/file/${result.fileId}?line=${result.startLine}`;
  console.log('Navigating to URL:', url);
  
  router.push(url);
};
*/