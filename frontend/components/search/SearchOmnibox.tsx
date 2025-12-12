// frontend/components/search/SearchOmnibox.tsx

'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Search,
  X,
  Loader2,
  Code2,
  FileCode,
  Sparkles
} from 'lucide-react';
import { SearchMode } from '@/lib/types/search';
import { useSymbolAutocomplete } from '@/lib/hooks/useSymbolAutocomplete';

interface SearchOmniboxProps {
  repoId: number;
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export default function SearchOmnibox({
  repoId,
  value,
  onChange,
  onSearch,
  mode,
  onModeChange,
  isLoading,
  placeholder = 'Search code... (Try: "Where is authentication?" or @symbolName)'
}: SearchOmniboxProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showModeSelector, setShowModeSelector] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // FIX: Ensure value is always a string
  const valueStr = String(value || '');
  const isSymbolQuery = valueStr.startsWith('@') || valueStr.startsWith('symbol:');
  const symbolQuery = isSymbolQuery
    ? valueStr.replace(/^(@|symbol:)/, '').trim()
    : '';

  // Symbol autocomplete
  const { symbols, isLoading: symbolsLoading } = useSymbolAutocomplete(
    repoId,
    symbolQuery,
    {
      enabled: isSymbolQuery && symbolQuery.length > 1,
      limit: 10
    }
  );

  // Auto-select symbol mode when @ prefix detected
  useEffect(() => {
    if (valueStr.startsWith('@') && mode !== SearchMode.SYMBOL) {
      onModeChange(SearchMode.SYMBOL);
    }
  }, [valueStr, mode, onModeChange]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (valueStr.trim()) {
        onSearch();
        setShowSuggestions(false);
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      inputRef.current?.blur();
    }
  };

  const handleSymbolSelect = (symbolName: string) => {
    onChange(symbolName);
    onModeChange(SearchMode.SYMBOL);
    setShowSuggestions(false);
    setTimeout(() => onSearch(), 100);
  };

  const getModeIcon = () => {
    switch (mode) {
      case SearchMode.SEMANTIC:
        return <Sparkles className="h-4 w-4" />;
      case SearchMode.SYMBOL:
        return <Code2 className="h-4 w-4" />;
      case SearchMode.KEYWORD:
        return <FileCode className="h-4 w-4" />;
      case SearchMode.REGEX:
        return <span className="text-xs font-bold">.*</span>;
      default:
        return <Search className="h-4 w-4" />;
    }
  };

  const getModeColor = () => {
    switch (mode) {
      case SearchMode.SEMANTIC:
        return 'text-purple-500';
      case SearchMode.SYMBOL:
        return 'text-blue-500';
      case SearchMode.KEYWORD:
        return 'text-green-500';
      case SearchMode.REGEX:
        return 'text-orange-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="relative w-full">
      {/* Search Input */}
      <div className="relative flex items-center">
        {/* Mode Indicator */}
        <button
          onClick={() => setShowModeSelector(!showModeSelector)}
          className={`absolute left-3 z-10 p-1 rounded hover:bg-accent transition ${getModeColor()}`}
          title={`Search mode: ${mode}`}
        >
          {getModeIcon()}
        </button>

        {/* Input Field */}
        <input
          ref={inputRef}
          type="text"
          value={valueStr}
          onChange={(e) => {
            onChange(e.target.value || '');
            setShowSuggestions(true);
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(true)}
          placeholder={placeholder}
          className="w-full pl-12 pr-24 py-3 bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        />

        {/* Right Actions */}
        <div className="absolute right-3 flex items-center gap-2">
          {isLoading && (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          )}
          
          {valueStr && (
            <button
              onClick={() => {
                onChange('');
                inputRef.current?.focus();
              }}
              className="p-1 hover:bg-accent rounded transition"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
          
          <button
            onClick={onSearch}
            disabled={!valueStr.trim() || isLoading}
            className="px-3 py-1 bg-primary hover:bg-primary/90 text-primary-foreground rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Search
          </button>
        </div>
      </div>

      {/* Mode Selector Dropdown */}
      {showModeSelector && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 mt-2 w-64 bg-card border border-border rounded-lg shadow-lg z-50 py-2"
        >
          <div className="px-3 py-2 text-xs font-semibold text-muted-foreground">
            Search Mode
          </div>
          {Object.values(SearchMode).map((modeOption) => (
            <button
              key={modeOption}
              onClick={() => {
                onModeChange(modeOption);
                setShowModeSelector(false);
              }}
              className={`w-full px-3 py-2 text-left hover:bg-accent transition flex items-center gap-2 ${
                mode === modeOption ? 'bg-accent' : ''
              }`}
            >
              <span className="text-xs font-medium capitalize">{modeOption}</span>
            </button>
          ))}
        </div>
      )}

      {/* Symbol Suggestions */}
      {showSuggestions && isSymbolQuery && symbols.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto"
        >
          <div className="px-3 py-2 text-xs font-semibold text-muted-foreground border-b border-border">
            Symbols
          </div>
          {symbols.map((symbol) => (
            <button
              key={symbol.id}
              onClick={() => handleSymbolSelect(symbol.name)}
              className="w-full px-3 py-2 text-left hover:bg-accent transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-mono text-sm">{symbol.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {symbol.symbolType} • {symbol.filePath}
                  </div>
                </div>
                <span className="text-xs px-2 py-1 bg-secondary rounded">
                  {symbol.symbolType}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Helper Text */}
      <div className="mt-2 text-xs text-muted-foreground">
        <span className="font-medium">Tips:</span> Use{' '}
        <code className="px-1 bg-secondary rounded">@symbolName</code> for symbols,{' '}
        <code className="px-1 bg-secondary rounded">regex:</code> prefix for regex search
      </div>
    </div>
  );
}