'use client'

import React, { useState } from 'react'
import { Sparkles, Activity, PanelRightClose, PanelRightOpen, RotateCcw } from 'lucide-react'
import { PromptConsole } from '../components/PromptConsole'
import { ChatThread } from '../components/ChatThread'
import { MetadataInspector } from '../components/MetadataInspector'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export default function WorkspacePage() {
  const [isRightCollapsed, setIsRightCollapsed] = useState(false)
  const { clearHistory } = useWorkspaceStore()

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between mb-6 shrink-0">
        <div>
          <h1 className="text-2xl font-display font-semibold text-white tracking-tight">Workspace Studio</h1>
          <p className="text-sm text-gray-400 mt-1 font-sans">Converse with Synex Agent to build metadata-first models.</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Primary Anchor: System Health */}
          <button className="bg-success text-black font-bold text-xs px-3 py-1.5 rounded flex items-center gap-2 shadow-[0_0_12px_rgba(5,242,155,0.25)] mr-4">
            <Sparkles className="w-3.5 h-3.5" /> SYSTEM HEALTHY
          </button>
          
          {/* Recessed Info: Latency */}
          <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 font-mono">
            <Activity className="w-3.5 h-3.5" />
            14ms
          </div>

          <div className="w-px h-4 bg-surfaceBorder mx-2"></div>

          {/* Recessed Action: Reset */}
          <button 
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded text-xs text-gray-500 hover:text-gray-300 hover:bg-surface transition"
            title="Reset Workspace"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
          
          {/* Recessed Action: Right Sidebar Toggle */}
          <button 
            onClick={() => setIsRightCollapsed(!isRightCollapsed)}
            className="p-1.5 rounded hover:bg-surface text-gray-500 hover:text-gray-300 transition ml-2"
            title={isRightCollapsed ? "Show Aspect Inspector" : "Hide Aspect Inspector"}
          >
            {isRightCollapsed ? <PanelRightOpen className="w-4 h-4" /> : <PanelRightClose className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Flex Layout */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden gap-6">
        
        {/* Center Chat Workspace Column */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#080C16] border border-surfaceBorder rounded-2xl overflow-hidden relative">
          {/* Chat message thread feed */}
          <ChatThread />

          {/* Floating bottom prompt console input */}
          <div className="p-4 border-t border-surfaceBorder/40 bg-surface/30 backdrop-blur-md shrink-0">
            <PromptConsole />
          </div>
        </div>

        {/* Right Sidebar: Aspect Inspector (Collapsible) */}
        {!isRightCollapsed && (
          <aside className="w-80 shrink-0 border-l border-surfaceBorder pl-6 h-full overflow-y-auto custom-scrollbar flex flex-col transition-all duration-300">
            <MetadataInspector />
          </aside>
        )}

      </div>
    </div>
  )
}
