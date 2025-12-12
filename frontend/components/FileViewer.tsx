// frontend/components/FileViewer.tsx

'use client';

import { useState, useEffect, useRef } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Download, ExternalLink, Check } from 'lucide-react';

interface FileViewerProps {
  repoId: number;
  fileId: number;
  filePath: string;
  language: string;
  content: string;
  highlightLine?: number;
  startLine?: number;
  endLine?: number;
}

export default function FileViewer({
  repoId,
  fileId,
  filePath,
  language,
  content,
  highlightLine,
  startLine = 1,
  endLine
}: FileViewerProps) {
  const [copied, setCopied] = useState(false);
  const highlightRef = useRef<HTMLDivElement>(null);

  // Scroll to highlighted line
  useEffect(() => {
    if (highlightLine && highlightRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }, 100);
    }
  }, [highlightLine]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath.split('/').pop() || 'file.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Custom line props to highlight specific line
  const lineProps = (lineNumber: number) => {
    const style: any = { display: 'block' };
    
    if (highlightLine && lineNumber === highlightLine) {
      style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
      style.borderLeft = '3px solid rgb(59, 130, 246)';
      style.paddingLeft = '0.5rem';
    }
    
    return { style };
  };

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-secondary/30">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded">
            <ExternalLink className="h-4 w-4 text-primary" />
          </div>
          <div>
            <div className="font-mono text-sm font-medium">{filePath}</div>
            <div className="text-xs text-muted-foreground">
              {language} • Lines {startLine}-{endLine || 'end'}
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

      {/* Code Content */}
      <div className="overflow-x-auto" ref={highlightRef}>
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          showLineNumbers={true}
          startingLineNumber={startLine}
          wrapLines={true}
          lineProps={lineProps}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: '14px',
            background: 'transparent'
          }}
        >
          {content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}