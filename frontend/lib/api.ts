// lib/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('API Request:', {
        method: config.method,
        url: config.url,
        data: config.data,
      });
    }
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('API Response:', {
        status: response.status,
        url: response.config.url,
      });
    }
    return response;
  },
  (error) => {
    console.error('API Response Error:', {
      status: error.response?.status,
      url: error.config?.url,
      data: error.response?.data,
    });
    return Promise.reject(error);
  }
);

// Types
export interface Repository {
  id: number;
  github_url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  repo_metadata?: {
    error?: string;
    total_files?: number;
    embedding_stats?: any;
    [key: string]: any;
  };
  local_path?: string;
  created_at: string;
  updated_at?: string;
}

export interface RepositoryIngestResponse {
  id: number;
  github_url: string;
  status: string;
  message: string;
}

export interface SourceReference {
  file_path: string;
  language: string;
  relevance_score: number;
  lines?: string;
}

export interface ChatMessage {
  id: number;
  question: string;
  answer: string;
  sources: SourceReference[];
  message_metadata?: {
    chunks_found?: number;
    avg_similarity?: number;
    model?: string;
    prompt_style?: string;
    streaming?: boolean;
  };
  created_at: string;
}

export interface ChatRequest {
  question: string;
  top_k?: number;
  prompt_style?: 'senior_dev' | 'concise' | 'educational';
  include_sources?: boolean;
  include_metadata?: boolean;
}

export interface CodeSearchRequest {
  query: string;
  top_k?: number;
  score_threshold?: number;
  rerank?: boolean;
}

export interface CodeChunk {
  id: string;
  content: string;
  metadata: Record<string, any>;
  similarity: number;
  original_similarity?: number;
}

export interface HealthCheckResponse {
  status: string;
  ollama_url: string;
  model: string;
  embed_model: string;
  embedding_dim?: number;
  error?: string;
}

export interface FileTreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  extension?: string;
  size: number;
  children?: FileTreeNode[];
}

export interface FileContent {
  file_path: string;
  content: string;
  language: string;
  size_bytes: number;
  lines: number;
}

export interface StreamEvent {
  type: 'token' | 'sources' | 'done' | 'error';
  content?: string | SourceReference[];
  message_id?: number;
}

// File System API
export async function getFileTree(repoId: number): Promise<FileTreeNode> {
  const response = await fetch(`${API_BASE_URL}/repos/${repoId}/files/tree`);
  if (!response.ok) {
    throw new Error('Failed to fetch file tree');
  }
  return response.json();
}

