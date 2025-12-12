// lib/hooks/useChat.ts
import { useState, useCallback } from 'react';
import { repositoryApi, ChatMessage, createChatRequest } from '../api';
import { extractErrorMessage } from '../utils/errorHandler';

interface ChatOptions {
  top_k?: number;
  prompt_style?: 'senior_dev' | 'concise' | 'educational';
  include_sources?: boolean;
  include_metadata?: boolean;
}

export function useChat(repoId: number) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const sendMessage = useCallback(async (
    question: string,
    options?: ChatOptions
  ): Promise<ChatMessage | null> => {
    try {
      // Validate input
      if (!question || typeof question !== 'string') {
        throw new Error('Question must be a non-empty string');
      }

      const trimmedQuestion = question.trim();
      if (!trimmedQuestion) {
        throw new Error('Question cannot be empty');
      }

      setIsLoading(true);
      setError('');
      
      // Create a properly formatted request object
      const request = createChatRequest(trimmedQuestion, options);
      
      if (process.env.NODE_ENV === 'development') {
        console.log('Sending chat request:', request);
      }
      
      const response = await repositoryApi.chat(repoId, request);
      return response;
    } catch (err: any) {
      console.error('Chat error:', err);
      const errorMsg = extractErrorMessage(err);
      setError(errorMsg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [repoId]);

  const clearError = useCallback(() => {
    setError('');
  }, []);

  return {
    sendMessage,
    isLoading,
    error,
    clearError,
  };
}