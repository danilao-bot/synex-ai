'use client'

import React, { useState, useEffect } from 'react'
import { Filter, RefreshCw, Copy, CheckCircle2, Loader2, Database, AlertCircle, Download, Check } from 'lucide-react'
import { API_BASE_URL } from '../../lib/api'

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRun, setSelectedRun] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [copiedId, setCopiedId] = useState(false)

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/history`)
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

  const successCount = runs.filter(r => r.status?.toLowerCase() === 'completed' || r.status?.toLowerCase() === 'success').length
  const successRate = runs.length > 0 ? ((successCount / runs.length) * 100).toFixed(1) : '100.0'

  const filteredRuns = runs.filter(run => {
    const matchesSearch = (run.prompt || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (run.target_name || '').toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'ALL' || 
                          (statusFilter === 'COMPLETED' && (run.status?.toLowerCase() === 'completed' || run.status?.toLowerCase() === 'success')) ||
                          (statusFilter === 'FAILED' && run.status?.toLowerCase() === 'failed')
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

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-hidden">
      {/* Header */}
      <header className="mb-6 shrink-0 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight font-display">Execution Run History</h1>
          <p className="text-sm text-gray-400 mt-1 font-sans">Audit past data modeling tasks, synthesized contracts, and trace logs.</p>
        </div>
        <button 
          onClick={exportCSV}
          disabled={runs.length === 0}
          className="border border-surfaceBorder bg-surface hover:bg-surfaceBorder text-gray-200 hover:text-white font-semibold text-xs px-4 py-2.5 rounded-xl transition flex items-center gap-2 shadow-sm disabled:opacity-40 font-sans cursor-pointer"
        >
          <Download className="w-4 h-4 text-primary" /> Export CSV
        </button>
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
                  <tr className="border-b border-surfaceBorder">
                    <th className="p-3 text-[10px] font-mono text-gray-500 tracking-widest uppercase">Status</th>
                    <th className="p-3 text-[10px] font-mono text-gray-500 tracking-widest uppercase">Prompt</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRuns.map((run) => (
                    <tr 
                      key={run.id} 
                      onClick={() => setSelectedRun(run)}
                      className={`border-b border-surfaceBorder/50 cursor-pointer transition ${selectedRun?.id === run.id ? 'bg-primary/10' : 'hover:bg-surfaceBorder/30'}`}
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${run.status === 'completed' || run.status === 'SUCCESS' ? 'bg-success' : 'bg-danger'}`} />
                          <span className={`text-[10px] font-mono uppercase ${run.status === 'completed' || run.status === 'SUCCESS' ? 'text-success' : 'text-danger'}`}>{run.status}</span>
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
    </div>
  )
}
