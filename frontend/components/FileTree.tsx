'use client';

import React, { useState } from 'react';
import { ChevronRight, ChevronDown, File as FileIcon, Folder, FolderOpen } from 'lucide-react';
import { FileTreeNode } from '@/lib/api';

interface FileTreeProps {
  tree: FileTreeNode;
  onFileSelect: (path: string) => void;
  selectedPath: string | null;
}

export default function FileTree({ tree, onFileSelect, selectedPath }: FileTreeProps) {
  return (
    <div className="w-full h-full overflow-y-auto bg-gray-900 text-gray-100 p-4">
      <TreeNode 
        node={tree} 
        onFileSelect={onFileSelect} 
        selectedPath={selectedPath}
        depth={0}
      />
    </div>
  );
}

interface TreeNodeProps {
  node: FileTreeNode;
  onFileSelect: (path: string) => void;
  selectedPath: string | null;
  depth: number;
}

function TreeNode({ node, onFileSelect, selectedPath, depth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth === 0); // Root expanded by default

  const isDirectory = node.type === 'directory';
  const isSelected = node.path === selectedPath;

  const handleClick = () => {
    if (isDirectory) {
      setIsExpanded(!isExpanded);
    } else {
      onFileSelect(node.path);
    }
  };

  const getFileIcon = () => {
    if (isDirectory) {
      return isExpanded ? <FolderOpen size={16} /> : <Folder size={16} />;
    }
    return <FileIcon size={16} />;
  };

  const getFileColor = () => {
    if (isDirectory) return 'text-blue-400';
    
    const ext = node.extension?.toLowerCase();
    if (['py'].includes(ext || '')) return 'text-yellow-400';
    if (['js', 'ts', 'jsx', 'tsx'].includes(ext || '')) return 'text-yellow-300';
    if (['json', 'yaml', 'yml'].includes(ext || '')) return 'text-green-400';
    if (['md', 'txt'].includes(ext || '')) return 'text-gray-400';
    if (['html', 'css', 'scss'].includes(ext || '')) return 'text-pink-400';
    return 'text-gray-300';
  };

  return (
    <div>
      <div
        onClick={handleClick}
        className={`
          flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer
          hover:bg-gray-800 transition-colors
          ${isSelected ? 'bg-gray-700' : ''}
        `}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isDirectory && (
          <span className="flex-shrink-0">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        )}
        <span className={`flex-shrink-0 ${getFileColor()}`}>
          {getFileIcon()}
        </span>
        <span className="truncate text-sm">{node.name}</span>
      </div>

      {isDirectory && isExpanded && node.children && (
        <div className="animate-in slide-in-from-top-2 duration-200">
          {node.children.map((child, index) => (
            <TreeNode
              key={`${child.path}-${index}`}
              node={child}
              onFileSelect={onFileSelect}
              selectedPath={selectedPath}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
