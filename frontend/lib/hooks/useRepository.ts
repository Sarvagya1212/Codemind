// lib/hooks/useRepository.ts
import { useState, useEffect, useCallback } from 'react';
import { repositoryApi, Repository } from '../api';
import { extractErrorMessage } from '../utils/errorHandler';

export function useRepository(repoId: number) {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isPolling, setIsPolling] = useState(false);

  const fetchRepository = useCallback(async () => {
    try {
      const repo = await repositoryApi.getById(repoId);
      setRepository(repo);
      setError('');
      
      // Continue polling if still processing
      if (repo.status === 'processing' || repo.status === 'pending') {
        setIsPolling(true);
      } else {
        setIsPolling(false);
      }
      
      return repo;
    } catch (err: any) {
      const errorMsg = extractErrorMessage(err);
      setError(errorMsg);
      setIsPolling(false);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [repoId]);

  // Initial fetch
  useEffect(() => {
    fetchRepository();
  }, [fetchRepository]);

  // Polling effect
  useEffect(() => {
    if (!isPolling) return;

    const interval = setInterval(() => {
      fetchRepository();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [isPolling, fetchRepository]);

  return {
    repository,
    isLoading,
    error,
    isPolling,
    refetch: fetchRepository,
  };
}