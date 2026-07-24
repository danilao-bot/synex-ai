'use client'

import React from 'react'
import { Database, Settings2, Copy, Loader2 } from 'lucide-react'
import Editor from '@monaco-editor/react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export const CodeSandbox: React.FC = () => {
  const { isComplete, executionResult } = useWorkspaceStore()

  const code = isComplete && executionResult 
    ? executionResult.sql 
    : `-- Waiting for Synex to generate code...
-- Execute a command above to see the results.
`

  return (
    <div className="w-full h-full bg-[#0A0E17] border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden relative z-0 isolate">
      {/* Tabs */}
      <div className="flex items-center justify-between bg-surface border-b border-surfaceBorder px-4 shrink-0 h-10">
        <div className="flex h-full">
          <div className="flex items-center gap-2 border-b-2 border-accent text-accent px-4 h-full bg-[#0A0E17]">
            <Database className="w-3.5 h-3.5" />
            <span className="text-xs font-bold tracking-wider">model.sql</span>
          </div>
          <div className="flex items-center gap-2 text-gray-500 px-4 h-full hover:text-gray-300 cursor-pointer transition">
            <Settings2 className="w-3.5 h-3.5" />
            <span className="text-xs font-bold tracking-wider">schema.yml</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-gray-500">
          <Copy className="w-3.5 h-3.5 hover:text-white cursor-pointer transition" />
        </div>
      </div>

      {/* Monaco Editor Content */}
      <div className="flex-1 overflow-hidden bg-[#0A0E17]">
        <Editor
          height="100%"
          defaultLanguage="sql"
          theme="vs-dark"
          value={code}
          loading={
            <div className="flex items-center justify-center h-full text-accent flex-col gap-2">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span className="text-xs font-mono">Loading Editor...</span>
            </div>
          }
          options={{
            minimap: { enabled: false },
            fontSize: 12,
            fontFamily: "'JetBrains Mono', 'Courier New', monospace",
            lineHeight: 24,
            padding: { top: 16 },
            readOnly: false,
            scrollBeyondLastLine: false,
            matchBrackets: "always",
            renderLineHighlight: "all",
            smoothScrolling: true,
            cursorBlinking: "smooth",
          }}
        />
      </div>
    </div>
  )
}
