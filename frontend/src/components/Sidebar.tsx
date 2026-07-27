'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Settings, Activity, Database, ChevronLeft, ChevronRight } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL } from '../lib/api'

export const Sidebar: React.FC = () => {
  const pathname = usePathname()
  const [isCollapsed, setIsCollapsed] = useState(false)

  const navItems = [
    { name: 'Workspace', path: '/', icon: <LayoutDashboard className="w-4 h-4 shrink-0" /> },
    { name: 'Run History', path: '/history', icon: <Activity className="w-4 h-4 shrink-0" /> },
    { name: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4 shrink-0" /> },
  ]

  return (
    <aside className={`${isCollapsed ? 'w-16' : 'w-64'} border-r border-surfaceBorder bg-[#04060C] flex flex-col h-full shrink-0 transition-[width] duration-300 ease-in-out relative z-20 overflow-hidden isolate shadow-2xl`}>
      {/* Brand Header */}
      <div className={`h-16 flex items-center border-b border-surfaceBorder mb-6 px-3 ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
        {!isCollapsed && (
          <div className="flex items-center min-w-0">
            <div className="w-7 h-7 bg-accent/20 border border-accent rounded shadow-[0_0_10px_rgba(0,229,255,0.2)] flex items-center justify-center shrink-0">
              <Database className="w-4 h-4 text-accent" />
            </div>
            <div className="flex items-center ml-3 truncate">
              <span className="font-bold text-lg text-white tracking-wide truncate">Synex</span>
            </div>
          </div>
        )}

        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded hover:bg-surface text-gray-400 hover:text-white transition shrink-0"
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Menu & Recent Sessions */}
      <nav className="flex-1 px-2 space-y-4 overflow-y-auto custom-scrollbar">
        <div>
          {!isCollapsed && (
            <div className="text-[10px] font-bold tracking-wider text-gray-500 mb-2 px-2 uppercase truncate">Core Engine</div>
          )}
          {navItems.map((item) => {
            const isActive = pathname === item.path
            return (
              <Link key={item.path} href={item.path}>
                <div 
                  title={isCollapsed ? item.name : undefined}
                  className={`flex items-center ${isCollapsed ? 'justify-center py-3 px-0' : 'gap-3 px-3 py-2.5'} rounded-lg text-sm transition-all duration-200 cursor-pointer ${
                    isActive 
                      ? 'bg-primary/15 text-primary font-medium shadow-[inset_2px_0_0_0_#6366F1]' 
                      : 'text-gray-400 hover:bg-surface hover:text-gray-200'
                  }`}
                >
                  {item.icon}
                  {!isCollapsed && <span className="truncate">{item.name}</span>}
                </div>
              </Link>
            )
          })}
        </div>

        {/* New Session Button & Recent Sessions Drawer */}
        {!isCollapsed && (
          <div className="pt-4 border-t border-surfaceBorder/40">
            <button 
              onClick={() => {
                useWorkspaceStore.getState().clearHistory()
                window.location.href = '/'
              }}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-primary hover:bg-primaryHover text-white font-semibold text-xs transition-all shadow-md mb-4"
            >
              <span>+ New Session</span>
            </button>

            <div className="text-[10px] font-bold tracking-wider text-gray-500 mb-2 px-2 uppercase truncate">Recent Sessions</div>
            <RecentSessionsList />
          </div>
        )}
      </nav>

      {/* Bottom Status */}
      <div className="p-3 border-t border-surfaceBorder shrink-0">
        <div className="bg-surface/80 border border-surfaceBorder rounded-xl p-3.5 flex flex-col gap-2.5 shadow-inner">
          <div className="flex items-center justify-between min-h-[18px]">
            {!isCollapsed && <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">GMS STATUS</span>}
            <div className={`flex items-center gap-1.5 ${isCollapsed ? 'mx-auto' : ''}`}>
              <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-[0_0_8px_rgba(5,242,155,0.6)]" title="GMS Healthy" />
              {!isCollapsed && <span className="text-[10px] font-sans font-semibold text-gray-300">Live</span>}
            </div>
          </div>

          <div className="flex items-center justify-between min-h-[18px]">
            {!isCollapsed && <span className="text-[10px] text-gray-400 font-mono tracking-widest uppercase">SANDBOX</span>}
            <div className={`flex items-center gap-1.5 ${isCollapsed ? 'mx-auto' : ''}`}>
              <div className="w-2 h-2 rounded-full bg-accent shadow-[0_0_8px_rgba(0,229,255,0.6)]" title="Sandbox Ready" />
              {!isCollapsed && <span className="text-[10px] font-sans font-semibold text-gray-300">Ready</span>}
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}

const RecentSessionsList: React.FC = () => {
  const [sessions, setSessions] = React.useState<any[]>([])

  React.useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/history`)
      .then(res => res.json())
      .then(data => {
        if (data.runs) setSessions(data.runs.slice(0, 6))
      })
      .catch(() => {})
  }, [])

  if (sessions.length === 0) {
    return <div className="text-xs text-gray-500 italic px-2">No past sessions</div>
  }

  return (
    <div className="space-y-1">
      {sessions.map((s) => (
        <div 
          key={s.id}
          onClick={() => {
            // Load session into workspace store
            const store = useWorkspaceStore.getState()
            store.clearHistory()
            store.addMessage({
              id: 'user-' + s.id,
              sender: 'user',
              text: s.prompt,
              timestamp: 'Saved Run'
            })
            store.addMessage({
              id: 'agent-' + s.id,
              sender: 'agent',
              text: `Restored session from Supabase history for target model ${s.target_name || s.target_urn || ''}`,
              timestamp: 'Saved Run',
              status: 'SUCCESS',
              result: {
                target_urn: s.target_urn || '',
                target_name: s.target_name || '',
                dataset_description: '',
                pii_columns: s.pii_columns || [],
                schema_fields: s.schema_fields || [],
                sql: s.sql || '',
                dbt_yaml: s.dbt_yaml || ''
              }
            })
            if (s.target_urn) {
              store.setSelectedMetadata(
                s.target_urn,
                s.pii_columns || [],
                s.schema_fields || [],
                s.target_name || '',
                ''
              )
            }
          }}
          className="px-2.5 py-1.5 rounded text-xs text-gray-400 hover:text-white hover:bg-surfaceBorder/40 transition cursor-pointer truncate flex items-center gap-2 font-sans"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
          <span className="truncate">{s.prompt}</span>
        </div>
      ))}
    </div>
  )
}
