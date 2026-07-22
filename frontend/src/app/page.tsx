'use client'

import React from 'react'
import { Sparkles, Database, CheckCircle, RefreshCw } from 'lucide-react'
import { PromptConsole } from '../components/PromptConsole'
import { LineageGraph } from '../components/LineageGraph'
import { MetadataInspector } from '../components/MetadataInspector'
import { CodeSandbox } from '../components/CodeSandbox'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export default function WorkspacePage() {
  const { resetWorkspace } = useWorkspaceStore()

  return (
    <div className="flex flex-col h-screen w-screen bg-background overflow-hidden">
      {/* Workspace Top Header Bar */}
      <header className="h-14 border-b border-surfaceBorder bg-surface/50 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-accent" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-2">
              SYNEX <span className="text-xs font-mono font-normal text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">DataHub Agent Hackathon</span>
            </h1>
            <p className="text-[11px] text-gray-400">Autonomous AI Data Engineering Agent Grounded in Metadata</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full">
            <CheckCircle className="w-3.5 h-3.5" />
            <span>DataHub GMS: Connected</span>
          </div>

          <button
            onClick={resetWorkspace}
            className="flex items-center gap-1.5 text-gray-400 hover:text-white bg-surface border border-surfaceBorder px-3 py-1 rounded-lg transition"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Reset
          </button>
        </div>
      </header>

      {/* Main 4-Pane Grid Layout */}
      <main className="flex-1 p-4 grid grid-cols-2 grid-rows-2 gap-4 overflow-hidden">
        {/* Pane 1: Prompt Console */}
        <div className="col-span-1 row-span-1 min-h-0">
          <PromptConsole />
        </div>

        {/* Pane 2: Lineage Graph Visualizer */}
        <div className="col-span-1 row-span-1 min-h-0">
          <LineageGraph />
        </div>

        {/* Pane 3: Aspect Inspector */}
        <div className="col-span-1 row-span-1 min-h-0">
          <MetadataInspector />
        </div>

        {/* Pane 4: Synthesized Code Sandbox */}
        <div className="col-span-1 row-span-1 min-h-0">
          <CodeSandbox />
        </div>
      </main>
    </div>
  )
}
