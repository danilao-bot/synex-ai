'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Sparkles, Activity, PanelRightClose, PanelRightOpen, RotateCcw, AlertCircle } from 'lucide-react'
import { PromptConsole } from '../components/PromptConsole'
import { ChatThread } from '../components/ChatThread'
import { MetadataInspector } from '../components/MetadataInspector'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL } from '../lib/api'

type HealthStatus = 'checking' | 'healthy' | 'degraded'

export default function WorkspacePage() {
  const [isRightCollapsed, setIsRightCollapsed] = useState(false)
  const [health, setHealth] = useState<HealthStatus>('checking')
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const { clearHistory } = useWorkspaceStore()

  const checkHealth = useCallback(async () => {
    const start = Date.now()
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { cache: 'no-store' })
      const ms = Date.now() - start
      setLatencyMs(ms)
      setHealth(res.ok ? 'healthy' : 'degraded')
    } catch {
      setHealth('degraded')
      setLatencyMs(null)
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30_000)
    return () => clearInterval(interval)
  }, [checkHealth])

  const statusConfig = {
    checking: {
      label: 'CONNECTING...',
      className: 'bg-gray-500/15 border border-gray-500/30 text-gray-400',
      icon: <Activity className="w-3.5 h-3.5 animate-pulse" />,
    },
    healthy: {
      label: 'SYSTEM HEALTHY',
      className: 'bg-success/15 border border-success/30 text-success shadow-[0_0_12px_rgba(5,242,155,0.2)]',
      icon: <Sparkles className="w-3.5 h-3.5 text-success" />,
    },
    degraded: {
      label: 'BACKEND OFFLINE',
      className: 'bg-danger/15 border border-danger/30 text-danger',
      icon: <AlertCircle className="w-3.5 h-3.5 text-danger" />,
    },
  }

  const cfg = statusConfig[health]

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-hidden relative">
      {/* Header */}
      <header className="flex items-center justify-between mb-6 shrink-0">
        <div>
          <h1 className="text-2xl font-display font-semibold text-white tracking-tight">Workspace Studio</h1>
          <p className="text-sm text-gray-400 mt-1 font-sans">Converse with Synex Agent to build metadata-first models.</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Live Backend Health Badge */}
          <div className={`font-sans font-bold text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 ${cfg.className}`}>
            {cfg.icon}
            <span>{cfg.label}</span>
          </div>

          {/* Real Latency */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-surfaceBorder bg-surface/50 text-xs text-gray-400 font-mono">
            <Activity className="w-3.5 h-3.5 text-accent" />
            <span>{latencyMs !== null ? `${latencyMs}ms` : '—'}</span>
          </div>

          <div className="w-px h-4 bg-surfaceBorder mx-1"></div>

          {/* Reset */}
          <button
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surfaceBorder bg-surface hover:bg-surfaceBorder text-xs text-gray-400 hover:text-white transition font-sans cursor-pointer"
            title="Reset Workspace"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>

          {/* Right Sidebar Toggle */}
          <button
            onClick={() => setIsRightCollapsed(!isRightCollapsed)}
            className="p-2 rounded-lg border border-surfaceBorder bg-surface hover:bg-surfaceBorder text-gray-400 hover:text-white transition cursor-pointer"
            title={isRightCollapsed ? 'Show Aspect Inspector' : 'Hide Aspect Inspector'}
          >
            {isRightCollapsed ? <PanelRightOpen className="w-4 h-4" /> : <PanelRightClose className="w-4 h-4" />}
          </button>
        </div>
      </header>

      {/* Main Flex Layout */}
      <div className="flex-1 flex flex-row min-h-0 overflow-hidden gap-6">

        {/* Center Chat Workspace Column */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#080C16] border border-surfaceBorder rounded-2xl overflow-hidden relative">
          <ChatThread />
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
