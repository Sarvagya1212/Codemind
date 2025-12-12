// frontend/components/search/SearchResults.tsx
'use client';

import React from 'react';
import { Zap, Search, Code, Layers, ChevronRight } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { SearchResultItem } from '@/lib/types/search';

interface SearchResultsProps {
  results: SearchResultItem[];
  query: string;
  repoId: number;
  isLoading?: boolean;
  totalResults?: number;
  onResultClick: (result: SearchResultItem) => void; // Use the passed handler
}

export default function SearchResults({
  results,
  query,
  repoId,
  isLoading,
  totalResults,
  onResultClick, // Receive handler from parent
}: SearchResultsProps) {
  const getMatchQuality = (score: number) => {
    if (score > 0.8) return { label: 'Excellent', color: 'text-green-400', bg: 'bg-green-500/20' };
    if (score > 0.6) return { label: 'Good', color: 'text-blue-400', bg: 'bg-blue-500/20' };
    return { label: 'Moderate', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500" />
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <Search className="w-16 h-16 mx-auto mb-4 text-gray-500" />
        <h3 className="text-xl font-semibold mb-2">No Results Found</h3>
        <p className="text-gray-400">Try a different search query or mode</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-gray-400">
        <span>
          Found <strong className="text-white">{totalResults || results.length}</strong> results
          for "<strong className="text-purple-400">{query}</strong>"
        </span>
      </div>

      {/* Results List */}
      {results.map((result, index) => {
        const quality = getMatchQuality(result.relevanceScore);
        
        return (
          <div
            key={`${result.fileId}-${result.startLine}-${index}`}
            onClick={() => {
              console.log('Result clicked:', result);
              onResultClick(result); // Use passed handler
            }}
            className="bg-slate-800 border border-slate-700 rounded-lg p-6 hover:border-purple-500 hover:shadow-lg hover:shadow-purple-500/10 transition-all cursor-pointer group"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-lg group-hover:text-purple-400 transition-colors">
                    {result.filePath}
                  </h3>
                  <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-purple-400 transition-colors" />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                    {result.language}
                  </span>
                  <span className="text-xs text-gray-400">
                    Lines {result.startLine}-{result.endLine}
                  </span>
                  {result.symbolName && (
                    <span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded">
                      {result.symbolType}: {result.symbolName}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    File ID: {result.fileId}
                  </span>
                </div>
              </div>

              {/* Relevance Score */}
              <div className="text-right ml-4">
                <div className="text-3xl font-bold text-purple-400">
                  {(result.relevanceScore * 100).toFixed(0)}%
                </div>
                <div className={`text-xs ${quality.color}`}>{quality.label}</div>
              </div>
            </div>

            {/* Match Type Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              {result.semanticScore && result.semanticScore > 0 && (
                <div className="flex items-center gap-1 text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded">
                  <Zap className="w-3 h-3" />
                  Semantic {(result.semanticScore * 100).toFixed(0)}%
                </div>
              )}
              {result.keywordScore && result.keywordScore > 0 && (
                <div className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                  <Search className="w-3 h-3" />
                  Keyword {(result.keywordScore * 100).toFixed(0)}%
                </div>
              )}
              {result.symbolScore && result.symbolScore > 0 && (
                <div className="flex items-center gap-1 text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded">
                  <Code className="w-3 h-3" />
                  Symbol {(result.symbolScore * 100).toFixed(0)}%
                </div>
              )}
              {result.matchType && Array.isArray(result.matchType) && result.matchType.length > 1 && (
                <div className="flex items-center gap-1 text-xs bg-orange-500/20 text-orange-300 px-2 py-1 rounded">
                  <Layers className="w-3 h-3" />
                  Multi-match Bonus
                </div>
              )}
            </div>

            {/* Code Snippet */}
            <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-700">
              <SyntaxHighlighter
                language={result.language}
                style={vscDarkPlus}
                showLineNumbers={true}
                startingLineNumber={result.startLine}
                customStyle={{
                  margin: 0,
                  padding: '1rem',
                  background: 'transparent',
                  fontSize: '0.8rem',
                  maxHeight: '200px',
                }}
                wrapLines={true}
              >
                {result.snippet}
              </SyntaxHighlighter>
            </div>

            {/* Why This Matched */}
            {result.matchType && Array.isArray(result.matchType) && result.matchType.length > 1 && (
              <div className="mt-4 text-sm bg-slate-900/50 p-3 rounded border border-slate-700">
                <strong className="text-purple-400">Why this matched:</strong>{' '}
                <span className="text-gray-400">
                  Found through {result.matchType.join(', ')} analysis.
                  {result.semanticScore && result.semanticScore > 0.7 &&
                    ' High semantic similarity means the code conceptually matches your query even if exact keywords differ.'}
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}