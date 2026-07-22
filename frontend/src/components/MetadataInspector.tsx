'use client'

import React from 'react'
import { ShieldCheck, Tag, Lock, AlertTriangle, Layers } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export const MetadataInspector: React.FC = () => {
  const { targetName, targetUrn, piiColumns } = useWorkspaceStore()

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder mb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-accent" />
          <h2 className="font-semibold text-sm tracking-wide text-gray-200">DATAHUB ASPECT INSPECTOR</h2>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">Aspect Store Verified</span>
      </div>

      <div className="flex-1 bg-background border border-surfaceBorder rounded-lg p-3 overflow-y-auto space-y-3 font-mono text-xs">
        {targetUrn ? (
          <>
            <div>
              <div className="text-gray-400 text-[10px]">DATASET URN</div>
              <div className="text-gray-200 font-bold truncate text-[11px]">{targetUrn}</div>
            </div>

            <div className="flex gap-2">
              <div className="flex-1 bg-surface border border-surfaceBorder p-2 rounded">
                <div className="text-gray-400 text-[10px] flex items-center gap-1">
                  <Tag className="w-3 h-3 text-accent" /> TIER
                </div>
                <div className="text-accent font-bold mt-0.5">Tier-1 Production</div>
              </div>
              <div className="flex-1 bg-surface border border-surfaceBorder p-2 rounded">
                <div className="text-gray-400 text-[10px] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-emerald-400" /> DEPRECATION
                </div>
                <div className="text-emerald-400 font-bold mt-0.5">Active (Not Deprecated)</div>
              </div>
            </div>

            <div className="bg-surface border border-surfaceBorder p-2.5 rounded">
              <div className="text-gray-400 text-[10px] flex items-center gap-1 mb-1">
                <Lock className="w-3 h-3 text-warning" /> GOVERNANCE & PII TAGS
              </div>
              {piiColumns.length > 0 ? (
                <div className="flex gap-1 flex-wrap">
                  {piiColumns.map((col, idx) => (
                    <span key={idx} className="bg-warning/20 text-warning px-2 py-0.5 rounded text-[10px]">
                      PII: {col} (Masked)
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-gray-400 text-[10px]">No PII detected.</span>
              )}
            </div>

            <div className="bg-surface border border-surfaceBorder p-2.5 rounded">
              <div className="text-gray-400 text-[10px] flex items-center gap-1 mb-1">
                <ShieldCheck className="w-3 h-3 text-accent" /> OWNERSHIP & GLOSSARY
              </div>
              <div className="text-gray-300 text-[11px]">Owner: Data Platform Core Team</div>
              <div className="text-gray-400 text-[10px] mt-0.5">Term: Financials.Revenue_Metrics</div>
            </div>
          </>
        ) : (
          <div className="text-center text-gray-500 text-xs italic py-8">
            Select or execute a prompt to view DataHub aspect metadata...
          </div>
        )}
      </div>
    </div>
  )
}
