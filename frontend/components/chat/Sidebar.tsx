import { Repository, ChatMessage } from '@/lib/api';
import { Clock, Github, Package, Calendar, MessageSquare, Trash2, AlertCircle } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface SidebarProps {
  repository: Repository;
  chatHistory: ChatMessage[];
  onSelectMessage: (message: ChatMessage) => void;
}

export default function Sidebar({ repository, chatHistory, onSelectMessage }: SidebarProps) {
  const router = useRouter();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      setDeleteError('');
      
      const response = await fetch(`http://localhost:8000/repos/${repository.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete repository');
      }

      // Redirect to home after successful deletion
      router.push('/');
      
    } catch (error: any) {
      setDeleteError(error.message);
      setIsDeleting(false);
    }
  };

  const fileCount = repository.repo_metadata?.total_files || 0;
  const totalChunks = repository.repo_metadata?.embedding_stats?.total_chunks || 0;

  return (
    <aside className="w-80 border-r border-border bg-card flex flex-col">
      {/* Repository Info */}
      <div className="p-6 border-b border-border">
        <div className="flex items-start gap-3 mb-4">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Package className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="font-semibold text-lg truncate mb-1">
              {repository.github_url.split('/').pop()?.replace('.git', '')}
            </h2>
            <a
              href={repository.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1 truncate"
            >
              <Github className="w-3 h-3" />
              <span className="truncate">{repository.github_url}</span>
            </a>
          </div>
        </div>

        {/* Stats */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Files</span>
            <span className="font-medium">{fileCount}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Code Chunks</span>
            <span className="font-medium">{totalChunks}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Status</span>
            <span className={`text-xs px-2 py-1 rounded ${
              repository.status === 'completed' ? 'bg-green-950/50 text-green-400' :
              repository.status === 'processing' ? 'bg-yellow-950/50 text-yellow-400' :
              repository.status === 'failed' ? 'bg-red-950/50 text-red-400' :
              'bg-muted text-muted-foreground'
            }`}>
              {repository.status}
            </span>
          </div>
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          Chat History
        </h3>
        
        {chatHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">No messages yet</p>
        ) : (
          <div className="space-y-2">
            {chatHistory.map((message) => (
              <button
                key={message.id}
                onClick={() => onSelectMessage(message)}
                className="w-full text-left p-3 rounded-lg hover:bg-muted/50 transition-colors border border-transparent hover:border-border"
              >
                <p className="text-sm font-medium line-clamp-2 mb-1">
                  {message.question}
                </p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3" />
                  {new Date(message.created_at).toLocaleString()}
                </div>
                
                {message.message_metadata && (
                  <div className="flex gap-2 mt-2">
                    {message.message_metadata.chunks_found !== undefined && (
                      <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">
                        {message.message_metadata.chunks_found} chunks
                      </span>
                    )}
                    {message.message_metadata.prompt_style && (
                      <span className="text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded">
                        {message.message_metadata.prompt_style === 'senior_dev' ? '👨‍💻' :
                         message.message_metadata.prompt_style === 'concise' ? '⚡' : '📚'}
                      </span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Delete Repository Section */}
      <div className="p-4 border-t border-border">
        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-950/20 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete Repository
          </button>
        ) : (
          <div className="bg-red-950/20 border border-red-900/50 rounded-lg p-3">
            <div className="flex items-start gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-red-400 mb-1">Delete Repository?</p>
                <p className="text-muted-foreground text-xs">
                  This will permanently delete all files, embeddings, and chat history.
                </p>
              </div>
            </div>
            
            {deleteError && (
              <p className="text-xs text-red-400 mb-2">{deleteError}</p>
            )}
            
            <div className="flex gap-2">
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex-1 px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded transition-colors"
              >
                {isDeleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteError('');
                }}
                disabled={isDeleting}
                className="flex-1 px-3 py-1.5 text-sm bg-background hover:bg-muted text-foreground rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
