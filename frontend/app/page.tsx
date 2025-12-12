'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Github, Loader2, ArrowRight, Sparkles, Code2, MessageSquare, Zap, CheckCircle2, FileCode, RefreshCw, Trash2 } from 'lucide-react';
import { repositoryApi, pollRepositoryStatus, Repository } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [githubUrl, setGithubUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<'idle' | 'ingesting' | 'polling' | 'ready'>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [repoId, setRepoId] = useState<number | null>(null);
  
  // NEW: Repository list state
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState(true);
  const [showRepoList, setShowRepoList] = useState(false);

  // NEW: Load repositories on mount
  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      setIsLoadingRepos(true);
      const repos = await repositoryApi.list();
      setRepositories(repos);
      setShowRepoList(repos.length > 0);
    } catch (error) {
      console.error('Failed to load repositories:', error);
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCurrentStep('idle');
    setProgress(0);
    setRepoId(null);

    if (!githubUrl.trim()) {
      setError('Please enter a GitHub repository URL');
      return;
    }

    if (!githubUrl.includes('github.com')) {
      setError('Please enter a valid GitHub URL');
      return;
    }

    setIsLoading(true);

    try {
      setCurrentStep('ingesting');
      setStatusMessage('Starting repository ingestion...');
      setProgress(10);

      const repo = await repositoryApi.ingest(githubUrl);
      setRepoId(repo.id);
      setProgress(20);
      setStatusMessage('Repository created! Processing codebase...');

      setCurrentStep('polling');
      let pollAttempts = 0;
      const maxAttempts = 120;

      await pollRepositoryStatus(
        repo.id,
        (currentStatus) => {
          pollAttempts++;
          const pollProgress = 20 + (pollAttempts / maxAttempts) * 70;
          setProgress(Math.min(pollProgress, 90));

          if (currentStatus === 'pending') {
            setStatusMessage('Waiting to start processing...');
          } else if (currentStatus === 'processing') {
            setStatusMessage('Cloning repository, parsing code, and creating embeddings...');
          } else if (currentStatus === 'completed') {
            setStatusMessage('Repository ready!');
            setProgress(100);
          } else if (currentStatus === 'failed') {
            throw new Error('Repository processing failed');
          }
        },
        maxAttempts,
        10000
      );

      setCurrentStep('ready');
      setProgress(100);
      setIsLoading(false);
      
      // Reload repositories list
      loadRepositories();

    } catch (err: any) {
      console.error('Error ingesting repository:', err);
      let errorMessage = 'Failed to ingest repository. Please try again.';

      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message === 'Timeout waiting for repository to be processed') {
        errorMessage = 'Repository processing is taking longer than expected. Please check back later.';
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
      setIsLoading(false);
      setCurrentStep('idle');
      setProgress(0);
      setRepoId(null);
    }
  };

  // NEW: Handle re-ingest
  const handleReingest = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm('Re-ingest this repository? This will re-clone and re-index all files.')) {
      return;
    }

    try {
      await repositoryApi.reingest(id);
      alert('Re-ingestion started! The repository will be processed in the background.');
      loadRepositories();
    } catch (error) {
      console.error('Reingest error:', error);
      alert('Failed to start re-ingestion');
    }
  };

  // NEW: Handle delete
  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm('Delete this repository? This will remove all data including chat history.')) {
      return;
    }

    try {
      await repositoryApi.delete(id);
      setRepositories(prev => prev.filter(repo => repo.id !== id));
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete repository');
    }
  };

  const getStepStatus = (step: string) => {
    const steps = ['ingesting', 'polling', 'ready'];
    const currentIndex = steps.indexOf(currentStep);
    const stepIndex = steps.indexOf(step);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <Sparkles className="w-12 h-12 text-purple-500 mr-3" />
            <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-purple-600 bg-clip-text text-transparent">
              CodeMind AI
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Ingest any GitHub repository and have intelligent conversations about the code using AI-powered RAG technology.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-12 max-w-5xl mx-auto">
          <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-6">
            <Code2 className="w-10 h-10 text-blue-500 mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">Code Analysis</h3>
            <p className="text-gray-400 text-sm">
              AI-powered analysis of your entire codebase structure and patterns
            </p>
          </div>

          <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-6">
            <MessageSquare className="w-10 h-10 text-green-500 mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">Smart Conversations</h3>
            <p className="text-gray-400 text-sm">
              Ask questions in plain English and get contextual answers
            </p>
          </div>

          <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-6">
            <Zap className="w-10 h-10 text-yellow-500 mb-3" />
            <h3 className="text-lg font-semibold text-white mb-2">Lightning Fast</h3>
            <p className="text-gray-400 text-sm">
              Powered by advanced RAG technology for precise results
            </p>
          </div>
        </div>

        {/* Main Card */}
        <div className="max-w-2xl mx-auto mb-12">
          <div className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-2xl p-8 shadow-2xl">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="github-url" className="block text-sm font-medium text-gray-300 mb-2">
                  GitHub Repository URL
                </label>
                <div className="relative">
                  <Github className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
                  <input
                    id="github-url"
                    type="text"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    disabled={isLoading}
                    className="w-full pl-11 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}

              {/* Progress Section */}
              {isLoading && (
                <div className="space-y-4">
                  <div className="bg-gray-800/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-400">{statusMessage}</span>
                      <span className="text-sm text-purple-400">{Math.round(progress)}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  {/* Progress Steps */}
                  <div className="flex justify-between items-center">
                    {[
                      { id: 'ingesting', label: 'Ingesting', icon: Github },
                      { id: 'polling', label: 'Processing', icon: Loader2 },
                      { id: 'ready', label: 'Ready', icon: CheckCircle2 },
                    ].map((step) => {
                      const status = getStepStatus(step.id);
                      const Icon = step.icon;
                      return (
                        <div key={step.id} className="flex flex-col items-center">
                          <div
                            className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-all ${
                              status === 'completed'
                                ? 'bg-green-500/20 border-2 border-green-500'
                                : status === 'active'
                                ? 'bg-purple-500/20 border-2 border-purple-500 animate-pulse'
                                : 'bg-gray-800 border-2 border-gray-700'
                            }`}
                          >
                            <Icon
                              className={`w-6 h-6 ${
                                status === 'completed'
                                  ? 'text-green-500'
                                  : status === 'active'
                                  ? 'text-purple-500'
                                  : 'text-gray-600'
                              } ${status === 'active' && step.id === 'polling' ? 'animate-spin' : ''}`}
                            />
                          </div>
                          <span
                            className={`text-xs ${
                              status !== 'pending' ? 'text-gray-300' : 'text-gray-600'
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Success State */}
              {currentStep === 'ready' && repoId && (
                <div className="space-y-4">
                  <div className="bg-green-900/20 border border-green-800 rounded-lg p-4">
                    <div className="flex items-center gap-2 text-green-400">
                      <CheckCircle2 className="w-5 h-5" />
                      <p className="font-medium">Repository ingested successfully!</p>
                    </div>
                    <p className="text-gray-400 text-sm mt-1">Choose what you'd like to do:</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {/* ✅ FIXED: Use /repo not /chat */}
                    <button
                      type="button"
                      onClick={() => router.push(`/repo/${repoId}`)}
                      className="flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-lg transition-all transform hover:scale-105 shadow-lg"
                    >
                      <MessageSquare className="w-5 h-5" />
                      Chat with Code
                    </button>

                    {/* This one is already correct */}
                    <button
                      type="button"
                      onClick={() => router.push(`/repo/${repoId}/files`)}
                      className="flex items-center justify-center gap-2 px-6 py-4 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white font-semibold rounded-lg transition-all transform hover:scale-105 shadow-lg"
                    >
                      <FileCode className="w-5 h-5" />
                      View Files
                    </button>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              {currentStep === 'idle' && (
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-700 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed shadow-lg"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Start Ingesting
                      <ArrowRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              )}
            </form>
          </div>

          <p className="text-center text-gray-500 text-sm mt-6">
            Enter any public GitHub repository URL to start analyzing the code
          </p>
        </div>

        {/* Repository List Section */}
{showRepoList && (
  <div className="max-w-6xl mx-auto">
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-2xl font-bold text-white">Your Repositories</h2>
      <button
        onClick={loadRepositories}
        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Refresh
      </button>
    </div>

    {isLoadingRepos ? (
      <div className="text-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500 mx-auto mb-4" />
        <p className="text-gray-400">Loading repositories...</p>
      </div>
    ) : (
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {repositories.map((repo) => {
          const repoName = repo.github_url.split('/').pop()?.replace('.git', '') || 'Repository';
          const fileCount = repo.repo_metadata?.total_files || 0;
          const canReingest = repo.status === 'completed' || repo.status === 'failed';

          return (
            <div
              key={repo.id}
              onClick={() => router.push(`/repo/${repo.id}`)} 
              className="bg-gray-900/50 backdrop-blur border border-gray-800 rounded-lg p-5 hover:border-purple-500/50 transition-all cursor-pointer group"
            >
              <div className="mb-3">
                <h3 className="font-semibold text-lg text-white mb-1 truncate group-hover:text-purple-400 transition-colors">
                  {repoName}
                </h3>
                <p className="text-sm text-gray-400 truncate">{repo.github_url}</p>
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
                <div className="flex items-center gap-1">
                  <FileCode className="w-4 h-4" />
                  {fileCount} files
                </div>
              </div>

              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs px-2 py-1 rounded ${
                  repo.status === 'completed' ? 'bg-green-900/30 text-green-400 border border-green-800' :
                  repo.status === 'processing' ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-800' :
                  repo.status === 'failed' ? 'bg-red-900/30 text-red-400 border border-red-800' :
                  'bg-gray-800 text-gray-400 border border-gray-700'
                }`}>
                  {repo.status}
                </span>

                <div className="flex gap-1">
                  {canReingest && (
                    <button
                      onClick={(e) => handleReingest(repo.id, e)}
                      className="p-2 text-gray-400 hover:text-blue-400 hover:bg-blue-950/20 rounded transition-colors"
                      title="Re-ingest repository"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  )}

                  <button
                    onClick={(e) => handleDelete(repo.id, e)}
                    className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-950/20 rounded transition-colors"
                    title="Delete repository"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    )}
  </div>
)}

      </div>
    </div>
  );
}

