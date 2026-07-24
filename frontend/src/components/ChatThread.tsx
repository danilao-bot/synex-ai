'use client'

import React, { useEffect, useRef, useState } from 'react'
import { Terminal, Database, GitBranch, TerminalSquare, AlertTriangle, Play, ChevronDown, ChevronUp } from 'lucide-react'
import { useWorkspaceStore, ChatMessage } from '../store/useWorkspaceStore'
import { LineageGraph } from './LineageGraph'
import { CodeSandbox } from './CodeSandbox'

export const ChatThread: React.FC = () => {
  const { messages } = useWorkspaceStore()
  const threadEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 custom-scrollbar">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center pt-24 pb-12 animate-fadeIn text-center">
            <div className="w-16 h-16 rounded-2xl bg-surface border border-surfaceBorder flex items-center justify-center mb-6 shadow-xl relative">
              {/* Bespoke Agent Motif: Lineage Thread */}
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-primary">
                <circle cx="18" cy="6" r="3" fill="currentColor"/>
                <circle cx="6" cy="18" r="3" fill="currentColor"/>
                <circle cx="12" cy="12" r="3" fill="currentColor"/>
                <path d="M16.5 7.5L13.5 10.5M10.5 13.5L7.5 16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              {/* Glowing backplate effect */}
              <div className="absolute inset-0 bg-primary opacity-20 blur-xl rounded-full"></div>
            </div>
            <h2 className="text-2xl font-display font-semibold text-white mb-2">How can Synex help you today?</h2>
            <p className="text-gray-400 font-sans mb-10 max-w-md">I am your metadata-aware data engineering agent. I can build models, trace lineage, and analyze dataset aspects.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-3xl">
              {[
                { title: "Model a dataset", desc: "Generate a new dbt model" },
                { title: "Trace lineage", desc: "For core.fct_orders" },
                { title: "Audit aspect", desc: "Check quality on users_table" }
              ].map((action, i) => (
                <button key={i} className="flex flex-col items-start p-4 rounded-xl bg-surface border border-surfaceBorder hover:border-primary/50 hover:bg-surfaceBorder/30 transition-all text-left group">
                  <span className="text-sm font-semibold text-white group-hover:text-primary transition-colors">{action.title}</span>
                  <span className="text-xs text-gray-500 mt-1">{action.desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={msg.id} className="animate-fadeIn">
            {msg.sender === 'user' ? (
              /* User Chat Bubble */
              <div className="flex justify-end">
                <div className="max-w-2xl bg-surface border border-surfaceBorder rounded-2xl rounded-tr-none px-5 py-3 text-[15px] text-gray-100 font-sans shadow-md border-r-4 border-r-primary">
                  {msg.text}
                </div>
              </div>
            ) : (
              /* Agent Chat Block */
              <div className="flex gap-4 items-start">
                {/* Agent Icon (Bespoke Motif) */}
                <div className="w-8 h-8 rounded-lg bg-surface border border-surfaceBorder flex items-center justify-center shrink-0 shadow-lg relative">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-primary relative z-10">
                    <circle cx="18" cy="6" r="3" fill="currentColor"/>
                    <circle cx="6" cy="18" r="3" fill="currentColor"/>
                    <circle cx="12" cy="12" r="3" fill="currentColor"/>
                    <path d="M16.5 7.5L13.5 10.5M10.5 13.5L7.5 16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                  <div className="absolute inset-0 bg-primary opacity-20 blur-md rounded-full"></div>
                </div>
                
                {/* Agent Content */}
                <div className="flex-1 space-y-4">
                  <div className="text-[15px] text-gray-300 leading-relaxed font-sans">
                    {msg.text}
                  </div>

                  {/* Render Logs (Trace Logs) */}
                  {msg.steps && msg.steps.length > 0 && (
                    <CollapsibleCard title="System Trace Log" icon={<Terminal className="w-3.5 h-3.5" />} defaultExpanded={msg.status === 'RUNNING'}>
                      <div className="font-mono text-[11px] leading-relaxed space-y-1 text-gray-400">
                        {msg.steps.map((s, i) => {
                          let colorClass = "text-accent"
                          if (s.message.includes('SUCCESS')) colorClass = "text-success"
                          if (s.message.includes('WARN')) colorClass = "text-warning"
                          if (s.message.includes('ERROR')) colorClass = "text-danger"
                          return (
                            <div key={i}>
                              <span className={colorClass}>{s.message.split(': ')[0]}:</span> {s.message.split(': ').slice(1).join(': ')}
                            </div>
                          )
                        })}
                      </div>
                    </CollapsibleCard>
                  )}

                  {/* Render Lineage & Code (If result generated) */}
                  {msg.result && (
                    <div className="space-y-4">
                      {/* Collapsible Lineage */}
                      <CollapsibleCard 
                        title={`Resolved Lineage Map (${msg.result.target_name || 'Graph'})`} 
                        icon={<GitBranch className="w-3.5 h-3.5" />} 
                        defaultExpanded={idx === messages.length - 1}
                      >
                        <div className="h-64 rounded-lg overflow-hidden border border-surfaceBorder bg-background/50">
                          <LineageGraph />
                        </div>
                      </CollapsibleCard>

                      {/* Code Output Editor */}
                      <CollapsibleCard 
                        title={`Synthesized dbt Model & Contract (${msg.result.target_name || 'Code'})`} 
                        icon={<TerminalSquare className="w-3.5 h-3.5" />} 
                        defaultExpanded={idx === messages.length - 1}
                      >
                        <div className="h-[350px] border border-surfaceBorder rounded-xl overflow-hidden shadow-lg">
                          <CodeSandbox />
                        </div>
                      </CollapsibleCard>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={threadEndRef} />
      </div>
    </div>
  )
}

/* Collapsible Card Component */
interface CollapsibleProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultExpanded?: boolean
}

const CollapsibleCard: React.FC<CollapsibleProps> = ({ title, icon, children, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="bg-[#050811] border border-surfaceBorder/60 rounded-xl overflow-hidden shadow-md flex flex-col">
      <div 
        onClick={() => setExpanded(!expanded)}
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-surfaceBorder/20 transition-all duration-200"
      >
        <div className="flex items-center gap-2 text-xs font-bold text-gray-300 uppercase tracking-widest">
          {icon}
          {title}
        </div>
        <div className="text-gray-500">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>
      {expanded && (
        <div className="p-4 border-t border-surfaceBorder/30">
          {children}
        </div>
      )}
    </div>
  )
}
