'use client'

import React, { useEffect, useRef } from 'react'
import {
  Check, Loader2, AlertTriangle, Clock, Circle,
  ChevronDown, ChevronUp, Shield, ArrowRight
} from 'lucide-react'
import { useWorkspaceStore, ChatMessage } from '../store/useWorkspaceStore'

export const ChatThread: React.FC = () => {
  const { messages } = useWorkspaceStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-5 py-6 custom-scrollbar">
      <div className="max-w-2xl mx-auto space-y-4">

        {/* ── Empty state ───────────────────────────────────────────────── */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center pt-24 text-center">
            <div className="w-12 h-12 rounded-2xl bg-surface border border-surfaceBorder flex items-center justify-center mb-4 relative">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-primary relative z-10">
                <circle cx="18" cy="6" r="3" fill="currentColor"/>
                <circle cx="6" cy="18" r="3" fill="currentColor"/>
                <circle cx="12" cy="12" r="3" fill="currentColor"/>
                <path d="M16.5 7.5L13.5 10.5M10.5 13.5L7.5 16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <div className="absolute inset-0 bg-primary opacity-15 blur-xl rounded-full"/>
            </div>
            <h2 className="text-lg font-display font-semibold text-white mb-1">Hello! I am Synex</h2>
            <p className="text-gray-500 text-sm font-sans max-w-xs leading-relaxed">
              Your DataHub Governed dbt Change Agent. Ask me to build a model, inspect trust scores, or trace lineage.
            </p>
          </div>
        )}

        {/* ── Messages ─────────────────────────────────────────────────── */}
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.sender === 'user' ? (
              <UserBubble text={msg.text} />
            ) : (
              <AgentBubble msg={msg} />
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}

/* ── User bubble ────────────────────────────────────────────────────────── */
const UserBubble: React.FC<{ text: string }> = ({ text }) => (
  <div className="flex justify-end">
    <div className="max-w-md bg-[#1a2340] border border-primary/20 rounded-2xl rounded-tr-sm px-4 py-2.5 text-[14px] text-gray-100 font-sans leading-relaxed shadow-sm">
      {text}
    </div>
  </div>
)

