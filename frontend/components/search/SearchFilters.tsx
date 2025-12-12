// frontend/components/search/SearchFilters.tsx

'use client';

import { useState } from 'react';
import { Filter, ChevronDown, X } from 'lucide-react';
import { SearchFilters as SearchFiltersType } from '@/lib/types/search';

interface SearchFiltersProps {
  filters: SearchFiltersType;
  onChange: (filters: SearchFiltersType) => void;
}

const LANGUAGE_OPTIONS = [
  'python', 'javascript', 'typescript', 'java', 'go', 
  'rust', 'cpp', 'c', 'ruby', 'php', 'swift', 'kotlin'
];

const SYMBOL_TYPE_OPTIONS = [
  'function', 'class', 'method', 'variable', 
  'constant', 'interface', 'type'
];

export default function SearchFilters({ filters, onChange }: SearchFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);

  const updateFilter = (key: keyof SearchFiltersType, value: any) => {
    onChange({ ...filters, [key]: value });
  };

  const clearFilters = () => {
    onChange({});
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="relative">
      {/* Filter Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg transition"
      >
        <Filter className="h-4 w-4" />
        <span className="text-sm">Filters</span>
        {activeFilterCount > 0 && (
          <span className="px-2 py-0.5 bg-primary text-primary-foreground text-xs rounded-full">
            {activeFilterCount}
          </span>
        )}
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Filter Panel */}
      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-card border border-border rounded-lg shadow-lg z-50 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Search Filters</h3>
            {activeFilterCount > 0 && (
              <button
                onClick={clearFilters}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Clear all
              </button>
            )}
          </div>

          <div className="space-y-4">
            {/* Language Filter */}
            <div>
              <label className="block text-sm font-medium mb-2">Language</label>
              <select
                value={filters.lang || ''}
                onChange={(e) => updateFilter('lang', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-background border border-input rounded-lg"
              >
                <option value="">All languages</option>
                {LANGUAGE_OPTIONS.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang}
                  </option>
                ))}
              </select>
            </div>

            {/* File Pattern */}
            <div>
              <label className="block text-sm font-medium mb-2">File Pattern</label>
              <input
                type="text"
                value={filters.file || ''}
                onChange={(e) => updateFilter('file', e.target.value || undefined)}
                placeholder="e.g., src/**/*.py"
                className="w-full px-3 py-2 bg-background border border-input rounded-lg"
              />
            </div>

            {/* Symbol Type */}
            <div>
              <label className="block text-sm font-medium mb-2">Symbol Type</label>
              <select
                value={filters.symbolType || ''}
                onChange={(e) => updateFilter('symbolType', e.target.value || undefined)}
                className="w-full px-3 py-2 bg-background border border-input rounded-lg"
              >
                <option value="">All types</option>
                {SYMBOL_TYPE_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            {/* Branch */}
            <div>
              <label className="block text-sm font-medium mb-2">Branch</label>
              <input
                type="text"
                value={filters.branch || 'main'}
                onChange={(e) => updateFilter('branch', e.target.value)}
                className="w-full px-3 py-2 bg-background border border-input rounded-lg"
              />
            </div>

            {/* Toggle Options */}
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={filters.includeTests !== false}
                  onChange={(e) => updateFilter('includeTests', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Include test files</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={filters.caseSensitive || false}
                  onChange={(e) => updateFilter('caseSensitive', e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">Case sensitive</span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}