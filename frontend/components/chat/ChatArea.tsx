'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, FileCode, Terminal, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Updated interfaces to match backend schemas
interface SourceReference {
  file_path: string;
  language: string;
  relevance_score: number;
  lines?: string;
}

interface ChatMessage {
  id: number;
  question: string;
  answer: string;
  sources: SourceReference[];
  metadata?: {
    chunks_found?: number;
    avg_similarity?: number;
    model?: string;
    prompt_style?: string;
    streaming?: boolean;
  };
  created_at: string;
}

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (question: string, options?: {
    top_k?: number;
    prompt_style?: 'senior_dev' | 'concise' | 'educational';
    include_sources?: boolean;
    include_metadata?: boolean;
  }) => Promise<void>;
  isLoading: boolean;
}

export default function ChatArea({ messages, onSendMessage, isLoading }: ChatAreaProps) {
  const [input, setInput] = useState('');
  const [promptStyle, setPromptStyle] = useState<'senior_dev' | 'concise' | 'educational'>('senior_dev');
  const [topK, setTopK] = useState(5);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    await onSendMessage(question, {
      top_k: topK,
      prompt_style: promptStyle,
      include_sources: true,
      include_metadata: true
    });
  };

  const promptStyleLabels = {
    senior_dev: { label: 'Senior Dev', icon: '👨‍💻', desc: 'Detailed technical analysis' },
    concise: { label: 'Concise', icon: '⚡', desc: 'Quick and direct answers' },
    educational: { label: 'Educational', icon: '📚', desc: 'Learning-focused explanations' }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-[#0b0c0f] text-gray-100 relative font-sans overflow-hidden">

      {/* Background Gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/10 via-[#0b0c0f] to-[#0b0c0f] pointer-events-none"></div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-800 z-10 relative">
        <div className="w-full max-w-[95%] xl:max-w-[1600px] mx-auto p-4 md:p-8 pb-32 space-y-10">

          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] animate-in fade-in zoom-in duration-500">
              <div className="p-6 rounded-3xl mb-8 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 shadow-2xl">
                <Sparkles className="h-12 w-12 text-indigo-400" />
              </div>
              <h3 className="text-3xl font-bold mb-4 text-white tracking-tight">CodeMind AI</h3>
              <p className="text-gray-400 text-lg max-w-xl text-center mb-10 leading-relaxed">
                I've analyzed your codebase. I can explain complex logic, trace data flows, or help you refactor.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-3xl">
                {[
                  "Where is the authentication logic?",
                  "Explain the database schema",
                  "How do I add a new API endpoint?",
                  "Are there any security vulnerabilities?",
                ].map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => setInput(suggestion)}
                    className="text-left p-5 rounded-2xl border border-gray-800 bg-[#15171e] hover:bg-[#1e212b] hover:border-indigo-500/50 transition-all text-sm text-gray-300 shadow-lg group"
                  >
                    <span className="block text-indigo-500 text-[10px] font-bold uppercase tracking-wider mb-1 opacity-70 group-hover:opacity-100">Sample Query</span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={message.id} className="fade-in duration-500">

                {/* USER MESSAGE */}
                <div className="flex justify-end mb-8 pl-12">
                  <div className="bg-[#1e212b] border border-gray-700 rounded-3xl p-5 shadow-xl max-w-3xl">
                    <p className="text-lg text-gray-200 whitespace-pre-wrap leading-relaxed font-medium">
                      {message.question}
                    </p>
                  </div>
                </div>

                {/* AI MESSAGE */}
                <div className="flex gap-6 mb-12">
                  <div className="p-1 h-fit rounded-xl bg-gradient-to-b from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/10">
                    <div className="bg-[#0b0c0f] p-2 rounded-[10px]">
                      <Bot className="h-6 w-6 text-indigo-400" />
                    </div>
                  </div>

                  <div className="flex-1 min-w-0">
                    {/* Answer Content */}
                    <div className="bg-transparent">
                      <div className="prose prose-invert prose-lg max-w-none text-gray-300">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({ node, inline, className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '')
                              return !inline ? (
                                <div className="my-6 rounded-xl overflow-hidden border border-gray-800 bg-[#0d0e12] shadow-2xl">
                                  <div className="flex items-center justify-between px-4 py-2 bg-[#16181d] border-b border-gray-800">
                                    <span className="text-xs text-gray-500 font-mono uppercase tracking-wider font-bold">{match?.[1] || 'CODE'}</span>
                                    <div className="flex gap-1.5">
                                      <div className="w-2.5 h-2.5 rounded-full bg-red-500/20"></div>
                                      <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20"></div>
                                      <div className="w-2.5 h-2.5 rounded-full bg-green-500/20"></div>
                                    </div>
                                  </div>
                                  <pre className="p-5 overflow-x-auto text-sm font-mono leading-relaxed text-gray-300 scrollbar-thin scrollbar-thumb-gray-700">
                                    <code className={className} {...props}>{children}</code>
                                  </pre>
                                </div>
                              ) : (
                                <code className="bg-indigo-500/10 text-indigo-300 px-1.5 py-0.5 rounded text-sm font-mono border border-indigo-500/20">{children}</code>
                              )
                            },
                            h1: ({ node, ...props }) => <h1 className="text-2xl font-bold mt-10 mb-6 text-white" {...props} />,
                            h2: ({ node, ...props }) => <h2 className="text-xl font-bold mt-8 mb-4 text-gray-100" {...props} />,
                            h3: ({ node, ...props }) => <h3 className="text-lg font-semibold mt-6 mb-3 text-indigo-200" {...props} />,
                            p: ({ node, ...props }) => <p className="mb-5 leading-7 text-gray-300" {...props} />,
                            ul: ({ node, ...props }) => <ul className="list-disc list-outside ml-5 mb-6 space-y-2 text-gray-300 marker:text-indigo-500" {...props} />,
                            li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                            a: ({ node, ...props }) => <a className="text-indigo-400 hover:text-indigo-300 underline underline-offset-4" {...props} />,
                          }}
                        >
                          {message.answer}
                        </ReactMarkdown>
                      </div>

                      {/* Metadata Section (if available) */}
                      {message.metadata && (
                        <div className="mt-6 p-4 bg-[#13151a] border border-gray-800 rounded-xl">
                          <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                            {message.metadata.model && (
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">Model:</span>
                                <span className="text-indigo-400">{message.metadata.model}</span>
                              </div>
                            )}
                            {message.metadata.prompt_style && (
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">Style:</span>
                                <span className="text-purple-400 capitalize">{message.metadata.prompt_style.replace('_', ' ')}</span>
                              </div>
                            )}
                            {message.metadata.chunks_found !== undefined && (
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">Chunks:</span>
                                <span className="text-green-400">{message.metadata.chunks_found}</span>
                              </div>
                            )}
                            {message.metadata.avg_similarity !== undefined && (
                              <div className="flex items-center gap-2">
                                <span className="font-semibold">Avg Similarity:</span>
                                <span className="text-blue-400">{(message.metadata.avg_similarity * 100).toFixed(1)}%</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Sources Section */}
                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-8 pt-6 border-t border-dashed border-gray-800">
                          <div className="flex items-center gap-2 mb-3">
                            <Terminal className="h-4 w-4 text-indigo-500" />
                            <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">Context Sources</span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {message.sources.map((source, idx) => (
                              <div key={idx} className="flex items-center gap-2 px-3 py-2 bg-[#16181d] border border-gray-800 rounded-lg group hover:border-indigo-500/30 transition-colors">
                                <FileCode className="h-3.5 w-3.5 text-gray-500 group-hover:text-indigo-400" />
                                <div className="flex flex-col gap-0.5">
                                  <span className="text-xs font-mono text-gray-400 group-hover:text-gray-200">
                                    {source.file_path}
                                  </span>
                                  <div className="flex items-center gap-2 text-[10px] text-gray-600">
                                    <span className="text-indigo-400">{source.language}</span>
                                    {source.lines && (
                                      <>
                                        <span>•</span>
                                        <span>Lines {source.lines}</span>
                                      </>
                                    )}
                                    <span>•</span>
                                    <span className="text-green-400">{Math.round(source.relevance_score * 100)}%</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area with Settings */}
      <div className="absolute bottom-6 left-0 right-0 px-4 md:px-8 z-50">
        <div className="w-full max-w-[1200px] mx-auto">

          {/* Settings Panel */}
          {showSettings && (
            <div className="mb-3 p-4 bg-[#13151a]/95 backdrop-blur-xl border border-gray-700 rounded-2xl shadow-2xl">
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Query Settings</h4>

              <div className="space-y-4">
                {/* Prompt Style Selector */}
                <div>
                  <label className="text-xs text-gray-500 mb-2 block">Response Style</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(Object.keys(promptStyleLabels) as Array<keyof typeof promptStyleLabels>).map((style) => (
                      <button
                        key={style}
                        onClick={() => setPromptStyle(style)}
                        className={`p-3 rounded-lg border text-left transition-all ${promptStyle === style
                            ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-[#1e212b] border-gray-700 text-gray-400 hover:border-indigo-500/50'
                          }`}
                      >
                        <div className="text-lg mb-1">{promptStyleLabels[style].icon}</div>
                        <div className="text-xs font-semibold">{promptStyleLabels[style].label}</div>
                        <div className="text-[10px] opacity-70">{promptStyleLabels[style].desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Top K Selector */}
                <div>
                  <label className="text-xs text-gray-500 mb-2 block">
                    Code Chunks to Retrieve: <span className="text-indigo-400 font-semibold">{topK}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                  <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                    <span>1 (Fast)</span>
                    <span>20 (Comprehensive)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Input Form */}
          <div className="relative flex items-end gap-3 bg-[#13151a]/95 backdrop-blur-xl border border-gray-700 rounded-2xl p-3 shadow-2xl transition-all ring-1 ring-white/5 focus-within:ring-2 focus-within:ring-indigo-500/50">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about the codebase... (Shift+Enter for new line)"
              disabled={isLoading}
              rows={1}
              className="flex-1 max-h-[200px] px-4 py-3 bg-transparent border-none focus:ring-0 text-lg text-gray-100 placeholder:text-gray-500 resize-none scrollbar-thin scrollbar-thumb-gray-600"
              style={{ minHeight: '52px' }}
            />

            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="p-3.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-all mb-[1px] shadow-lg"
              title="Query Settings"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !input.trim()}
              className="p-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-[1px] shadow-lg"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>

          <div className="text-center mt-3">
            <span className="text-[10px] text-gray-600 font-medium tracking-widest uppercase">
              Powered by Ollama • {promptStyleLabels[promptStyle].label} Mode • Top-{topK} Chunks
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}