'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Settings, Activity, Database, ChevronLeft, ChevronRight } from 'lucide-react'

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

      {/* Navigation Menu */}
      <nav className="flex-1 px-2 space-y-2 overflow-y-auto custom-scrollbar">
        {!isCollapsed && (
          <div className="text-[10px] font-bold tracking-wider text-gray-500 mb-4 px-2 uppercase truncate">Core Engine</div>
        )}
        {navItems.map((item) => {
          const isActive = pathname === item.path
          return (
            <Link key={item.path} href={item.path}>
              <div 
                title={isCollapsed ? item.name : undefined}
                className={`flex items-center ${isCollapsed ? 'justify-center py-3 px-0' : 'gap-3 px-3 py-2.5'} rounded-lg text-sm transition-all duration-200 cursor-pointer ${
                  isActive 
                    ? 'bg-accent/15 text-accent font-medium shadow-[inset_2px_0_0_0_#00E5FF]' 
                    : 'text-gray-400 hover:bg-surface hover:text-gray-200'
                }`}
              >
                {item.icon}
                {!isCollapsed && <span className="truncate">{item.name}</span>}
              </div>
            </Link>
          )
        })}
      </nav>

      {/* Bottom Status */}
      <div className="p-2 border-t border-surfaceBorder shrink-0">
        <div className="bg-surface rounded p-2 flex flex-col gap-2">
          <div className="flex items-center justify-between min-h-[16px]">
            {!isCollapsed && <span className="text-[10px] text-gray-400 font-mono truncate">GMS STATUS</span>}
            <div className={`w-2 h-2 rounded-full bg-success animate-pulse shadow-[0_0_8px_rgba(5,242,155,0.6)] ${isCollapsed ? 'mx-auto' : ''}`} title="GMS Healthy"></div>
          </div>
          <div className="flex items-center justify-between min-h-[16px]">
            {!isCollapsed && <span className="text-[10px] text-gray-400 font-mono truncate">SANDBOX</span>}
            <div className={`w-2 h-2 rounded-full bg-accent shadow-[0_0_8px_rgba(0,229,255,0.6)] ${isCollapsed ? 'mx-auto' : ''}`} title="Sandbox Ready"></div>
          </div>
        </div>
      </div>
    </aside>
  )
}
