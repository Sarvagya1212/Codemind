import { Repository } from '@/lib/api';
import { Trash2, MessageSquare, FileCode, Github, RefreshCw, Zap, RotateCcw, ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
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
  const [showReingestMenu, setShowReingestMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowReingestMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  const handleReingest = async (e: React.MouseEvent, incremental: boolean) => {
    e.preventDefault();
    e.stopPropagation();
    setShowReingestMenu(false);

    const modeText = incremental ? 'Quick update (only changed files)' : 'Full re-index (all files)';
    if (!confirm(`${modeText}?\n\nThis will re-process the repository.`)) {
      return;
    }

    try {
      setIsReingesting(true);
      await repositoryApi.reingest(repository.id, { incremental });
      if (onReingest) onReingest(repository.id);
      alert(incremental
        ? '⚡ Quick update started! Only changed files will be re-indexed.'
        : '🔄 Full re-index started! All files will be processed.');
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
        <span className={`text-xs px-2 py-1 rounded ${repository.status === 'completed' ? 'bg-green-950/50 text-green-400' :
          repository.status === 'processing' ? 'bg-yellow-950/50 text-yellow-400' :
            repository.status === 'failed' ? 'bg-red-950/50 text-red-400' :
              'bg-muted text-muted-foreground'
          }`}>
          {repository.status}
        </span>

        <div className="flex gap-1">
          {/* Re-ingest Dropdown */}
          {canReingest && (
            <div className="relative" ref={menuRef}>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setShowReingestMenu(!showReingestMenu);
                }}
                disabled={isReingesting}
                className="flex items-center gap-1 p-2 text-muted-foreground hover:text-blue-400 hover:bg-blue-950/20 rounded transition-colors disabled:opacity-50"
                title="Re-index repository"
              >
                <RefreshCw className={`w-4 h-4 ${isReingesting ? 'animate-spin' : ''}`} />
                <ChevronDown className="w-3 h-3" />
              </button>

              {showReingestMenu && (
                <div
                  className="absolute right-0 top-full mt-1 w-56 bg-background border border-border rounded-lg shadow-lg z-50 overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={(e) => handleReingest(e, true)}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors text-left"
                  >
                    <Zap className="w-4 h-4 text-yellow-400" />
                    <div>
                      <div className="text-sm font-medium">Quick Update</div>
                      <div className="text-xs text-muted-foreground">Only changed files</div>
                    </div>
                  </button>
                  <div className="border-t border-border" />
                  <button
                    onClick={(e) => handleReingest(e, false)}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors text-left"
                  >
                    <RotateCcw className="w-4 h-4 text-blue-400" />
                    <div>
                      <div className="text-sm font-medium">Full Re-index</div>
                      <div className="text-xs text-muted-foreground">Re-process all files</div>
                    </div>
                  </button>
                </div>
              )}
            </div>
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
