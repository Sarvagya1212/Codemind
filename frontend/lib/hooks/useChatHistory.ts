// lib/hooks/useChatHistory.ts
import { useState, useEffect, useCallback } from 'react';
import { repositoryApi, ChatMessage } from '../api';
import { extractErrorMessage } from '../utils/errorHandler';

export function useChatHistory(repoId: number, enabled: boolean = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const fetchHistory = useCallback(async () => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }
    
    try {
      setIsLoading(true);
      const history = await repositoryApi.getHistory(repoId);
      setMessages(history);
      setError('');
    } catch (err: any) {
      const errorMsg = extractErrorMessage(err);
      setError(errorMsg);
      console.error('Failed to load chat history:', errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [repoId, enabled]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [message, ...prev]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const clearError = useCallback(() => {
    setError('');
  }, []);

  return {
    messages,
    isLoading,
    error,
    refetch: fetchHistory,
    addMessage,
    clearMessages,
    clearError,
  };
}