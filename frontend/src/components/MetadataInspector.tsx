'use client'

import React from 'react'
import { AlertTriangle, UserCircle2 } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

export const MetadataInspector: React.FC = () => {
  const { selectedUrn, selectedPiiColumns } = useWorkspaceStore()

  if (!selectedUrn) {
    return (
      <div className="h-full flex flex-col justify-center items-center text-center px-4 animate-fadeIn">
        <div className="w-24 h-24 mb-6 relative">
          {/* Wireframe Outline */}
          <svg viewBox="0 0 100 100" fill="none" className="w-full h-full text-surfaceBorder">
            <rect x="10" y="10" width="80" height="80" rx="8" stroke="currentColor" strokeWidth="3" strokeDasharray="6 6"/>
            <rect x="20" y="30" width="60" height="8" rx="4" fill="currentColor" opacity="0.5"/>
            <rect x="20" y="50" width="40" height="8" rx="4" fill="currentColor" opacity="0.5"/>
            <rect x="20" y="70" width="50" height="8" rx="4" fill="currentColor" opacity="0.5"/>
          </svg>
        </div>
        <h2 className="text-lg font-display font-semibold text-gray-400 mb-2">Aspect Inspector</h2>
        <p className="text-gray-500 text-sm font-sans max-w-[200px] leading-relaxed">
          Select a dataset node in the lineage graph to inspect its DataHub metadata.
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col gap-8 animate-fadeIn">
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2 tracking-tight">Aspect Inspector</h2>
        <div className="w-12 h-1 bg-primary"></div>
      </div>

      {/* Dataset URN */}
      <div>
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-2">Dataset URN</h3>
        <div className="bg-[#041A24] border border-accent/30 rounded p-3 text-accent font-mono text-xs break-all">
          {selectedUrn}
        </div>
      </div>

      {/* Ownership */}
      <div>
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-2">Ownership</h3>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold text-sm shadow-lg">
            DA
          </div>
          <div>
            <div className="text-sm font-bold text-gray-200">Data Analytics Team</div>
            <div className="text-xs text-gray-500">#analytics-eng</div>
          </div>
        </div>
      </div>

      {/* PII Warning */}
      {selectedPiiColumns && selectedPiiColumns.length > 0 && (
        <div className="bg-[#1A1400] border border-warning/50 rounded-lg p-4 shadow-[0_0_15px_rgba(255,159,0,0.1)]">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-warning" />
            <span className="text-xs font-bold text-warning tracking-widest uppercase">PII Detected</span>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed font-sans">
            Fields <span className="text-warning font-mono">{selectedPiiColumns.join(', ')}</span> have been flagged as Tier-1 PII.
          </p>
        </div>
      )}

      {/* Freshness & DQ */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface border border-surfaceBorder rounded p-3">
          <div className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-1">Freshness</div>
          <div className="text-success font-bold text-lg">12m ago</div>
        </div>
        <div className="bg-surface border border-surfaceBorder rounded p-3">
          <div className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-1">DQ Score</div>
          <div className="text-accent font-bold text-lg">98.2%</div>
        </div>
      </div>

      {/* Schema Preview */}
      <div>
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-3">Schema Preview</h3>
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs pb-2 border-b border-surfaceBorder/50">
            <span className="font-mono text-gray-300">order_id</span>
            <span className="bg-surface px-1.5 py-0.5 rounded text-gray-500 font-mono text-[10px]">INT64</span>
          </div>
          <div className="flex justify-between items-center text-xs pb-2 border-b border-surfaceBorder/50">
            <span className="font-mono text-gray-300">status</span>
            <span className="bg-surface px-1.5 py-0.5 rounded text-gray-500 font-mono text-[10px]">STRING</span>
          </div>
          <div className="flex justify-between items-center text-xs pb-2 border-b border-surfaceBorder/50">
            <span className="font-mono text-gray-300">is_enriched</span>
            <span className="bg-surface px-1.5 py-0.5 rounded text-gray-500 font-mono text-[10px]">BOOL</span>
          </div>
        </div>
      </div>
      
      <div className="mt-auto pt-4">
         <button className="w-full bg-transparent border border-surfaceBorder text-gray-400 hover:text-primary hover:border-primary font-bold text-xs tracking-wider uppercase py-3 rounded transition-all duration-200">
            View Full Metadata
         </button>
      </div>

    </div>
  )
}
