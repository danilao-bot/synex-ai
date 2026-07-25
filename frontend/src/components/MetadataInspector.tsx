'use client'

import React from 'react'
import { AlertTriangle, Database, Tag } from 'lucide-react'
import { useWorkspaceStore, SchemaField } from '../store/useWorkspaceStore'

export const MetadataInspector: React.FC = () => {
  const {
    selectedUrn,
    selectedPiiColumns,
    selectedSchemaFields,
    selectedDatasetName,
    selectedDatasetDescription,
  } = useWorkspaceStore()
  const [showModal, setShowModal] = React.useState(false)

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
        <h2 className="text-lg font-display font-semibold text-gray-400 mb-2">Aspect Inspector</h2>
        <p className="text-gray-500 text-sm font-sans max-w-[200px] leading-relaxed">
          Run a prompt to inspect real DataHub metadata aspects for the resolved dataset.
        </p>
      </div>
    )
  }

  const piiSet = new Set(selectedPiiColumns)

  return (
    <div className="h-full flex flex-col gap-6 animate-fadeIn relative">
      <div>
        <h2 className="text-xl font-display font-semibold text-white mb-2 tracking-tight">Aspect Inspector</h2>
        <div className="w-12 h-1 bg-primary"></div>
      </div>

      {/* Dataset Name */}
      {selectedDatasetName && (
        <div>
          <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-2">Dataset</h3>
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-accent shrink-0" />
            <span className="text-sm font-mono text-gray-200 break-all">{selectedDatasetName}</span>
          </div>
          {selectedDatasetDescription && (
            <p className="text-xs text-gray-500 mt-2 font-sans leading-relaxed">{selectedDatasetDescription}</p>
          )}
        </div>
      )}

      {/* Dataset URN */}
      <div>
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-2">Dataset URN</h3>
        <div className="bg-[#041A24] border border-accent/30 rounded p-3 text-accent font-mono text-xs break-all">
          {selectedUrn}
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
            Fields <span className="text-warning font-mono">{selectedPiiColumns.join(', ')}</span> are flagged as PII and will be masked in generated SQL.
          </p>
        </div>
      )}

      {/* Schema from DataHub */}
      <div>
        <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase mb-3">
          Schema <span className="text-gray-600 normal-case font-normal">({selectedSchemaFields.length} fields from DataHub)</span>
        </h3>
        {selectedSchemaFields.length === 0 ? (
          <p className="text-xs text-gray-600 font-sans">No schema fields returned from DataHub.</p>
        ) : (
          <div className="space-y-1.5 max-h-52 overflow-y-auto custom-scrollbar pr-1">
            {selectedSchemaFields.map((field: SchemaField) => {
              const isPii = piiSet.has(field.fieldPath)
              const fieldTags = field.tags?.tags?.map(t => t.tag.name) || []
              return (
                <div
                  key={field.fieldPath}
                  className={`flex justify-between items-center text-xs py-1.5 px-2 rounded ${isPii ? 'bg-warning/5 border border-warning/20' : 'border border-surfaceBorder/30'}`}
                >
                  <div className="flex items-center gap-1.5 min-w-0">
                    {isPii && <AlertTriangle className="w-3 h-3 text-warning shrink-0" />}
                    <span className={`font-mono truncate ${isPii ? 'text-warning' : 'text-gray-300'}`}>
                      {field.fieldPath}
                    </span>
                    {fieldTags.length > 0 && (
                      <div className="flex gap-1 shrink-0">
                        {fieldTags.slice(0, 2).map(tag => (
                          <span key={tag} className="flex items-center gap-0.5 text-[9px] bg-primary/10 text-primary px-1 rounded">
                            <Tag className="w-2 h-2" />{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <span className="bg-surface px-1.5 py-0.5 rounded text-gray-500 font-mono text-[10px] shrink-0 ml-2">
                    {field.nativeDataType}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="mt-auto pt-4">
        <button
          onClick={() => setShowModal(true)}
          className="w-full bg-transparent border border-surfaceBorder text-gray-400 hover:text-primary hover:border-primary font-bold text-xs tracking-wider uppercase py-3 rounded transition-all duration-200 cursor-pointer"
        >
          View Full Aspect JSON
        </button>
      </div>

      {/* Full Aspect JSON Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-fadeIn">
          <div className="bg-surface border border-surfaceBorder rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-surfaceBorder pb-4">
              <h3 className="text-base font-bold text-white font-display">DataHub Aspect — Real Metadata</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-white text-sm font-mono">✕ Close</button>
            </div>
            <div className="bg-[#04060C] p-4 rounded-xl font-mono text-xs text-accent overflow-auto max-h-96">
              <pre>{JSON.stringify({
                urn: selectedUrn,
                name: selectedDatasetName,
                description: selectedDatasetDescription,
                pii_columns: selectedPiiColumns,
                schema_fields: selectedSchemaFields,
              }, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
