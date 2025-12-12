import { Repository } from '@/lib/api';
import { Trash2, MessageSquare, FileCode, Github, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import Link from 'next/link';
import { repositoryApi } from '@/lib/api';

interface RepositoryCardProps {
  repository: Repository;
  onDelete?: (id: number) => void;
  onReingest?: (id: number) => void;
}

export default function RepositoryCard({ repository, onDelete, onReingest }: RepositoryCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isReingesting, setIsReingesting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      setIsDeleting(true);
      await repositoryApi.delete(repository.id);
      if (onDelete) onDelete(repository.id);
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete repository');
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleReingest = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm('Re-ingest this repository? This will re-clone and re-index all files.')) {
      return;
    }
    
    try {
      setIsReingesting(true);
      await repositoryApi.reingest(repository.id);
      if (onReingest) onReingest(repository.id);
      alert('Re-ingestion started! The repository will be processed in the background.');
    } catch (error) {
      console.error('Reingest error:', error);
      alert('Failed to start re-ingestion');
    } finally {
      setIsReingesting(false);
    }
  };

  const fileCount = repository.repo_metadata?.total_files || 0;
  const repoName = repository.github_url.split('/').pop()?.replace('.git', '') || 'Repository';
  const canReingest = repository.status === 'completed' || repository.status === 'failed';

  return (
    <Link 
      href={`/chat/${repository.id}`}
      className="block border border-border rounded-lg p-4 hover:border-primary/50 transition-colors relative"
    >
      <div className="mb-3">
        <h3 className="font-semibold text-lg mb-1">{repoName}</h3>
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Github className="w-4 h-4" />
          <span className="truncate">{repository.github_url}</span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
        <div className="flex items-center gap-1">
          <FileCode className="w-4 h-4" />
          {fileCount} files
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className={`text-xs px-2 py-1 rounded ${
          repository.status === 'completed' ? 'bg-green-950/50 text-green-400' :
          repository.status === 'processing' ? 'bg-yellow-950/50 text-yellow-400' :
          repository.status === 'failed' ? 'bg-red-950/50 text-red-400' :
          'bg-muted text-muted-foreground'
        }`}>
          {repository.status}
        </span>

        <div className="flex gap-1">
          {/* Re-ingest Button */}
          {canReingest && (
            <button
              onClick={handleReingest}
              disabled={isReingesting}
              className="p-2 text-muted-foreground hover:text-blue-400 hover:bg-blue-950/20 rounded transition-colors disabled:opacity-50"
              title="Re-ingest repository"
            >
              <RefreshCw className={`w-4 h-4 ${isReingesting ? 'animate-spin' : ''}`} />
            </button>
          )}

          {/* Delete Button */}
          {!showDeleteConfirm ? (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setShowDeleteConfirm(true);
              }}
              className="p-2 text-muted-foreground hover:text-red-400 hover:bg-red-950/20 rounded transition-colors"
              title="Delete repository"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          ) : (
            <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
              >
                {isDeleting ? 'Deleting...' : 'Confirm'}
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowDeleteConfirm(false);
                }}
                className="px-3 py-1 text-xs bg-muted hover:bg-muted/80 rounded"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
