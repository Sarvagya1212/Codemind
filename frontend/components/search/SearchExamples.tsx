'use client';

import React from 'react';
import { Sparkles } from 'lucide-react';

interface SearchExamplesProps {
  onExampleClick: (query: string) => void;
}

export default function SearchExamples({ onExampleClick }: SearchExamplesProps) {
  const examples = [
    {
      category: 'Semantic (Conceptual)',
      items: [
        'how does authentication work',
        'database connection logic',
        'error handling patterns',
        'API endpoint definitions',
      ],
    },
    {
      category: 'Symbol (Functions/Classes)',
      items: [
        'getUserById',
        'UserManager',
        'handleLogin',
        'validateEmail',
      ],
    },
    {
      category: 'Keyword (Exact Match)',
      items: [
        'TODO',
        'FIXME',
        'deprecated',
        'import React',
      ],
    },
  ];

  return (
    <div className="bg-slate-800/30 border border-slate-700 rounded-lg p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-yellow-400" />
        <h3 className="font-semibold">Try These Example Searches</h3>
      </div>

      <div className="space-y-4">
        {examples.map((category) => (
          <div key={category.category}>
            <p className="text-sm text-gray-400 mb-2">{category.category}:</p>
            <div className="flex flex-wrap gap-2">
              {category.items.map((query) => (
                <button
                  key={query}
                  onClick={() => onExampleClick(query)}
                  className="text-sm bg-slate-700 hover:bg-purple-600 px-3 py-2 rounded-lg transition-colors hover:scale-105"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}