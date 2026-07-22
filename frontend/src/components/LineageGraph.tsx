'use client'

import React from 'react'
import { GitFork, Database, ArrowRight } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export const LineageGraph: React.FC = () => {
  const { targetName, targetUrn } = useWorkspaceStore()

  return (
    <div className="bg-surface border border-surfaceBorder rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder mb-3">
        <div className="flex items-center gap-2">
          <GitFork className="w-5 h-5 text-accent" />
          <h2 className="font-semibold text-sm tracking-wide text-gray-200">DATAHUB METADATA LINEAGE GRAPH</h2>
        </div>
        <span className="text-xs text-gray-400">2-Hop Traversal</span>
      </div>

      <div className="flex-1 bg-background border border-surfaceBorder rounded-lg p-4 flex items-center justify-center relative overflow-hidden">
        {targetUrn ? (
          <div className="flex items-center gap-4 w-full justify-around">
            {/* Upstream Source Node */}
            <div className="bg-surface border border-surfaceBorder rounded-lg p-3 w-44 text-center shadow-md">
              <Database className="w-6 h-6 text-blue-400 mx-auto mb-1" />
              <div className="text-xs font-bold text-gray-200 truncate">raw.postgres.orders</div>
              <div className="text-[10px] text-gray-500 font-mono">Upstream Source</div>
            </div>

            <ArrowRight className="w-5 h-5 text-gray-500" />

            {/* Target Selected Node */}
            <div className="bg-blue-950/60 border border-accent rounded-lg p-3 w-48 text-center shadow-lg ring-1 ring-accent">
              <Database className="w-6 h-6 text-accent mx-auto mb-1" />
              <div className="text-xs font-bold text-blue-300 truncate">{targetName || 'analytics.prod.orders'}</div>
              <div className="text-[10px] text-accent font-mono">Tier-1 Verified Target</div>
            </div>

            <ArrowRight className="w-5 h-5 text-gray-500" />

            {/* Downstream Synthesized Node */}
            <div className="bg-surface border border-emerald-500/40 rounded-lg p-3 w-48 text-center shadow-md">
              <Database className="w-6 h-6 text-emerald-400 mx-auto mb-1" />
              <div className="text-xs font-bold text-emerald-300 truncate">monthly_customer_retention</div>
              <div className="text-[10px] text-emerald-400 font-mono">Synthesized dbt Model</div>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-500 text-xs italic">
            Run a prompt to visualize live DataHub upstream/downstream lineage...
          </div>
        )}
      </div>
    </div>
  )
}
