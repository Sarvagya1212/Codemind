// frontend/app/search/[id]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertCircle, RefreshCw, Trash2, Info } from 'lucide-react';
import Link from 'next/link';
import { useCodeSearch } from '@/lib/hooks/useCodeSearch';
import { useIndexStatus } from '@/lib/hooks/useIndexStatus';
import { SearchMode, SearchResultItem, MatchType } from '@/lib/types/search';
import { searchApi } from '@/lib/api';
import SearchOmnibox from '@/components/search/SearchOmnibox';
import SearchFilters from '@/components/search/SearchFilters';
import SearchResults from '@/components/search/SearchResults';

export default function SearchPage() {
  const params = useParams();
  const router = useRouter();
  const repoId = parseInt(params.id as string);
  const [indexStats, setIndexStats] = useState<any>(null);
  const [showIndexOptions, setShowIndexOptions] = useState(false);

  // Index status
  const { status: indexStatus, isLoading: indexLoading, startIndexing } =
    useIndexStatus(repoId);

  // Search state
  const {
    query,
    setQuery,
    results,
    totalResults,
    isLoading: searchLoading,
    error: searchError,
    latency,
    currentPage,
    mode,
    setMode,
    filters,
    setFilters,
    search,
    nextPage,
    prevPage,
    goToPage
  } = useCodeSearch(repoId, '', {
    mode: SearchMode.HYBRID,
    autoSearch: false,
    perPage: 20
  });

  const [isIndexing, setIsIndexing] = useState(false);

  // Fetch index stats
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const stats = await searchApi.getIndexStats(repoId);
        setIndexStats(stats);
      } catch (error) {
        console.error('Failed to fetch index stats:', error);
      }
    };
    fetchStats();
  }, [repoId]);

  // FIXED: Handle result click with proper debugging
  const handleResultClick = (result: SearchResultItem) => {
    // Ensure matchType is MatchType[]
    if (!Array.isArray(result.matchType) || result.matchType.some(mt => typeof mt !== 'string')) {
      console.error('ERROR: Invalid matchType:', result.matchType);
      alert('Error: Invalid matchType');
      return;
    }

    console.log('=== SEARCH RESULT CLICK DEBUG ===');
    console.log('Full result object:', result);
    console.log('fileId type:', typeof result.fileId, 'value:', result.fileId);
    console.log('startLine:', result.startLine);
    console.log('repoId:', repoId);

    // Ensure fileId is a number
    const fileId = Number(result.fileId);

    if (isNaN(fileId)) {
      console.error('ERROR: Invalid fileId:', result.fileId);
      alert('Error: Invalid file ID');
      return;
    }

    const line = result.startLine ?? 1;

    // This should match your file route: /repo/[id]/file/[fileId]/page.tsx
    const url = `/repo/${repoId}/file/${fileId}?line=${line}`;

    console.log('Navigating to URL:', url);
    console.log('Expected route: app/repo/[id]/file/[fileId]/page.tsx');
    console.log('================================');

    router.push(url);
  };

  // Start indexing if not indexed yet
  const handleStartIndexing = async () => {
    setIsIndexing(true);
    try {
      await startIndexing({
        incremental: false,
        force: true
      });
    } catch (error) {
      console.error('Failed to start indexing:', error);
    } finally {
      setIsIndexing(false);
    }
  };

  const handleClearIndex = async () => {
    if (!confirm('Are you sure you want to clear the entire index? This cannot be undone.')) {
      return;
    }
    try {
      await searchApi.clearIndex(repoId);
      alert('Index cleared successfully! You can now re-index.');
      window.location.reload();
    } catch (error) {
      alert('Failed to clear index');
    }
  };

  const handleStartIndexingMode = async (mode: 'full' | 'incremental') => {
    try {
      await searchApi.startIndexing(repoId, {
        force: mode === 'full',
        incremental: mode === 'incremental',
        branch: 'main'
      });
      alert(`${mode === 'full' ? 'Full' : 'Incremental'} indexing started!`);
      window.location.reload();
    } catch (error) {
      alert('Failed to start indexing');
    }
  };

  const isIndexed = indexStats?.files_indexed > 0 && indexStats?.chunks_created > 0;
  const isIndexingInProgress =
    indexStatus?.status === 'running' ||
    indexStatus?.status === 'pending';

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href={`/repo/${repoId}`}
                className="p-2 hover:bg-accent rounded-lg transition"
              >
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold">Code Search</h1>
                <p className="text-sm text-muted-foreground">
                  Semantic + Keyword + Symbol hybrid search
                </p>
              </div>
            </div>
            {/* Index Status Indicator */}
            {indexStatus && (
              <div className="flex items-center gap-3">
                {isIndexingInProgress && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>
                      Indexing... {Math.round(indexStatus.progress * 100)}%
                    </span>
                  </div>
                )}
                {isIndexed && (
                  <div className="flex items-center gap-2 text-sm text-green-500">
                    <div className="h-2 w-2 bg-green-500 rounded-full" />
                    <span>Indexed</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Index Stats Banner */}
        {indexStats && isIndexed && (
          <div className="mb-6 p-4 bg-card border border-border rounded-lg">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Index Status
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Files Indexed</div>
                    <div className="font-semibold">{indexStats.files_indexed}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Code Chunks</div>
                    <div className="font-semibold">{indexStats.chunks_created}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Symbols</div>
                    <div className="font-semibold">{indexStats.symbols_extracted}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Embeddings</div>
                    <div className="font-semibold">{indexStats.embeddings_count}</div>
                  </div>
                </div>
                {indexStats.last_indexed_at && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    Last indexed: {new Date(indexStats.last_indexed_at).toLocaleString()}
                  </div>
                )}
              </div>
              <button
                onClick={() => setShowIndexOptions(!showIndexOptions)}
                className="px-3 py-1 text-sm border border-border rounded hover:bg-accent"
              >
                Manage Index
              </button>
            </div>
            {showIndexOptions && (
              <div className="mt-4 pt-4 border-t border-border">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <button
                    onClick={() => handleStartIndexingMode('incremental')}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Incremental Update
                  </button>
                  <button
                    onClick={() => handleStartIndexingMode('full')}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Full Re-index
                  </button>
                  <button
                    onClick={handleClearIndex}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-lg transition"
                  >
                    <Trash2 className="h-4 w-4" />
                    Clear Index
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Not Indexed Banner */}
        {!isIndexed && !isIndexingInProgress && (
          <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-500 mb-1">
                  Repository Not Indexed
                </h3>
                <p className="text-sm text-muted-foreground mb-3">
                  This repository needs to be indexed before you can search.
                </p>
                <button
                  onClick={handleStartIndexing}
                  disabled={isIndexing}
                  className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg transition disabled:opacity-50 flex items-center gap-2"
                >
                  {isIndexing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    'Start Indexing'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Search Input */}
        <div className="mb-6">
          <SearchOmnibox
            repoId={repoId}
            value={query}
            onChange={setQuery}
            onSearch={search}
            mode={mode}
            onModeChange={setMode}
            isLoading={searchLoading}
          />
        </div>

        {/* Filters & Results Info */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            {totalResults > 0 && (
              <div className="text-sm text-muted-foreground">
                Found <span className="font-semibold text-foreground">{totalResults}</span> results
                {latency > 0 && (
                  <span className="ml-2">
                    in <span className="font-semibold">{latency}ms</span>
                  </span>
                )}
              </div>
            )}
          </div>
          <SearchFilters filters={filters} onChange={setFilters} />
        </div>

        {/* Search Error */}
        {searchError && (
          <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-destructive mb-1">Search Error</h3>
                <p className="text-sm text-muted-foreground">{searchError}</p>
              </div>
            </div>
          </div>
        )}

        {/* Results - Pass repoId and handler */}
        <SearchResults
          results={results.map(result => ({
            ...result,
            matchType: Array.isArray(result.matchType)
              ? result.matchType.map(mt => typeof mt === 'string' ? mt as MatchType : mt)
              : []
          }))}
          query={query}
          repoId={repoId}
          onResultClick={handleResultClick}
          isLoading={searchLoading}
          totalResults={totalResults}
        />

        {/* Pagination */}
        {totalResults > 0 && (
          <div className="mt-8 flex items-center justify-center gap-2">
            <button
              onClick={prevPage}
              disabled={currentPage === 1}
              className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, Math.ceil(totalResults / 20)) }, (_, i) => {
                const page = i + 1;
                return (
                  <button
                    key={page}
                    onClick={() => goToPage(page)}
                    className={`px-3 py-2 rounded-lg transition ${
                      currentPage === page
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary hover:bg-secondary/80'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}
            </div>
            <button
              onClick={nextPage}
              disabled={currentPage >= Math.ceil(totalResults / 20)}
              className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}