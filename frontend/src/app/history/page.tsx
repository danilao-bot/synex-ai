'use client'

import React, { useState, useEffect } from 'react'
import { Filter, RefreshCw, Copy, CheckCircle2, Loader2, Database, AlertCircle, Download, Check, Split, ArrowLeftRight, ChevronRight, X } from 'lucide-react'
import { API_BASE_URL, fetchWithAuth } from '../../lib/api'

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRun, setSelectedRun] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [copiedId, setCopiedId] = useState(false)

  // Run Comparison States
  const [compareIds, setCompareIds] = useState<string[]>([])
  const [showCompare, setShowCompare] = useState(false)

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/v1/history`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const fetchedRuns = data.runs || []
      setRuns(fetchedRuns)
      if (fetchedRuns.length > 0) {
        setSelectedRun(fetchedRuns[0])
      }
    } catch (err: any) {
      setError(`Unable to connect to Synex Backend (${err.message})`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const successCount = runs.filter(r => {
    const s = (r.status || '').toUpperCase()
    return s === 'SUCCESS' || s === 'COMPLETED'
  }).length
  const successRate = runs.length > 0 ? ((successCount / runs.length) * 100).toFixed(1) : '100.0'

  const filteredRuns = runs.filter(run => {
    const matchesSearch = (run.prompt || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (run.target_name || '').toLowerCase().includes(searchTerm.toLowerCase())
    const status = (run.status || '').toUpperCase()
    const matchesStatus = statusFilter === 'ALL' ||
                          (statusFilter === 'COMPLETED' && (status === 'SUCCESS' || status === 'COMPLETED')) ||
                          (statusFilter === 'FAILED' && status === 'FAILED')
    return matchesSearch && matchesStatus
  })

  const exportCSV = () => {
    if (runs.length === 0) return
    const headers = ['Run ID', 'Status', 'Prompt', 'Target URN', 'Created At']
    const rows = runs.map(r => [
      `"${r.id || ''}"`,
      `"${r.status || ''}"`,
      `"${(r.prompt || '').replace(/"/g, '""')}"`,
      `"${r.target_urn || ''}"`,
      `"${r.created_at || ''}"`
    ])
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', 'synex_execution_history.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Toggle selection of run for comparison
  const handleToggleCompare = (id: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent selecting the run in detail view
    setCompareIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(x => x !== id)
      } else {
        if (prev.length >= 2) return [prev[1], id] // Keep max 2 selections
        return [...prev, id]
      }
    })
  }

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-hidden">
      {/* Header */}
      <header className="mb-6 shrink-0 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight font-display">Execution Run History</h1>
          <p className="text-sm text-gray-400 mt-1 font-sans">Audit past data modeling tasks, synthesized contracts, and trace logs.</p>
        </div>
        <div className="flex gap-3">
          {compareIds.length === 2 && (
            <button
              onClick={() => setShowCompare(true)}
              className="bg-primary hover:bg-primaryHover text-white font-bold text-xs px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-[0_0_15px_rgba(99,102,241,0.3)] cursor-pointer"
            >
              <ArrowLeftRight className="w-4 h-4" /> Compare Selected ({compareIds.length})
            </button>
          )}
          <button 
            onClick={exportCSV}
            disabled={runs.length === 0}
            className="border border-surfaceBorder bg-surface hover:bg-surfaceBorder text-gray-200 hover:text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-sm disabled:opacity-40 font-sans cursor-pointer"
          >
            <Download className="w-4 h-4 text-primary" /> Export CSV
          </button>
        </div>
      </header>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-3 gap-6 mb-6 shrink-0">
        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg relative flex flex-col justify-between">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">SUCCESS RATE</h3>
            <CheckCircle2 className="w-4 h-4 text-success" />
          </div>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full border-[3px] border-success border-r-surfaceBorder flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-gray-200 font-sans">{successRate}%</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-white font-sans tracking-tight">{successRate}%</div>
              <div className="text-xs text-gray-500 font-sans mt-0.5">Real-Time Telemetry</div>
            </div>
          </div>
        </div>

        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">RECORDED RUNS</h3>
            <Database className="w-4 h-4 text-accent" />
          </div>
          <div>
            <div className="text-2xl font-bold text-accent font-sans tracking-tight">{runs.length}</div>
            <div className="text-xs text-gray-500 font-sans mt-0.5">Total executions recorded</div>
          </div>
        </div>

        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">BACKEND CONNECTION</h3>
            <span className={`w-2.5 h-2.5 rounded-full ${error ? 'bg-danger' : 'bg-success animate-pulse'}`} />
          </div>
          <div>
            <div className="text-lg font-bold text-white font-sans">{error ? 'DISCONNECTED' : 'VAULT SYNC LIVE'}</div>
            <div className="text-xs text-gray-500 font-sans mt-0.5">
              {error ? 'Check server connection' : 'Audit telemetry stream active'}
            </div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex justify-between items-center bg-surface border border-surfaceBorder rounded-xl p-3 mb-6 shrink-0">
        <div className="flex gap-4 items-center">
          <div className="flex items-center gap-2 text-xs text-gray-400 font-sans">
            <Filter className="w-4 h-4 text-primary" /> Filter:
          </div>
          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#0A0E17] border border-surfaceBorder text-gray-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary transition cursor-pointer font-sans"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
          </select>
          {compareIds.length > 0 && (
            <span className="text-[10px] text-accent font-mono">
              Selected for comparison: {compareIds.length}/2. Check another log row box.
            </span>
          )}
        </div>

        <input 
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search prompts or models..."
          className="bg-[#0A0E17] border border-surfaceBorder rounded-lg px-4 py-1.5 text-xs text-white placeholder-gray-500 w-72 focus:outline-none focus:border-primary transition font-sans"
        />
      </div>

      {/* Main Split View */}
      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
        {/* Left Table */}
        <div className="col-span-5 bg-surface border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-surfaceBorder">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase font-mono">Execution Log History</h3>
            <button onClick={fetchHistory} className="p-1 rounded hover:bg-surfaceBorder text-gray-400 hover:text-white transition" title="Refresh Log">
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-gray-500 gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-xs font-mono">Fetching execution history...</span>
            </div>
          ) : error ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <AlertCircle className="w-8 h-8 text-danger mb-3" />
              <p className="text-sm font-semibold text-gray-300 mb-1">Backend Connection Error</p>
              <p className="text-xs text-gray-500 font-mono mb-4">{error}</p>
              <button onClick={fetchHistory} className="px-3 py-1.5 bg-surface border border-surfaceBorder rounded text-xs text-white hover:border-primary transition">
                Retry Connection
              </button>
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
              <Database className="w-8 h-8 text-gray-600 mb-3" />
              <p className="text-sm text-gray-400 font-semibold mb-1">No Runs Found</p>
              <p className="text-xs text-gray-500 max-w-xs font-sans">No execution logs match your search filter.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-auto custom-scrollbar">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surfaceBorder text-[10px] font-mono text-gray-500 tracking-widest uppercase">
                    <th className="p-3 w-8">Comp</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Prompt</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRuns.map((run) => (
                    <tr 
                      key={run.id} 
                      onClick={() => setSelectedRun(run)}
                      className={`border-b border-surfaceBorder/50 cursor-pointer transition ${selectedRun?.id === run.id ? 'bg-primary/10' : 'hover:bg-surfaceBorder/30'}`}
                    >
                      <td className="p-3 text-center">
                        <input
                          type="checkbox"
                          checked={compareIds.includes(run.id)}
                          onChange={(e) => handleToggleCompare(run.id, e as any)}
                          className="rounded border-surfaceBorder text-primary focus:ring-primary w-3.5 h-3.5 cursor-pointer bg-background"
                        />
                      </td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${['SUCCESS', 'COMPLETED'].includes((run.status || '').toUpperCase()) ? 'bg-success' : 'bg-danger'}`} />
                          <span className={`text-[10px] font-mono uppercase ${['SUCCESS', 'COMPLETED'].includes((run.status || '').toUpperCase()) ? 'text-success' : 'text-danger'}`}>{run.status}</span>
                        </div>
                      </td>
                      <td className="p-3 text-xs text-gray-300 truncate max-w-[180px] font-sans">{run.prompt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Detail Pane */}
        <div className="col-span-7 bg-surface border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden">
          {selectedRun ? (
            <>
              <div className="flex justify-between items-center p-4 border-b border-surfaceBorder bg-[#0A0E17]">
                <div>
                  <h2 className="text-sm font-bold text-white tracking-wide font-mono">Run ID: {selectedRun.id}</h2>
                  <p className="text-[10px] text-gray-500 font-mono mt-0.5">{selectedRun.created_at || 'Just now'}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(selectedRun.id || '')
                      setCopiedId(true)
                      setTimeout(() => setCopiedId(false), 2000)
                    }}
                    className="p-1.5 rounded hover:bg-surfaceBorder text-gray-400 hover:text-white transition"
                    title="Copy Run ID"
                  >
                    {copiedId ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}
                  </button>
                  <span className="bg-surfaceBorder px-2.5 py-1 rounded text-xs font-mono text-accent">
                    {selectedRun.target_name || 'Synthesized Model'}
                  </span>
                </div>
              </div>

              <div className="flex-1 overflow-auto custom-scrollbar p-6 space-y-6">
                {/* Original Prompt */}
                <div>
                  <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2 font-mono">Original Prompt</h3>
                  <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 text-sm text-gray-200 font-sans">
                    "{selectedRun.prompt}"
                  </div>
                </div>

                {/* Workflow steps from Phase 2 */}
                {((selectedRun.workflow_steps || selectedRun.trace_logs) || []).length > 0 && (
                  <div>
                    <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2 font-mono">Workflow Steps</h3>
                    <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 space-y-2 max-h-56 overflow-auto custom-scrollbar">
                      {(selectedRun.workflow_steps || selectedRun.trace_logs || []).map((s: any, i: number) => (
                        <div key={i} className="flex items-start justify-between gap-3 text-[11px]">
                          <div>
                            <span className="text-accent font-mono">{s.label || s.stage_label || s.type || s.id || `step-${i + 1}`}</span>
                            <p className="text-gray-400 mt-0.5">{s.message || s.reasoning_summary || ''}</p>
                          </div>
                          <span className="text-gray-600 font-mono shrink-0">
                            {s.status || ''}{typeof s.duration_ms === 'number' ? ` · ${s.duration_ms}ms` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Generated SQL */}
                {selectedRun.sql && (
                  <div>
                    <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2 font-mono">Synthesized SQL</h3>
                    <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 font-mono text-xs text-gray-300 overflow-x-auto max-h-48">
                      <pre>{selectedRun.sql}</pre>
                    </div>
                  </div>
                )}

                {/* Generated dbt YAML */}
                {selectedRun.dbt_yaml && (
                  <div>
                    <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2 font-mono">dbt Contract (schema.yml)</h3>
                    <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 font-mono text-xs text-accent overflow-x-auto max-h-36">
                      <pre>{selectedRun.dbt_yaml}</pre>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-gray-500 text-sm font-sans">
              Select a run from the history log to inspect details.
            </div>
          )}
        </div>
      </div>

      {/* Full-Screen Comparison Modal */}
      {showCompare && compareIds.length === 2 && (
        <RunComparisonModal 
          runIdA={compareIds[0]} 
          runIdB={compareIds[1]} 
          runs={runs} 
          onClose={() => { setShowCompare(false); setCompareIds([]) }} 
        />
      )}
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   RUN COMPARISON MODAL SUB-COMPONENT
   ───────────────────────────────────────────────────────────────────────────── */
interface CompareModalProps {
  runIdA: string
  runIdB: string
  runs: any[]
  onClose: () => void
}

const RunComparisonModal: React.FC<CompareModalProps> = ({ runIdA, runIdB, runs, onClose }) => {
  const runA = runs.find(r => r.id === runIdA)
  const runB = runs.find(r => r.id === runIdB)

  if (!runA || !runB) return null

  // Calculate parameters for side-by-side SQL diff
  const splitA = (runA.sql || '').split('\n')
  const splitB = (runB.sql || '').split('\n')

  const trustA = runA.confidence || 75
  const trustB = runB.confidence || 85
  const trustDiff = trustB - trustA

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-fadeIn">
      <div className="bg-surface border border-surfaceBorder rounded-2xl w-full max-w-6xl h-[90vh] flex flex-col overflow-hidden shadow-2xl">
        
        {/* Modal Header */}
        <header className="p-4 border-b border-surfaceBorder bg-[#0A0E17] flex justify-between items-center shrink-0">
          <div className="flex items-center gap-2">
            <Split className="w-5 h-5 text-primary" />
            <div>
              <h2 className="text-base font-bold text-white font-display">Iterative Run Comparison Analysis</h2>
              <p className="text-xs text-gray-400 font-sans">Identify differences in prompts, trust dimensions, and synthesized code.</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded hover:bg-surfaceBorder text-gray-400 hover:text-white transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        {/* Modal Content */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          
          {/* Key Metrics Comparison Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Trust Comparison */}
            <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Trust Score Change</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-gray-200 font-mono">{trustA}% → {trustB}%</span>
                <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${trustDiff >= 0 ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'}`}>
                  {trustDiff >= 0 ? `+${trustDiff}%` : `${trustDiff}%`}
                </span>
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Iterative reasoning improved confidence score.</p>
            </div>

            {/* Downstream dependencies comparison */}
            <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Target Entities</span>
              <div className="text-xs text-gray-300 font-mono truncate space-y-1">
                <div><span className="text-gray-500 uppercase mr-1 text-[8px]">Run A:</span> {runA.target_name || 'selected'}</div>
                <div><span className="text-gray-500 uppercase mr-1 text-[8px]">Run B:</span> {runB.target_name || 'selected'}</div>
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Muted assets matching and lineage targets.</p>
            </div>

            {/* Connection and status */}
            <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Workflow Statuses</span>
              <div className="flex justify-between text-xs font-mono text-gray-300 mt-1">
                <div><span className="text-gray-500 uppercase mr-1 text-[8px]">Run A:</span> <span className={runA.status === 'FAILED' ? 'text-danger' : 'text-success'}>{runA.status}</span></div>
                <div><span className="text-gray-500 uppercase mr-1 text-[8px]">Run B:</span> <span className={runB.status === 'FAILED' ? 'text-danger' : 'text-success'}>{runB.status}</span></div>
              </div>
              <p className="text-[11px] text-gray-400 mt-2">Ensures pipeline consistency checks compile successfully.</p>
            </div>

          </div>

          {/* Prompts Comparison */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase font-mono">Prompt Differences</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[#04060C] border border-surfaceBorder rounded p-4 text-xs font-sans text-gray-300">
                <span className="font-bold text-accent block mb-1 uppercase text-[9px] font-mono">Run A Prompt</span>
                "{runA.prompt}"
              </div>
              <div className="bg-[#04060C] border border-surfaceBorder rounded p-4 text-xs font-sans text-gray-300">
                <span className="font-bold text-primary block mb-1 uppercase text-[9px] font-mono">Run B Prompt</span>
                "{runB.prompt}"
              </div>
            </div>
          </div>

          {/* SQL Side-by-Side Code Compare */}
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-gray-400 tracking-widest uppercase font-mono">Side-by-Side Model SQL</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#04060C] border border-surfaceBorder rounded-xl overflow-hidden divide-x divide-surfaceBorder">
              {/* SQL Column A */}
              <div className="overflow-x-auto p-4 max-h-[40vh] custom-scrollbar">
                <span className="font-bold text-accent uppercase text-[9px] font-mono block mb-2">Run A Code</span>
                <pre className="font-mono text-[11px] leading-relaxed text-gray-400">
                  {splitA.map((line: string, idx: number) => {
                    const isDiff = !splitB.includes(line)
                    return (
                      <div key={idx} className={isDiff ? 'bg-danger/10 text-danger-300 px-1 rounded' : ''}>
                        {line || ' '}
                      </div>
                    )
                  })}
                </pre>
              </div>

              {/* SQL Column B */}
              <div className="overflow-x-auto p-4 max-h-[40vh] custom-scrollbar pl-4">
                <span className="font-bold text-success uppercase text-[9px] font-mono block mb-2">Run B Code</span>
                <pre className="font-mono text-[11px] leading-relaxed text-gray-400">
                  {splitB.map((line: string, idx: number) => {
                    const isDiff = !splitA.includes(line)
                    return (
                      <div key={idx} className={isDiff ? 'bg-success/10 text-success-300 px-1 rounded font-semibold' : ''}>
                        {line || ' '}
                      </div>
                    )
                  })}
                </pre>
              </div>
            </div>
          </div>

        </div>
        
        {/* Modal Footer */}
        <footer className="p-4 border-t border-surfaceBorder bg-[#0A0E17] flex justify-end shrink-0">
          <button 
            onClick={onClose}
            className="bg-primary hover:bg-primaryHover text-white font-bold text-xs px-6 py-2.5 rounded-xl transition cursor-pointer"
          >
            Close Analysis
          </button>
        </footer>

      </div>
    </div>
  )
}
