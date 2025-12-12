// frontend/lib/hooks/useIndexStatus.ts

import { useState, useEffect, useCallback } from 'react';
import { searchApi } from '../api/search';
import { IndexJobStatus } from '../types/search';

export function useIndexStatus(
  repoId: number,
  jobId?: number,
  options: {
    pollInterval?: number;
    enabled?: boolean;
  } = {}
) {
  const [status, setStatus] = useState<IndexJobStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (options.enabled === false) {
      return;
    }

    try {
      const statusData = await searchApi.getIndexStatus(repoId, jobId);
      setStatus(statusData);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch status');
      setStatus(null);
    } finally {
      setIsLoading(false);
    }
  }, [repoId, jobId, options.enabled]);

  // Initial fetch
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Polling
  useEffect(() => {
    if (options.enabled === false) {
      return;
    }

    // Only poll if job is running
    if (status && (status.status === 'pending' || status.status === 'running')) {
      const interval = setInterval(() => {
        fetchStatus();
      }, options.pollInterval || 3000);

      return () => clearInterval(interval);
    }
  }, [status, options.pollInterval, options.enabled, fetchStatus]);

  const startIndexing = useCallback(async (indexOptions: {
  branch?: string;
  force?: boolean;
  incremental?: boolean;
} = {}) => {
  try {
    setIsLoading(true);
    
    // FIX: Always force on first index
    const options = {
      branch: indexOptions.branch || 'main',
      force: indexOptions.force !== false,  // Default to true
      incremental: false  // Don't use incremental on first run
    };
    
    const newJob = await searchApi.startIndexing(repoId, options);
    setStatus(newJob);
    setError(null);
  } catch (err: any) {
    setError(err.response?.data?.detail || 'Failed to start indexing');
  } finally {
    setIsLoading(false);
  }
}, [repoId]);


  

  return {
    status,
    isLoading,
    error,
    refetch: fetchStatus,
    startIndexing
  };
}