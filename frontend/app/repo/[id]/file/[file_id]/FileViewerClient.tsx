// frontend/app/repo/[id]/file/[fileId]/FileViewerClient.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Copy, Download, Check, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { searchApi } from '@/lib/api';

interface FileViewerClientProps {
  repoId: number;
  fileId: number;
  highlightLine?: number;
}

export default function FileViewerClient({ 
  repoId, 
  fileId, 
  highlightLine 
}: FileViewerClientProps) {
  const router = useRouter();
  const [file, setFile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchFile = async () => {
      try {
        const fileData = await searchApi.getFileContent(repoId, fileId);
        setFile(fileData);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load file');
      } finally {
        setIsLoading(false);
      }
    };

    fetchFile();
  }, [repoId, fileId]);

  // Scroll to highlighted line
  useEffect(() => {
    if (highlightLine && !isLoading) {
      setTimeout(() => {
        const element = document.querySelector(`[data-line-number="${highlightLine}"]`);
        element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [highlightLine, isLoading]);

  const handleCopy = async () => {
    if (file) {
      await navigator.clipboard.writeText(file.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (file) {
      const blob = new Blob([file.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.file_path.split('/').pop() || 'file.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Error Loading File</h2>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  if (!file) {
    return null;
  }

  // Custom line props to highlight specific line
  const lineProps = (lineNumber: number) => {
    const style: any = { display: 'block' };
    if (highlightLine && lineNumber === highlightLine) {
      style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
      style.borderLeft = '3px solid rgb(59, 130, 246)';
      style.paddingLeft = '0.5rem';
    }
    return { 
      style, 
      'data-line-number': lineNumber 
    };
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="p-2 hover:bg-accent rounded-lg transition"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div>
                <div className="font-mono text-sm font-medium">{file.file_path}</div>
                <div className="text-xs text-muted-foreground">
                  {file.language} • Lines {file.start_line}-{file.end_line}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopy}
                className="p-2 hover:bg-accent rounded transition"
                title="Copy to clipboard"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={handleDownload}
                className="p-2 hover:bg-accent rounded transition"
                title="Download file"
              >
                <Download className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Code Content */}
      <div className="container mx-auto px-4 py-4">
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <SyntaxHighlighter
            language={file.language}
            style={vscDarkPlus}
            showLineNumbers={true}
            startingLineNumber={file.start_line}
            wrapLines={true}
            lineProps={lineProps}
            customStyle={{
              margin: 0,
              borderRadius: 0,
              fontSize: '14px',
              background: 'transparent'
            }}
          >
            {file.content}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  );
}