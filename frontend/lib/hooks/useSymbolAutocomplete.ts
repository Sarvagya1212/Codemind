// frontend/lib/hooks/useSymbolAutocomplete.ts
import { useState, useEffect, useCallback } from 'react';
import { searchApi } from '../api';
import { SymbolInfo } from '../types/search';
import { useDebounce } from './useDebounce';

export function useSymbolAutocomplete(
  repoId: number,
  query: string,
  options: {
    lang?: string;
    symbolType?: string;
    limit?: number;
    debounceMs?: number;
    enabled?: boolean;
  } = {}
) {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedQuery = useDebounce(query, options.debounceMs || 200);

  const fetchSymbols = useCallback(async () => {
    // FIX: Safe string handling
    const queryStr = String(debouncedQuery || '');
    
    if (!queryStr || queryStr.length < 2) {
      setSymbols([]);
      return;
    }

    if (options.enabled === false) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await searchApi.searchSymbols(repoId, queryStr, {
        lang: options.lang,
        symbolType: options.symbolType,
        limit: options.limit || 20
      });

      setSymbols(response.symbols);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch symbols';
      setError(errorMessage);
      setSymbols([]);
    } finally {
      setIsLoading(false);
    }
  }, [repoId, debouncedQuery, options.lang, options.symbolType, options.limit, options.enabled]);

  useEffect(() => {
    fetchSymbols();
  }, [fetchSymbols]);

  return {
    symbols,
    isLoading,
    error
  };
}