// frontend/lib/hooks/useFileViewer.ts

import { useState, useEffect } from 'react';
import { getFileTree, getFileContent, FileTreeNode, FileContent } from '../api';

export function useFileTree(repoId: number | null) {
  const [tree, setTree] = useState<FileTreeNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId) return;

    const fetchTree = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getFileTree(repoId);
        setTree(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load file tree');
      } finally {
        setLoading(false);
      }
    };

    fetchTree();
  }, [repoId]);

  return { tree, loading, error };
}

export function useFileContent(repoId: number | null, filePath: string | null) {
  const [content, setContent] = useState<FileContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId || !filePath) {
      setContent(null);
      return;
    }

    const fetchContent = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getFileContent(repoId, filePath);
        setContent(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load file content');
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [repoId, filePath]);

  return { content, loading, error };
}
