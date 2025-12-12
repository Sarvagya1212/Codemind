// frontend/app/repo/[id]/file/[fileId]/page.tsx
'use client';

import { useEffect, useState, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Loader2, Download, Copy, Check } from 'lucide-react';
import Link from 'next/link';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface FileContent {
  file_id: number;
  file_path: string;
  language: string;
  content: string;
  start_line: number;
  end_line: number;
  total_lines: number;
}

export default function FileViewerPage({
  params
}: {
  params: Promise<{ id: string; fileId: string }>;
}) {
  const resolvedParams = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const repoId = parseInt(resolvedParams.id);
  const fileId = parseInt(resolvedParams.fileId);
  const highlightLine = searchParams.get('line') ? parseInt(searchParams.get('line')!) : undefined;

  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchFileContent = async () => {
      if (isNaN(repoId) || isNaN(fileId)) {
        setError('Invalid repository or file ID');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        // Fetch file content from API
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(
          `${API_BASE}/repos/${repoId}/file/${fileId}/content`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch file: ${response.statusText}`);
        }

        const data = await response.json();
        setFileContent(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load file content');
        console.error('Error loading file:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchFileContent();
  }, [repoId, fileId]);

  // Scroll to highlighted line
  useEffect(() => {
    if (highlightLine && fileContent) {
      setTimeout(() => {
        const element = document.getElementById(`line-${highlightLine}`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    }
  }, [highlightLine, fileContent]);

  const handleCopyContent = async () => {
    if (fileContent) {
      await navigator.clipboard.writeText(fileContent.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (fileContent) {
      const blob = new Blob([fileContent.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileContent.file_path.split('/').pop() || 'file.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading file...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="border-b border-border bg-card">
          <div className="container mx-auto px-4 py-4">
            <Link
              href={`/search/${repoId}`}
              className="inline-flex items-center gap-2 p-2 hover:bg-accent rounded-lg transition"
            >
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Search</span>
            </Link>
          </div>
        </div>
        <div className="container mx-auto px-4 py-8">
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center">
            <h2 className="text-xl font-bold text-destructive mb-2">Error Loading File</h2>
            <p className="text-muted-foreground">{error}</p>
            <button
              onClick={() => router.back()}
              className="mt-4 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!fileContent) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">File not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <Link
                href={`/search/${repoId}`}
                className="p-2 hover:bg-accent rounded-lg transition flex-shrink-0"
              >
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div className="min-w-0 flex-1">
                <h1 className="text-lg font-semibold truncate" title={fileContent.file_path}>
                  {fileContent.file_path}
                </h1>
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span className="px-2 py-0.5 bg-primary/10 text-primary rounded">
                    {fileContent.language}
                  </span>
                  <span>{fileContent.total_lines} lines</span>
                  {highlightLine && (
                    <span className="text-yellow-500">
                      Highlighting line {highlightLine}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={handleCopyContent}
                className="flex items-center gap-2 px-3 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4" />
                    <span className="hidden sm:inline">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    <span className="hidden sm:inline">Copy</span>
                  </>
                )}
              </button>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-3 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline">Download</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* File Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <SyntaxHighlighter
            language={fileContent.language}
            style={vscDarkPlus}
            showLineNumbers={true}
            startingLineNumber={1}
            customStyle={{
              margin: 0,
              padding: '1.5rem',
              background: 'transparent',
              fontSize: '0.875rem',
            }}
            wrapLines={true}
            lineProps={(lineNumber) => {
              const style: any = { display: 'block' };
              
              // Highlight the target line
              if (lineNumber === highlightLine) {
                style.backgroundColor = 'rgba(255, 255, 0, 0.1)';
                style.borderLeft = '3px solid #facc15';
                style.paddingLeft = '0.5rem';
                style.id = `line-${lineNumber}`;
              }
              
              return { style };
            }}
          >
            {fileContent.content}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  );
}