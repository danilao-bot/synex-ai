'use client'

import React, { useState } from 'react'
import {
  TerminalSquare, GitBranch, ShieldCheck, Check, XCircle, CheckCircle2,
  Award, Users, Tag, Database, AlertTriangle, ChevronDown, ChevronUp,
  Clock
} from 'lucide-react'
import { useWorkspaceStore, SchemaField } from '../store/useWorkspaceStore'
import { LineageGraph } from './LineageGraph'
import { CodeSandbox } from './CodeSandbox'

/* ─────────────────────────────────────────────────────────────────────────── */
/*  MetadataInspector  — right panel: shows RESULTS when workflow completes   */
/* ─────────────────────────────────────────────────────────────────────────── */
export const MetadataInspector: React.FC = () => {
  const {
    selectedUrn,
    selectedPiiColumns,
    selectedSchemaFields,
    selectedDatasetName,
    selectedCandidate,
    messages,
  } = useWorkspaceStore()

  const lastAgent = [...messages].reverse().find(m => m.sender === 'agent' && m.result)
  const hasResult = !!(lastAgent?.result?.sql && lastAgent.result.sql !== '-- No SQL generated')
  const validation = lastAgent?.result?.validation
  const metadataSource = (lastAgent?.result as any)?.metadata_source

  /* ── No result yet ──────────────────────────────────────────────────── */
  if (!selectedUrn && !hasResult) {
    return (
      <div className="h-full flex flex-col justify-center items-center text-center px-5 py-8">
        <div className="w-16 h-16 mb-5 opacity-20">
          <svg viewBox="0 0 100 100" fill="none" className="w-full h-full text-gray-400">
            <rect x="10" y="10" width="80" height="80" rx="8" stroke="currentColor" strokeWidth="3" strokeDasharray="6 6"/>
            <rect x="20" y="30" width="60" height="8" rx="4" fill="currentColor"/>
            <rect x="20" y="50" width="40" height="8" rx="4" fill="currentColor"/>
            <rect x="20" y="70" width="50" height="8" rx="4" fill="currentColor"/>
          </svg>
        </div>
        <p className="text-gray-500 text-sm font-sans leading-relaxed max-w-[200px]">
          Run a prompt — the generated model, lineage, and approval will appear here.
        </p>
      </div>
    )
  }

  const trustScore = selectedCandidate?.trust_score
  const hasTrust   = typeof trustScore === 'number'
  const scoreColor =
    !hasTrust          ? 'text-gray-400 border-surfaceBorder bg-surface' :
    trustScore >= 80   ? 'text-success  border-success/40  bg-success/10' :
    trustScore >= 50   ? 'text-warning  border-warning/40  bg-warning/10' :
                         'text-danger   border-danger/40   bg-danger/10'

  return (
    <div className="h-full flex flex-col gap-4 text-xs overflow-y-auto custom-scrollbar pb-6">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="shrink-0 pt-1">
        <h2 className="text-sm font-display font-semibold text-white tracking-tight">Result Inspector</h2>
        <p className="text-[11px] text-gray-500 mt-0.5">
          {selectedDatasetName ? `Dataset: ${selectedDatasetName}` : 'Model results'}
          {metadataSource && <span className="ml-1 text-accent/70">via {metadataSource}</span>}
        </p>
      </div>

      {/* ── Trust score strip ──────────────────────────────────────────── */}
      {hasTrust && (
        <div className="shrink-0 flex items-center justify-between bg-[#060d1a] border border-surfaceBorder rounded-xl px-3.5 py-2.5">
          <div className="flex items-center gap-2 text-gray-300">
            <Award className="w-3.5 h-3.5 text-accent" />
            <span className="font-semibold">Trust Score</span>
          </div>
          <div className="flex items-center gap-2">
            {selectedCandidate?.is_certified && (
              <span className="flex items-center gap-0.5 text-success text-[10px] font-bold">
                <CheckCircle2 className="w-3 h-3" /> Certified
              </span>
            )}
            {selectedCandidate?.is_deprecated && (
              <span className="flex items-center gap-0.5 text-danger text-[10px] font-bold">
                <XCircle className="w-3 h-3" /> Deprecated
              </span>
            )}
            <span className={`px-2.5 py-0.5 rounded-full border font-mono font-bold text-xs ${scoreColor}`}>
              {trustScore}/100
            </span>
          </div>
        </div>
      )}

      {/* ── Validation result ──────────────────────────────────────────── */}
      {validation && (
        <Section
          title="Governance Validation"
          icon={<ShieldCheck className="w-3.5 h-3.5 text-primary" />}
          defaultOpen
        >
          <div className={`flex items-center gap-2 text-[11px] font-bold mb-2 ${validation.passed ? 'text-success' : 'text-danger'}`}>
            {validation.passed
              ? <><Check className="w-3.5 h-3.5" /> All checks passed</>
              : <><AlertTriangle className="w-3.5 h-3.5" /> {validation.blocking_errors?.length || 0} blocking error(s)</>
            }
          </div>
          {(validation.blocking_errors || []).map((e: string, i: number) => (
            <p key={i} className="text-[10px] text-danger/80 bg-danger/5 border border-danger/20 rounded p-2 mb-1 leading-relaxed">{e}</p>
          ))}
          {(validation.warnings || []).slice(0, 3).map((w: string, i: number) => (
            <p key={i} className="text-[10px] text-warning/80 bg-warning/5 border border-warning/20 rounded p-2 mb-1 leading-relaxed">{w}</p>
          ))}
        </Section>
      )}

      {/* ── PII columns ────────────────────────────────────────────────── */}
      {selectedPiiColumns.length > 0 && (
        <Section title="PII Columns (SHA2 hashed)" icon={<ShieldCheck className="w-3.5 h-3.5 text-warning" />}>
          <div className="flex flex-wrap gap-1.5">
            {selectedPiiColumns.map(col => (
              <span key={col} className="bg-warning/10 border border-warning/30 text-warning text-[10px] px-2 py-0.5 rounded font-mono">
                {col}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ── Schema fields ──────────────────────────────────────────────── */}
      {selectedSchemaFields.length > 0 && (
        <Section title={`Schema · ${selectedSchemaFields.length} fields`} icon={<Database className="w-3.5 h-3.5 text-accent" />}>
          <div className="space-y-1">
            {selectedSchemaFields.map((f: SchemaField) => {
              const isPii = selectedPiiColumns.includes(f.fieldPath)
              return (
                <div key={f.fieldPath} className={`flex items-center gap-2 px-2 py-1.5 rounded ${isPii ? 'bg-warning/5 border border-warning/20' : 'bg-[#04060C]'}`}>
                  <span className="font-mono text-[10px] text-gray-200 flex-1 truncate">{f.fieldPath}</span>
                  <span className="font-mono text-[9px] text-gray-600">{f.nativeDataType}</span>
                  {isPii && <span className="text-[9px] text-warning font-bold">PII</span>}
                </div>
              )
            })}
          </div>
        </Section>
      )}

      {/* ── Lineage graph ──────────────────────────────────────────────── */}
      {hasResult && (
        <Section title="Lineage Impact" icon={<GitBranch className="w-3.5 h-3.5 text-accent" />} defaultOpen>
          <div className="h-52 rounded-lg overflow-hidden border border-surfaceBorder bg-background/50">
            <LineageGraph />
          </div>
        </Section>
      )}

      {/* ── dbt Model + Contract ───────────────────────────────────────── */}
      {hasResult && (
        <Section
          title={`dbt Model · ${lastAgent?.result?.target_name || 'generated'}`}
          icon={<TerminalSquare className="w-3.5 h-3.5 text-primary" />}
          defaultOpen
        >
          <div className="h-[360px] border border-surfaceBorder rounded-xl overflow-hidden">
            <CodeSandbox />
          </div>
        </Section>
      )}

    </div>
  )
}

/* ── Reusable collapsible section ────────────────────────────────────────── */
const Section: React.FC<{
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}> = ({ title, icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-surfaceBorder/50 rounded-xl overflow-hidden bg-[#060d1a] shrink-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-[11px] font-bold text-gray-300 uppercase tracking-wider">{title}</span>
        </div>
        {open
          ? <ChevronUp className="w-3.5 h-3.5 text-gray-600" />
          : <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
        }
      </button>
      {open && (
        <div className="px-3.5 pb-3.5 border-t border-surfaceBorder/30 pt-3">
          {children}
        </div>
      )}
    </div>
  )
}
