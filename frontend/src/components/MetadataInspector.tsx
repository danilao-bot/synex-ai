'use client'

import React from 'react'
import { AlertTriangle, Database, ShieldCheck, Tag, CheckCircle2, XCircle, Award, Users, Globe, BookOpen } from 'lucide-react'
import { useWorkspaceStore, SchemaField } from '../store/useWorkspaceStore'

export const MetadataInspector: React.FC = () => {
  const {
    selectedUrn,
    selectedPiiColumns,
    selectedSchemaFields,
    selectedDatasetName,
    selectedDatasetDescription,
    selectedCandidate,
    messages,
  } = useWorkspaceStore()
  const [showModal, setShowModal] = React.useState(false)

  const lastAgentMsg = [...messages].reverse().find((m) => m.sender === 'agent' && m.result)
  const validation = lastAgentMsg?.result?.validation
  const candidates = lastAgentMsg?.result?.candidate_datasets || []

  if (!selectedUrn) {
    return (
      <div className="h-full flex flex-col justify-center items-center text-center px-4 animate-fadeIn">
        <div className="w-24 h-24 mb-6 relative">
          <svg viewBox="0 0 100 100" fill="none" className="w-full h-full text-surfaceBorder">
            <rect x="10" y="10" width="80" height="80" rx="8" stroke="currentColor" strokeWidth="3" strokeDasharray="6 6"/>
            <rect x="20" y="30" width="60" height="8" rx="4" fill="currentColor" opacity="0.5"/>
            <rect x="20" y="50" width="40" height="8" rx="4" fill="currentColor" opacity="0.5"/>
            <rect x="20" y="70" width="50" height="8" rx="4" fill="currentColor" opacity="0.5"/>
          </svg>
        </div>
        <h2 className="text-lg font-display font-semibold text-gray-400 mb-2">Metadata Aspect Inspector</h2>
        <p className="text-gray-500 text-sm font-sans max-w-[200px] leading-relaxed">
          Run a prompt to inspect real DataHub graph aspects, trust scores, and governance validation reports.
        </p>
      </div>
    )
  }

  const piiSet = new Set(selectedPiiColumns)
  const trustScore = selectedCandidate?.trust_score ?? 85

  const scoreColor = 
    trustScore >= 80 ? 'text-success border-success/40 bg-success/10' :
    trustScore >= 50 ? 'text-warning border-warning/40 bg-warning/10' :
    'text-danger border-danger/40 bg-danger/10'

  return (
    <div className="h-full flex flex-col gap-5 animate-fadeIn relative text-xs">
      <div>
        <h2 className="text-lg font-display font-semibold text-white mb-1 tracking-tight">DataHub Aspect Inspector</h2>
        <div className="w-12 h-1 bg-primary"></div>
      </div>

      {/* Trust Score & Certification Banner */}
      <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-3.5 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-accent" />
            <span className="font-bold text-gray-200">Trust Score</span>
          </div>
          <div className={`px-2.5 py-0.5 rounded-full border font-mono font-bold text-xs ${scoreColor}`}>
            {trustScore} / 100
          </div>
        </div>

        {selectedCandidate && (
          <div className="flex gap-1.5 flex-wrap pt-1">
            {selectedCandidate.is_certified && (
              <span className="flex items-center gap-1 bg-success/15 border border-success/30 text-success text-[10px] px-2 py-0.5 rounded-full font-bold">
                <CheckCircle2 className="w-3 h-3" /> Certified Asset
              </span>
            )}
            {selectedCandidate.is_deprecated ? (
              <span className="flex items-center gap-1 bg-danger/15 border border-danger/30 text-danger text-[10px] px-2 py-0.5 rounded-full font-bold">
                <XCircle className="w-3 h-3" /> Deprecated
              </span>
            ) : (
              <span className="flex items-center gap-1 bg-primary/15 border border-primary/30 text-primary text-[10px] px-2 py-0.5 rounded-full font-bold">
                Active Source
              </span>
            )}
            {selectedCandidate.owners.length > 0 && (
              <span className="flex items-center gap-1 bg-surface border border-surfaceBorder text-gray-300 text-[10px] px-2 py-0.5 rounded">
                <Users className="w-2.5 h-2.5 text-accent" /> {selectedCandidate.owners[0]}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Dataset Identity */}
      {selectedDatasetName && (
        <div className="space-y-1">
          <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Dataset</h3>
          <div className="flex items-center gap-2 bg-[#040A14] border border-surfaceBorder/60 rounded p-2.5">
            <Database className="w-4 h-4 text-accent shrink-0" />
            <span className="font-mono text-gray-200 break-all font-semibold">{selectedDatasetName}</span>
          </div>
          {selectedDatasetDescription && (
            <p className="text-gray-500 text-[11px] font-sans leading-relaxed pt-1">{selectedDatasetDescription}</p>
          )}
        </div>
      )}

      {/* Deterministic Validation Report */}
      {validation && (
        <div className={`p-3 rounded-xl border ${validation.passed ? 'bg-success/5 border-success/30' : 'bg-danger/5 border-danger/30'}`}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 font-bold">
              {validation.passed ? <ShieldCheck className="w-4 h-4 text-success" /> : <AlertTriangle className="w-4 h-4 text-danger" />}
              <span className={validation.passed ? 'text-success' : 'text-danger'}>
                {validation.passed ? 'Governance Validation Passed' : 'Validation Blocking Errors'}
              </span>
            </div>
          </div>
          {validation.blocking_errors && validation.blocking_errors.length > 0 ? (
            <ul className="space-y-1 text-[11px] text-danger font-sans list-disc list-inside">
              {validation.blocking_errors.map((err: string, i: number) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          ) : (
            <p className="text-[11px] text-gray-400 font-sans">Zero blocking errors detected. Mandatory PII masking & schema contracts confirmed.</p>
          )}
        </div>
      )}

      {/* PII Warning */}
      {selectedPiiColumns && selectedPiiColumns.length > 0 && (
        <div className="bg-[#1A1400] border border-warning/50 rounded-lg p-3 shadow-[0_0_15px_rgba(255,159,0,0.1)] space-y-1">
          <div className="flex items-center gap-1.5 text-warning font-bold uppercase text-[10px] tracking-wider">
            <AlertTriangle className="w-3.5 h-3.5" /> PII Masking Enforced
          </div>
          <p className="text-gray-300 text-[11px] leading-relaxed font-sans">
            Fields <span className="text-warning font-mono">{selectedPiiColumns.join(', ')}</span> are hashed via SHA2.
          </p>
        </div>
      )}

      {/* Selection Reasoning */}
      {selectedCandidate && selectedCandidate.selection_reasons.length > 0 && (
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">Selection Reasons</h3>
          <ul className="space-y-1 text-gray-300 text-[11px] font-sans">
            {selectedCandidate.selection_reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-success font-bold">✓</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Schema Fields */}
      <div className="space-y-2">
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase">
          Schema Fields ({selectedSchemaFields.length})
        </h3>
        <div className="space-y-1 max-h-44 overflow-y-auto custom-scrollbar pr-1">
          {selectedSchemaFields.map((field: SchemaField) => {
            const isPii = piiSet.has(field.fieldPath)
            return (
              <div
                key={field.fieldPath}
                className={`flex justify-between items-center py-1 px-2 rounded ${isPii ? 'bg-warning/10 border border-warning/30 text-warning' : 'border border-surfaceBorder/30 text-gray-300'}`}
              >
                <div className="flex items-center gap-1.5 truncate">
                  {isPii && <AlertTriangle className="w-3 h-3 text-warning shrink-0" />}
                  <span className="font-mono text-[11px] truncate">{field.fieldPath}</span>
                </div>
                <span className="bg-surface px-1.5 py-0.5 rounded text-gray-500 font-mono text-[9px] shrink-0">
                  {field.nativeDataType}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-auto pt-2">
        <button
          onClick={() => setShowModal(true)}
          className="w-full bg-transparent border border-surfaceBorder text-gray-400 hover:text-primary hover:border-primary font-bold text-[11px] tracking-wider uppercase py-2.5 rounded transition cursor-pointer"
        >
          View Aspect Metadata JSON
        </button>
      </div>

      {/* Full Aspect JSON Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-fadeIn">
          <div className="bg-surface border border-surfaceBorder rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-surfaceBorder pb-3">
              <h3 className="text-sm font-bold text-white font-display">DataHub Real Graph Aspect JSON</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white text-xs font-mono">✕ Close</button>
            </div>
            <div className="bg-[#04060C] p-4 rounded-xl font-mono text-[11px] text-accent overflow-auto max-h-96">
              <pre>{JSON.stringify({
                selected_candidate: selectedCandidate,
                selected_urn: selectedUrn,
                dataset_name: selectedDatasetName,
                pii_columns: selectedPiiColumns,
                schema_fields: selectedSchemaFields,
                all_candidates: candidates,
              }, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
