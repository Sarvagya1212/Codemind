// frontend/lib/hooks/useCodeSearch.ts

import { useState, useCallback, useEffect } from 'react';  // ADD THIS LINE
import { searchApi } from '../api';
import {
  SearchMode,
  SearchFilters,
  SearchResponse,
  SearchResultItem
} from '../types/search';
import { useDebounce } from './useDebounce';

interface UseCodeSearchOptions {
  mode?: SearchMode;
  filters?: SearchFilters;
  page?: number;
  perPage?: number;
  debounceMs?: number;
  autoSearch?: boolean;
}

export function useCodeSearch(
  repoId: number,
  initialQuery: string = '',
  options: UseCodeSearchOptions = {}
) {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState(0);
  const [currentPage, setCurrentPage] = useState(options.page || 1);
  const [mode, setMode] = useState(options.mode || SearchMode.AUTO);
  const [filters, setFilters] = useState<SearchFilters>(options.filters || {});

  // Debounce query for auto-search
  const debouncedQuery = useDebounce(query, options.debounceMs || 300);

  const search = useCallback(async (
    searchQuery?: string,
    searchOptions?: Partial<UseCodeSearchOptions>
  ) => {
    // FIX: Ensure query is always a string
    let q = searchQuery !== undefined ? searchQuery : query;
    
    // Convert to string if it's not
    if (typeof q !== 'string') {
      console.error('Invalid query type:', typeof q, q);
      q = String(q || '');
    }
    
    q = q.trim();
    
    if (!q) {
      setResults([]);
      setTotalResults(0);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await searchApi.search(repoId, q, {
        mode: searchOptions?.mode || mode,
        filters: searchOptions?.filters || filters,
        page: searchOptions?.page || currentPage,
        perPage: searchOptions?.perPage || options.perPage || 20
      });

      setResults(response.results);
      setTotalResults(response.totalResults);
      setLatency(response.latencyMs);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Search failed';
      setError(errorMessage);
      setResults([]);
      setTotalResults(0);
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [repoId, query, mode, filters, currentPage, options.perPage]);

  // Auto-search on debounced query change
  useEffect(() => {
    if (options.autoSearch && debouncedQuery && typeof debouncedQuery === 'string') {
      search(debouncedQuery);
    }
  }, [debouncedQuery, options.autoSearch]);

  const nextPage = useCallback(() => {
    const newPage = currentPage + 1;
    setCurrentPage(newPage);
    search(query, { page: newPage });
  }, [currentPage, query, search]);

  const prevPage = useCallback(() => {
    if (currentPage > 1) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      search(query, { page: newPage });
    }
  }, [currentPage, query, search]);

  const goToPage = useCallback((page: number) => {
    setCurrentPage(page);
    search(query, { page });
  }, [query, search]);

  const updateFilters = useCallback((newFilters: SearchFilters) => {
    setFilters(newFilters);
    setCurrentPage(1);
    search(query, { filters: newFilters, page: 1 });
  }, [query, search]);

  const updateMode = useCallback((newMode: SearchMode) => {
    setMode(newMode);
    setCurrentPage(1);
    search(query, { mode: newMode, page: 1 });
  }, [query, search]);

  return {
    query,
    setQuery,
    results,
    totalResults,
    isLoading,
    error,
    latency,
    currentPage,
    mode,
    setMode: updateMode,
    filters,
    setFilters: updateFilters,
    search,
    nextPage,
    prevPage,
    goToPage
  };
}