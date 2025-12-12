'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import FileTree from '@/components/FileTree';
import CodeViewer from '@/components/CodeViewer';
import { useFileTree, useFileContent } from '@/lib/hooks/useFileViewer';

export default function FileViewerPage() {
  const params = useParams();
  const repoId = Number(params.id);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const { tree, loading: treeLoading, error: treeError } = useFileTree(repoId);
  const { content, loading: contentLoading, error: contentError } = useFileContent(
    repoId,
    selectedPath
  );

  const handleFileSelect = (path: string) => {
    setSelectedPath(path);
  };

  if (treeLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-white">Loading repository...</div>
      </div>
    );
  }

  if (treeError) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-red-400">Error: {treeError}</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Left Sidebar - File Tree */}
      <div className="w-80 border-r border-gray-800 flex-shrink-0">
        {tree && (
          <FileTree
            tree={tree}
            onFileSelect={handleFileSelect}
            selectedPath={selectedPath}
          />
        )}
      </div>

      {/* Right Panel - Code Viewer */}
      <div className="flex-1">
        <CodeViewer
          fileContent={content}
          loading={contentLoading}
          error={contentError}
        />
      </div>
    </div>
  );
}