/* ── Agent bubble ────────────────────────────────────────────────────────── */
const AgentBubble: React.FC<{ msg: ChatMessage }> = ({ msg }) => {
  const isRunning = msg.status === 'RUNNING'
  const isFailed  = msg.status === 'FAILED'
  const steps     = msg.workflowSteps || []
  const hasResult = !!(msg.result?.sql && msg.result.sql !== '-- No SQL generated')

  return (
    <div className="flex gap-2.5 items-start">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-lg bg-[#0D1527] border border-surfaceBorder flex items-center justify-center shrink-0 mt-0.5 relative">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="text-primary relative z-10">
          <circle cx="18" cy="6" r="3" fill="currentColor"/>
          <circle cx="6" cy="18" r="3" fill="currentColor"/>
          <circle cx="12" cy="12" r="3" fill="currentColor"/>
          <path d="M16.5 7.5L13.5 10.5M10.5 13.5L7.5 16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </div>

      <div className="flex-1 space-y-2 min-w-0">
        {/* Text bubble */}
        <div className={`inline-block rounded-2xl rounded-tl-sm px-4 py-2.5 text-[14px] font-sans leading-relaxed max-w-md ${
          isFailed
            ? 'bg-danger/10 border border-danger/25 text-danger/90'
            : 'bg-[#0D1527] border border-surfaceBorder/80 text-gray-200'
        }`}>
          {isRunning && <Loader2 className="w-3 h-3 text-primary animate-spin inline mr-2 mb-0.5" />}
          {msg.text}
        </div>

        {/* Workflow timeline strip — only shows during/after run */}
        {(steps.length > 0 || isRunning) && (
          <WorkflowStrip steps={steps} running={isRunning} />
        )}

        {/* Completion CTA — points user to right panel */}
        {hasResult && !isRunning && (
          <div className="flex items-center gap-2 text-[12px] font-sans text-gray-400 pl-1">
            <ArrowRight className="w-3.5 h-3.5 text-accent shrink-0" />
            <span>Model ready — review code and approve in the <strong className="text-accent">panel →</strong></span>
          </div>
        )}

        {/* Clarifying questions */}
        {msg.clarifyingQuestions && msg.clarifyingQuestions.length > 0 && (
          <ul className="pl-1 space-y-1">
            {msg.clarifyingQuestions.map((q, i) => (
              <li key={i} className="text-[13px] text-gray-300 flex gap-2">
                <span className="text-accent shrink-0">{i + 1}.</span>
                {q}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/* ── Workflow strip ──────────────────────────────────────────────────────── */
const ICON = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s === 'completed') return <Check className="w-2.5 h-2.5 text-success" />
  if (s === 'running')   return <Loader2 className="w-2.5 h-2.5 text-primary animate-spin" />
  if (s === 'waiting')   return <Clock className="w-2.5 h-2.5 text-warning" />
  if (s === 'failed')    return <AlertTriangle className="w-2.5 h-2.5 text-danger" />
  return <Circle className="w-2.5 h-2.5 text-gray-700" />
}

const WorkflowStrip: React.FC<{ steps: any[]; running: boolean }> = ({ steps, running }) => {
  const [open, setOpen] = React.useState(running) // auto-open while running

  React.useEffect(() => {
    if (!running && open) {
      // auto-collapse 1s after completion
      const t = setTimeout(() => setOpen(false), 1200)
      return () => clearTimeout(t)
    }
  }, [running])

  const done  = steps.filter(s => s.status === 'completed').length
  const total = steps.length
  const failed = steps.filter(s => s.status === 'failed').length

  return (
    <div className="border border-surfaceBorder/50 rounded-xl overflow-hidden bg-[#060d1a] w-full max-w-md">
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          {running
            ? <Loader2 className="w-3 h-3 text-primary animate-spin" />
            : failed > 0
              ? <AlertTriangle className="w-3 h-3 text-danger" />
              : <Check className="w-3 h-3 text-success" />
          }
          <span className="text-[11px] font-mono text-gray-400">
            {running ? 'Running workflow…' : failed > 0 ? `Workflow — ${failed} failed` : 'Workflow complete'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {total > 0 && (
            <span className="text-[10px] font-mono text-gray-600">{done}/{total}</span>
          )}
          {open ? <ChevronUp className="w-3 h-3 text-gray-600" /> : <ChevronDown className="w-3 h-3 text-gray-600" />}
        </div>
      </button>

      {/* Steps */}
      {open && (
        <div className="px-3 pb-2.5 border-t border-surfaceBorder/30 space-y-0.5 pt-2">
          {steps.length === 0 && (
            <div className="flex items-center gap-2 text-[11px] text-gray-600 py-1">
              <Loader2 className="w-2.5 h-2.5 animate-spin" />
              Starting…
            </div>
          )}
          {steps.map((s, i) => {
            const label  = s.label || s.stage_label || s.name || s.stage || `Step ${i + 1}`
            const status = (s.status || '').toLowerCase()
            const isErr  = status === 'failed'

            return (
              <div key={i} className="flex items-start gap-2 py-1">
                <div className="mt-0.5 shrink-0">{ICON(status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-1.5">
                    <span className={`text-[11px] font-medium truncate ${isErr ? 'text-danger' : 'text-gray-300'}`}>
                      {label}
                    </span>
                    {typeof s.duration_ms === 'number' && (
                      <span className="text-[10px] font-mono text-gray-700 shrink-0">{s.duration_ms}ms</span>
                    )}
                  </div>
                  {s.message && (
                    <p className={`text-[10px] leading-relaxed mt-0.5 ${isErr ? 'text-danger/70' : 'text-gray-600'}`}>
                      {s.message.length > 100 ? s.message.slice(0, 100) + '…' : s.message}
                    </p>
                  )}
                  {typeof s.trust_score === 'number' && (
                    <span className="text-[10px] font-mono text-accent/80 flex items-center gap-1 mt-0.5">
                      <Shield className="w-2 h-2" /> Trust {s.trust_score}/100
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
