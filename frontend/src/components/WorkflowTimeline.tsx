'use client'

import React from 'react'
import { Check, Circle, Loader2, AlertTriangle, Clock } from 'lucide-react'

export interface WorkflowStepView {
  id?: string
  name?: string
  label?: string
  stage?: string
  stage_label?: string
  status?: string
  message?: string
  duration_ms?: number | null
  reasoning_summary?: string
  trust_score?: number | null
  warnings?: string[]
  errors?: string[]
  logs?: string[]
}

interface Props {
  steps: WorkflowStepView[]
  running?: boolean
}

const STATUS_ICON = (status?: string) => {
  const s = (status || '').toLowerCase()
  if (s === 'completed') return <Check className="w-3.5 h-3.5 text-success" />
  if (s === 'running') return <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
  if (s === 'waiting') return <Clock className="w-3.5 h-3.5 text-warning" />
  if (s === 'failed') return <AlertTriangle className="w-3.5 h-3.5 text-danger" />
  return <Circle className="w-3.5 h-3.5 text-gray-600" />
}

export const WorkflowTimeline: React.FC<Props> = ({ steps, running }) => {
  if (!steps.length) {
    return (
      <div className="text-xs text-gray-500 font-sans px-1 py-2">
        {running ? 'Starting workflow engine…' : 'No workflow steps yet.'}
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {steps.map((s, i) => {
        const label = s.label || s.stage_label || s.name || s.stage || s.id || `Step ${i + 1}`
        const status = (s.status || 'pending').toLowerCase()
        const border =
          status === 'failed' ? 'border-danger/40' :
          status === 'running' ? 'border-primary/40' :
          status === 'waiting' ? 'border-warning/40' :
          'border-surfaceBorder'

        return (
          <div key={`${label}-${i}`} className={`relative pl-7 pb-3 last:pb-0`}>
            {i < steps.length - 1 && (
              <div className="absolute left-[11px] top-5 bottom-0 w-px bg-surfaceBorder" />
            )}
            <div className="absolute left-0 top-1 w-[22px] h-[22px] rounded-full bg-[#050811] border border-surfaceBorder flex items-center justify-center">
              {STATUS_ICON(status)}
            </div>
            <div className={`rounded-lg border ${border} bg-[#050811]/50 px-3 py-2`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] font-semibold text-gray-200 font-sans">{label}</span>
                <span className="text-[10px] font-mono text-gray-500 uppercase">
                  {(s as any).time ? `${(s as any).time} · ` : ''}{status}
                  {typeof s.duration_ms === 'number' ? ` · ${s.duration_ms}ms` : ''}
                </span>
              </div>
              {s.message && (
                <p className="text-[11px] text-gray-400 mt-1 font-sans leading-relaxed">{s.message}</p>
              )}
              {typeof s.trust_score === 'number' && (
                <p className="text-[10px] font-mono text-accent mt-1">Trust {s.trust_score}/100</p>
              )}
              {s.reasoning_summary && (
                <p className="text-[10px] text-gray-500 mt-1 italic">{s.reasoning_summary}</p>
              )}
              {s.warnings && s.warnings.length > 0 && (
                <p className="text-[10px] text-warning mt-1">{s.warnings[0]}</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
