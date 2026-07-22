'use client'

import React, { useState } from 'react'
import { Code2, FileCode, Copy, Check } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export const CodeSandbox: React.FC = () => {
  const { generatedSql, generatedDbtYaml } = useWorkspaceStore()
  const [activeTab, setActiveTab] = useState<'sql' | 'yaml'>('sql')
  const [copied, setCopied] = useState(false)

  const content = activeTab === 'sql' ? generatedSql : generatedDbtYaml

  const handleCopy = () => {
    if (!content) return
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder mb-3">
        <div className="flex items-center gap-2">
          <Code2 className="w-5 h-5 text-accent" />
          <h2 className="font-semibold text-sm tracking-wide text-gray-200">SYNTHESIZED CODE & DATA CONTRACT</h2>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex bg-background border border-surfaceBorder rounded p-0.5 text-xs">
            <button
              onClick={() => setActiveTab('sql')}
              className={`px-2.5 py-1 rounded transition ${activeTab === 'sql' ? 'bg-accent text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              SQL Model
            </button>
            <button
              onClick={() => setActiveTab('yaml')}
              className={`px-2.5 py-1 rounded transition ${activeTab === 'yaml' ? 'bg-accent text-white font-medium' : 'text-gray-400 hover:text-gray-200'}`}
            >
              dbt schema.yml
            </button>
          </div>

          <button
            onClick={handleCopy}
            disabled={!content}
            className="p-1.5 rounded bg-surface border border-surfaceBorder hover:bg-surfaceBorder text-gray-300 disabled:opacity-40 transition"
            title="Copy code"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="flex-1 bg-background border border-surfaceBorder rounded-lg p-3 font-mono text-xs overflow-auto text-gray-200">
        {content ? (
          <pre className="whitespace-pre-wrap leading-relaxed">{content}</pre>
        ) : (
          <div className="text-center text-gray-500 italic py-12">
            Synthesized SQL and dbt contracts will appear here after agent execution...
          </div>
        )}
      </div>
    </div>
  )
}
