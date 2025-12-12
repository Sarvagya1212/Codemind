'use client';

import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileContent } from '@/lib/api';
import { File as FileIcon, Copy, Check } from 'lucide-react';

interface CodeViewerProps {
  fileContent: FileContent | null;
  loading: boolean;
  error: string | null;
}

export default function CodeViewer({ fileContent, loading, error }: CodeViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (fileContent) {
      navigator.clipboard.writeText(fileContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900 text-gray-400">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p>Loading file...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900 text-red-400">
        <div className="text-center">
          <p className="text-lg font-semibold">Error</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!fileContent) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900 text-gray-500">
        <div className="text-center">
          <FileIcon size={48} className="mx-auto mb-3 opacity-50" />
          <p>Select a file to view its contents</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2 text-gray-300">
          <FileIcon size={16} />
          <span className="font-mono text-sm">{fileContent.file_path}</span>
          <span className="text-xs text-gray-500">
            ({fileContent.lines} lines · {(fileContent.size_bytes / 1024).toFixed(1)} KB)
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded transition-colors"
        >
          {copied ? (
            <>
              <Check size={14} />
              Copied
            </>
          ) : (
            <>
              <Copy size={14} />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div className="flex-1 overflow-auto">
        <SyntaxHighlighter
          language={fileContent.language}
          style={vscDarkPlus}
          showLineNumbers
          wrapLines
          customStyle={{
            margin: 0,
            padding: '1rem',
            background: 'transparent',
            fontSize: '0.875rem',
          }}
          lineNumberStyle={{
            minWidth: '3em',
            paddingRight: '1em',
            color: '#6b7280',
            userSelect: 'none',
          }}
        >
          {fileContent.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
