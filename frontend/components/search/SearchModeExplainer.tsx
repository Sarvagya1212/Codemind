'use client';

import React from 'react';
import { Zap, Search, Code, Layers, HelpCircle } from 'lucide-react';

export default function SearchModeExplainer() {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle className="w-5 h-5 text-purple-400" />
        <h3 className="font-semibold text-lg">Search Modes Explained</h3>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Semantic */}
        <div className="bg-slate-900/50 p-4 rounded-lg border border-purple-500/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-purple-500/20 rounded">
              <Zap className="w-5 h-5 text-purple-400" />
            </div>
            <h4 className="font-semibold">Semantic (AI)</h4>
          </div>
          <p className="text-sm text-gray-400 mb-3">
            Understands <strong>what you mean</strong>, not just keywords. Uses AI to find conceptually similar code.
          </p>
          <div className="bg-slate-800 p-3 rounded text-xs font-mono">
            <div className="text-green-400 mb-1">✓ Query: "auth logic"</div>
            <div className="text-gray-400">Finds: verifyUser(), checkToken(), validateSession()</div>
          </div>
        </div>

        {/* Keyword */}
        <div className="bg-slate-900/50 p-4 rounded-lg border border-blue-500/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-blue-500/20 rounded">
              <Search className="w-5 h-5 text-blue-400" />
            </div>
            <h4 className="font-semibold">Keyword</h4>
          </div>
          <p className="text-sm text-gray-400 mb-3">
            Finds <strong>exact word matches</strong> in code (like Ctrl+F). Fast for specific terms.
          </p>
          <div className="bg-slate-800 p-3 rounded text-xs font-mono">
            <div className="text-green-400 mb-1">✓ Query: "getUserById"</div>
            <div className="text-gray-400">Finds: only that exact function name</div>
          </div>
        </div>

        {/* Symbol */}
        <div className="bg-slate-900/50 p-4 rounded-lg border border-green-500/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-green-500/20 rounded">
              <Code className="w-5 h-5 text-green-400" />
            </div>
            <h4 className="font-semibold">Symbol</h4>
          </div>
          <p className="text-sm text-gray-400 mb-3">
            Searches <strong>function/class names only</strong>. Perfect for finding specific definitions.
          </p>
          <div className="bg-slate-800 p-3 rounded text-xs font-mono">
            <div className="text-green-400 mb-1">✓ Query: "User"</div>
            <div className="text-gray-400">Finds: UserClass, getUserData(), UserManager</div>
          </div>
        </div>

        {/* Hybrid */}
        <div className="bg-slate-900/50 p-4 rounded-lg border border-orange-500/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-orange-500/20 rounded">
              <Layers className="w-5 h-5 text-orange-400" />
            </div>
            <h4 className="font-semibold">Hybrid (Recommended)</h4>
          </div>
          <p className="text-sm text-gray-400 mb-3">
            <strong>Combines all methods</strong> for most comprehensive results. Best for exploratory search.
          </p>
          <div className="bg-slate-800 p-3 rounded text-xs font-mono">
            <div className="text-green-400 mb-1">✓ Query: "user authentication"</div>
            <div className="text-gray-400">Uses AI + keywords + symbols = complete coverage</div>
          </div>
        </div>
      </div>

      {/* Pro Tips */}
      <div className="mt-4 p-4 bg-purple-900/20 rounded-lg border border-purple-500/30">
        <div className="text-sm space-y-2">
          <p className="font-semibold text-purple-400">💡 Pro Tips:</p>
          <ul className="text-gray-400 space-y-1 ml-4 list-disc">
            <li>Use <strong>Semantic</strong> for "how does X work?" questions</li>
            <li>Use <strong>Symbol</strong> to find specific function/class definitions</li>
            <li>Use <strong>Keyword</strong> for exact string matches</li>
            <li>Use <strong>Hybrid</strong> when you're not sure (combines all!)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}