export async function getFileContent(
  repoId: number,
  filePath: string
): Promise<FileContent> {
  const response = await fetch(
    `${API_BASE_URL}/repos/${repoId}/files/content?path=${encodeURIComponent(filePath)}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch file content');
  }
  return response.json();
}

export async function rescanRepository(repoId: number): Promise<{ message: string; files_count: number }> {
  const response = await fetch(`${API_BASE_URL}/repos/${repoId}/files/rescan`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to rescan repository');
  }
  return response.json();
}

// Repository API
export const repositoryApi = {
  // Ingest a new repository
  ingest: async (githubUrl: string): Promise<Repository> => {
    if (!githubUrl || typeof githubUrl !== 'string') {
      throw new Error('GitHub URL is required');
    }
    const response = await api.post('/repos/ingest', { github_url: githubUrl });
    return response.data;
  },

  reingest: async (id: number): Promise<RepositoryIngestResponse> => {
    const response = await api.post(`/repos/${id}/reingest`);
    return response.data;
  },

  // Get repository status
  getById: async (id: number): Promise<Repository> => {
    const response = await api.get(`/repos/${id}`);
    return response.data;
  },

  // List all repositories
  list: async (): Promise<Repository[]> => {
    const response = await api.get('/repos/');
    return response.data;
  },

  // Delete repository
  delete: async (id: number): Promise<void> => {
    await api.delete(`/repos/${id}`);
  },

  // Chat with repository (standard)
  chat: async (id: number, request: ChatRequest): Promise<ChatMessage> => {
    // Validate request
    if (!request || typeof request !== 'object') {
      throw new Error('Invalid request object');
    }
    
    if (!request.question || typeof request.question !== 'string' || !request.question.trim()) {
      throw new Error('Question is required and must be a non-empty string');
    }

    // Ensure all required fields are present
    const validatedRequest: ChatRequest = {
      question: request.question.trim(),
      top_k: request.top_k ?? 5,
      prompt_style: request.prompt_style ?? 'senior_dev',
      include_sources: request.include_sources ?? true,
      include_metadata: request.include_metadata ?? true,
    };

    const response = await api.post(`/repos/${id}/chat`, validatedRequest);
    return response.data;
  },

  // Chat with repository (streaming)
  chatStream: async (
    id: number,
    request: ChatRequest,
    onToken: (token: string) => void,
    onSources: (sources: SourceReference[]) => void,
    onDone: (messageId: number) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    // Validate request
    if (!request.question || !request.question.trim()) {
      throw new Error('Question is required');
    }

    const validatedRequest: ChatRequest = {
      question: request.question.trim(),
      top_k: request.top_k ?? 5,
      prompt_style: request.prompt_style ?? 'senior_dev',
      include_sources: request.include_sources ?? true,
      include_metadata: request.include_metadata ?? true,
    };

    const response = await fetch(`${API_BASE_URL}/repos/${id}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(validatedRequest),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to start streaming chat');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('Stream not available');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const event: StreamEvent = JSON.parse(data);

              switch (event.type) {
                case 'token':
                  onToken(event.content as string);
                  break;
                case 'sources':
                  onSources(event.content as SourceReference[]);
                  break;
                case 'done':
                  onDone(event.message_id!);
                  break;
                case 'error':
                  onError(event.content as string);
                  break;
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  // Get chat history
  getHistory: async (id: number, limit: number = 50): Promise<ChatMessage[]> => {
    const response = await api.get(`/repos/${id}/history`, { params: { limit } });
    return response.data;
  },

  // Advanced code search
  searchCode: async (id: number, request: CodeSearchRequest): Promise<CodeChunk[]> => {
    if (!request.query || !request.query.trim()) {
      throw new Error('Search query is required');
    }

    const validatedRequest: CodeSearchRequest = {
      query: request.query.trim(),
      top_k: request.top_k ?? 5,
      score_threshold: request.score_threshold ?? 0.3,
      rerank: request.rerank ?? true,
    };

    const response = await api.post(`/repos/${id}/search`, validatedRequest);
    return response.data;
  },

  // Check RAG service health
  checkHealth: async (): Promise<HealthCheckResponse> => {
    const response = await api.get('/repos/health/rag');
    return response.data;
  },
};

// Search API (for advanced search features)
export const searchApi = {
  startIndexing: async (repoId: number, options: any = {}) => {
    const response = await api.post(`/repos/${repoId}/index`, {
      branch: options.branch || 'main',
      force: options.force || false,
      incremental: options.incremental !== false
    });
    return response.data;
  },

  getIndexStatus: async (repoId: number, jobId?: number) => {
    const params = jobId ? { job_id: jobId } : {};
    const response = await api.get(`/repos/${repoId}/index/status`, { params });
    return response.data;
  },

  getIndexStats: async (repoId: number) => {
    const response = await api.get(`/repos/${repoId}/index/stats`);
    return response.data;
  },

  clearIndex: async (repoId: number) => {
    const response = await api.delete(`/repos/${repoId}/index`);
    return response.data;
  },

  search: async (repoId: number, query: string, options: any = {}) => {
    const params = {
      q: query,
      mode: options.mode || 'auto',
      page: options.page || 1,
      per_page: options.perPage || 20,
      ...options.filters
    };
    const response = await api.get(`/repos/${repoId}/search`, { params });
    return response.data;
  },

  searchSymbols: async (repoId: number, query: string, options: any = {}) => {
    const params = { q: query, ...options };
    const response = await api.get(`/repos/${repoId}/symbols`, { params });
    return response.data;
  },

  getFileContent: async (repoId: number, fileId: number, options: any = {}) => {
    const response = await api.get(`/repos/${repoId}/file/${fileId}/content`, { params: options });
    return response.data;
  },

  getPreview: async (repoId: number, chunkIds: string[], contextLines: number = 5) => {
    const response = await api.post(`/repos/${repoId}/search/preview`, {
      chunk_ids: chunkIds,
      context_lines: contextLines
    });
    return response.data;
  }
};

// Utility function to poll repository status
export const pollRepositoryStatus = async (
  id: number,
  onUpdate: (status: Repository['status']) => void,
  maxAttempts: number = 120,
  interval: number = 3000
): Promise<Repository> => {
  let attempt = 0;

  while (attempt < maxAttempts) {
    const repo = await repositoryApi.getById(id);
    onUpdate(repo.status);

    if (repo.status === 'completed' || repo.status === 'failed') {
      return repo;
    }

    await new Promise(resolve => setTimeout(resolve, interval));
    attempt++;
  }

  throw new Error('Timeout waiting for repository to be processed');
};

// Helper function to create chat request with defaults
export const createChatRequest = (
  question: string,
  options?: Partial<ChatRequest>
): ChatRequest => {
  if (!question || typeof question !== 'string') {
    throw new Error('Question must be a non-empty string');
  }

  const trimmedQuestion = question.trim();
  if (!trimmedQuestion) {
    throw new Error('Question cannot be empty');
  }

  return {
    question: trimmedQuestion,
    top_k: options?.top_k ?? 5,
    prompt_style: options?.prompt_style ?? 'senior_dev',
    include_sources: options?.include_sources ?? true,
    include_metadata: options?.include_metadata ?? true,
  };
};

// Helper function to create search request with defaults
export const createSearchRequest = (
  query: string,
  options?: Partial<CodeSearchRequest>
): CodeSearchRequest => {
  if (!query || typeof query !== 'string') {
    throw new Error('Query must be a non-empty string');
  }

  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    throw new Error('Query cannot be empty');
  }

  return {
    query: trimmedQuery,
    top_k: options?.top_k ?? 5,
    score_threshold: options?.score_threshold ?? 0.3,
    rerank: options?.rerank ?? true,
  };
};