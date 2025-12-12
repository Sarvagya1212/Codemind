'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChatMessage } from '@/lib/api';
import { useRepository } from '@/lib/hooks/useRepository';
import { useChatHistory } from '@/lib/hooks/useChatHistory';
import { useChat } from '@/lib/hooks/useChat';
import { safeRenderError } from '@/lib/utils/errorHandler';
import Sidebar from '@/components/chat/Sidebar';
import ChatArea from '@/components/chat/ChatArea';
import { Loader2, AlertCircle, ArrowLeft, Clock, Search } from 'lucide-react';
import Link from 'next/link';

export default function RepoChat() {
  const params = useParams();
  const router = useRouter();
  const repoId = parseInt(params.id as string);

  // Custom hooks for data management
  const { repository, isLoading: isLoadingRepo, error: repoError, isPolling } = useRepository(repoId);
  const isRepoReady = repository?.status === 'completed';
  const { messages: chatHistory, addMessage } = useChatHistory(repoId, isRepoReady);
  const { sendMessage, isLoading: isSending, error: chatError, clearError } = useChat(repoId);

  const [displayMessages, setDisplayMessages] = useState<ChatMessage[]>([]);

  // Sync chat history to display messages when ready
  useEffect(() => {
    if (isRepoReady && chatHistory.length > 0) {
      setDisplayMessages([...chatHistory].reverse()); // Reverse to show oldest first
    }
  }, [chatHistory, isRepoReady]);

  // Clear chat error after 5 seconds
  useEffect(() => {
    if (chatError) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [chatError, clearError]);

  const handleSendMessage = async (
    question: string,
    options?: {
      topK?: number;
      promptStyle?: 'senior_dev' | 'concise' | 'educational';
      includeSources?: boolean;
      includeMetadata?: boolean;
    }
  ) => {
    if (!question || !question.trim()) {
      return;
    }

    const trimmedQuestion = question.trim();
    const newMessage = await sendMessage(trimmedQuestion, options);
    
    if (newMessage) {
      addMessage(newMessage);
      setDisplayMessages((prev) => [...prev, newMessage]);
    }
  };

  const handleSelectMessage = (message: ChatMessage) => {
    setDisplayMessages((prev) => {
      const exists = prev.find(m => m.id === message.id);
      if (exists) {
        return prev;
      }
      return [...prev, message];
    });
  };

  // Loading state
  if (isLoadingRepo) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)]">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading repository...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (repoError || !repository) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] px-4">
        <div className="max-w-md w-full bg-card border border-border rounded-lg p-8 text-center">
          <div className="inline-flex items-center justify-center p-3 bg-destructive/10 rounded-full mb-4">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Error Loading Repository</h2>
          <p className="text-muted-foreground mb-6">
            {/* FIXED: Only pass error, provide fallback in JSX */}
            {repoError ? safeRenderError(repoError) : 'Repository not found'}
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  // Processing state
  if (repository.status === 'processing' || repository.status === 'pending' || isPolling) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] px-4">
        <div className="max-w-md w-full bg-card border border-border rounded-lg p-8 text-center">
          <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-full mb-4 relative">
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Processing Repository</h2>
          <p className="text-muted-foreground mb-6">
            {repository.status === 'pending' 
              ? 'Waiting to start processing...'
              : 'Parsing code and creating embeddings...'}
          </p>
          
          <div className="space-y-3 text-left mb-6">
            <div className="flex items-center gap-3 text-sm">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
              <span className="text-muted-foreground">Cloning repository</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse animation-delay-200" />
              <span className="text-muted-foreground">Parsing code files</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <div className="w-2 h-2 bg-primary rounded-full animate-pulse animation-delay-400" />
              <span className="text-muted-foreground">Creating embeddings</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>This may take a few minutes</span>
          </div>

          <div className="mt-6">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Failed state
  if (repository.status === 'failed') {
    // FIXED: Access repo_metadata correctly
    const failureError = repository.repo_metadata?.error;
    
    return (
      <div className="flex items-center justify-center h-[calc(100vh-140px)] px-4">
        <div className="max-w-md w-full bg-card border border-border rounded-lg p-8 text-center">
          <div className="inline-flex items-center justify-center p-3 bg-destructive/10 rounded-full mb-4">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Processing Failed</h2>
          <p className="text-muted-foreground mb-2">
            Failed to process this repository
          </p>
          {failureError && (
            <p className="text-sm text-destructive mb-6 font-mono bg-destructive/10 p-3 rounded">
              {safeRenderError(failureError)}
            </p>
          )}
          <div className="flex gap-3 justify-center">
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg transition"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition"
            >
              Try Another Repository
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Main chat interface (repository is ready)
  return (
    <div className="flex h-[calc(100vh-140px)]">
      <Sidebar
        repository={repository}
        chatHistory={chatHistory}
        onSelectMessage={handleSelectMessage}
      />
      
      <div className="flex-1 flex flex-col">
        <div className="border-b border-border p-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Chat with Repository</h2>
          
          <Link
            href={`/search/${repoId}`}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition"
          >
            <Search className="h-4 w-4" />
            Code Search
          </Link>
        </div>
        
        <ChatArea
          messages={displayMessages}
          onSendMessage={handleSendMessage}
          isLoading={isSending}
        />
        
        {/* Chat error notification */}
        {chatError && (
          <div className="fixed bottom-4 right-4 max-w-md bg-destructive/10 border border-destructive/20 rounded-lg p-4 shadow-lg animate-in slide-in-from-bottom-5">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-destructive">Error</p>
                <p className="text-sm text-muted-foreground">
                  {safeRenderError(chatError)}
                </p>
              </div>
              <button
                onClick={clearError}
                className="text-muted-foreground hover:text-foreground"
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
