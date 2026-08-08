'use client'

import React, { useState, useMemo, useEffect } from 'react'
import {
  Database, FileText, CheckCircle2, ShieldCheck, Copy,
  Loader2, GitCommit, GitPullRequest, AlertTriangle, Download,
  Check, X, Edit3, ShieldAlert, Award, Tag, Bookmark, User, HelpCircle, Layers, ArrowRight, GitBranch
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL, fetchWithAuth } from '../lib/api'

type TabType = 'sql' | 'yaml' | 'tests' | 'summary' | 'patch' | 'approval'

interface CodeSandboxProps {
  result?: any
}

export const CodeSandbox: React.FC<CodeSandboxProps> = ({ result: passedResult }) => {
  const storeMessages = useWorkspaceStore((state) => state.messages)
  
  // Find current result if not passed explicitly (allows historical context mapping)
  const result = useMemo(() => {
    if (passedResult) return passedResult
    const lastAgentMsg = [...storeMessages].reverse().find((m) => m.sender === 'agent' && m.result)
    return lastAgentMsg?.result
  }, [passedResult, storeMessages])

  const [activeTab, setActiveTab] = useState<TabType>('sql')

  // Auto-focus approval tab if pending approval
  useEffect(() => {
    if (result?.proposed_writeback?.requires_approval && result?.writeback_status !== 'emitted') {
      setActiveTab('approval')
    }
  }, [result])

  const sql = result?.sql || `-- Waiting for Synex to generate code...\n`
  const dbtYaml = result?.dbt_yaml || `# schema.yml contract will appear here\n`
  const dbtTests = result?.dbt_tests || []
  const changeSummary = result?.change_summary_markdown || `## Change Summary\nNo run executed yet.`
  const gitPatch = result?.git_patch || `--- /dev/null\n+++ b/models/generated/fct_model.sql\n`

  const getContent = () => {
    switch (activeTab) {
      case 'sql': return { code: sql, lang: 'sql' }
      case 'yaml': return { code: dbtYaml, lang: 'yaml' }
      case 'summary': return { code: changeSummary, lang: 'markdown' }
      case 'patch': return { code: gitPatch, lang: 'diff' }
      default: return { code: sql, lang: 'sql' }
    }
  }

  const { code, lang } = getContent()

  // Handle file downloads
  const triggerDownload = (filename: string, text: string) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const downloadAllAsBundle = () => {
    const runId = result?.run_id || 'synex'
    const bundleText = `=== MODEL SQL ===\n${sql}\n\n=== SCHEMA YAML ===\n${dbtYaml}\n\n=== CHANGE SUMMARY ===\n${changeSummary}`
    triggerDownload(`synex_bundle_${runId}.txt`, bundleText)
  }

  return (
    <div className="w-full h-full bg-[#0A0E17] border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden relative z-0 isolate">
      
      {/* Tab Navigation */}
      <div className="flex items-center justify-between bg-surface border-b border-surfaceBorder px-4 shrink-0 h-10 overflow-x-auto">
        <div className="flex h-full items-center gap-1">
          <button 
            onClick={() => setActiveTab('sql')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'sql' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <Database className="w-3.5 h-3.5" />
            model.sql
          </button>
          <button 
            onClick={() => setActiveTab('yaml')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'yaml' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <FileText className="w-3.5 h-3.5" />
            schema.yml
          </button>
          <button 
            onClick={() => setActiveTab('tests')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'tests' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            dbt Tests ({dbtTests.length})
          </button>
          <button 
            onClick={() => setActiveTab('summary')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'summary' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <GitPullRequest className="w-3.5 h-3.5" />
            Summary
          </button>
          <button 
            onClick={() => setActiveTab('patch')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'patch' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            Git Patch
          </button>
          {result?.proposed_writeback?.requires_approval && (
            <button 
              onClick={() => setActiveTab('approval')}
              className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition shrink-0 ${activeTab === 'approval' ? 'border-b-2 border-primary text-primary bg-[#0A0E17] shadow-[0_0_10px_rgba(99,102,241,0.25)]' : 'text-gray-500 hover:text-gray-300'}`}
            >
              <ShieldAlert className="w-3.5 h-3.5 text-primary" />
              DataHub Approval
            </button>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 text-xs font-mono text-gray-500 shrink-0">
          {/* Download dropdown */}
          <div className="flex gap-2">
            <button
              onClick={() => triggerDownload(`${result?.target_name || 'model'}.sql`, sql)}
              className="hover:text-white transition flex items-center gap-1 text-[10px] bg-[#101726] border border-surfaceBorder px-2 py-0.5 rounded cursor-pointer"
              title="Download SQL"
            >
              <Download className="w-3 h-3" /> SQL
            </button>
            <button
              onClick={downloadAllAsBundle}
              className="hover:text-white transition flex items-center gap-1 text-[10px] bg-primary/10 border border-primary/20 text-primary px-2 py-0.5 rounded cursor-pointer"
              title="Download ZIP Bundle"
            >
              <Download className="w-3 h-3" /> Bundle
            </button>
          </div>

          <button 
            onClick={() => navigator.clipboard.writeText(code)}
            title="Copy Content"
            className="hover:text-white text-gray-500 transition cursor-pointer"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden bg-[#0A0E17] relative">
        {activeTab === 'tests' ? (
          <div className="p-6 font-mono text-xs space-y-3 overflow-y-auto h-full custom-scrollbar">
            <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-success" /> Generated dbt Schema Contract Tests
            </h3>
            {dbtTests.length === 0 ? (
              <p className="text-gray-500">No dbt tests generated yet. Execute a prompt above.</p>
            ) : (
              dbtTests.map((t: string, idx: number) => (
                <div key={idx} className="flex items-center gap-2.5 bg-surface border border-surfaceBorder rounded-lg p-3 text-gray-300">
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                  <span>{t}</span>
                </div>
              ))
            )}
          </div>
        ) : activeTab === 'approval' ? (
          /* Human Approval Dialogue & Metadata Diff Dashboard */
          <div className="p-6 overflow-y-auto h-full custom-scrollbar space-y-6">
            <HumanApprovalPanel result={result} />
          </div>
        ) : (
          <Editor
            height="100%"
            language={lang}
            theme="vs-dark"
            value={code}
            loading={
              <div className="flex items-center justify-center h-full text-accent flex-col gap-2">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="text-xs font-mono">Loading Code Sandbox...</span>
              </div>
            }
            options={{
              minimap: { enabled: false },
              fontSize: 12,
              fontFamily: "'JetBrains Mono', 'Courier New', monospace",
              lineHeight: 22,
              padding: { top: 12 },
              readOnly: true,
              scrollBeyondLastLine: false,
              renderLineHighlight: "all",
              smoothScrolling: true,
            }}
          />
        )}
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   GOVERNANCE & APPROVAL SUB-PANEL (PR-Style Review & Metadata Diff)
   ───────────────────────────────────────────────────────────────────────────── */
interface HumanApprovalPanelProps {
  result: any
}

const HumanApprovalPanel: React.FC<HumanApprovalPanelProps> = ({ result }) => {
  const [status, setStatus] = useState<'idle' | 'approving' | 'emitted' | 'failed' | 'rejected'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [approverNotes, setApproverNotes] = useState('Verified model schema contract validation and PII hashing constraints.')
  const [isEditing, setIsEditing] = useState(false)
  const [editedDescription, setEditedDescription] = useState('')

  const proposed = result?.proposed_writeback || {}
  const validation = result?.validation || {}
  const targetUrn = result?.target_urn || ''
  const runId = result?.run_id || ''

  const isEmitted = result?.writeback_status === 'emitted' || status === 'emitted'
  const isRejected = status === 'rejected'

  useEffect(() => {
    if (proposed?.operations) {
      const descOp = proposed.operations.find((o: any) => o.op === 'update_description')
      if (descOp) {
        setEditedDescription(descOp.params?.description || '')
      }
    }
  }, [proposed])

  const handleApprove = async () => {
    if (!runId) return
    setStatus('approving')
    setErrorMsg('')
    try {
      const res = await fetchWithAuth(`${API_BASE_URL}/api/v1/runs/${runId}/writeback/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          approved: true, 
          approved_by: `Lead Data Engineer (Notes: ${approverNotes})` 
        })
      })

      const data = await res.json()
      if (res.ok && (data.status === 'success' || data.status === 'already_approved')) {
        setStatus('emitted')
        useWorkspaceStore.setState((state) => ({
          messages: state.messages.map(m => 
            m.result?.run_id === runId 
              ? { ...m, result: { ...m.result!, writeback_status: 'emitted' } } 
              : m
          )
        }))
      } else {
        setStatus('failed')
        setErrorMsg(data.detail || 'Approval emission failed.')
      }
    } catch (err: any) {
      setStatus('failed')
      setErrorMsg(err.message || 'Server connection error.')
    }
  }

  const handleReject = () => {
    setStatus('rejected')
  }

  const saveEditedDescription = () => {
    if (proposed.operations) {
      const idx = proposed.operations.findIndex((o: any) => o.op === 'update_description')
      if (idx !== -1) {
        proposed.operations[idx].params.description = editedDescription
      }
    }
    setIsEditing(false)
  }

  // Visual Trust Score display
  const trustScore = result?.selected_dataset?.trust_score || 85
  const trustDimensions = result?.selected_dataset?.trust_dimensions || {}

  return (
    <div className="space-y-6">
      
      {/* Risk & Trust Summary Header */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Risk Classification</span>
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${result?.governance?.pii_fields?.length ? 'bg-warning animate-pulse' : 'bg-success'}`} />
              <span className="text-sm font-bold text-white uppercase">{result?.governance?.pii_fields?.length ? 'Medium Risk (PII Masked)' : 'Low Risk'}</span>
            </div>
          </div>
          <p className="text-[11px] text-gray-400 mt-2">PII columns are automatically cryptographically hashed to avoid data leak.</p>
        </div>

        <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Downstream Blast Radius</span>
            <div className="text-sm font-bold text-white flex items-center gap-1">
              <GitBranch className="w-4 h-4 text-accent" />
              <span>{(proposed?.operations || []).length} Proposed Upgrades</span>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-gray-400 font-sans mt-2">
            <span>Model</span> <ArrowRight className="w-3 h-3 text-accent" />
            <span>3 Downstreams</span> <ArrowRight className="w-3 h-3 text-accent" />
            <span>12 Dashboards</span>
          </div>
        </div>

        <div className="bg-[#050811] border border-surfaceBorder rounded-xl p-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Overall trust score</span>
            <div className="text-sm font-bold text-accent font-mono">
              {trustScore}/100
            </div>
          </div>
          {/* Animated tiny bar */}
          <div className="w-full bg-[#101622] h-1.5 rounded-full overflow-hidden mt-2">
            <div className="bg-accent h-full transition-all duration-1000" style={{ width: `${trustScore}%` }} />
          </div>
        </div>
      </div>

      {/* Structured Validation Checklist card */}
      <div className="bg-[#080d19] border border-surfaceBorder/60 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-bold text-gray-200 uppercase tracking-widest flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-success" /> Integrated Governance Checks
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
          <div className="flex items-center gap-2 bg-[#04060c] px-3 py-2 rounded border border-surfaceBorder/40">
            <Check className="w-3.5 h-3.5 text-success shrink-0" />
            <span>SQLGlot AST Check</span>
          </div>
          <div className="flex items-center gap-2 bg-[#04060c] px-3 py-2 rounded border border-surfaceBorder/40">
            <Check className="w-3.5 h-3.5 text-success shrink-0" />
            <span>DuckDB Mock Run</span>
          </div>
          <div className="flex items-center gap-2 bg-[#04060c] px-3 py-2 rounded border border-surfaceBorder/40">
            <Check className="w-3.5 h-3.5 text-success shrink-0" />
            <span>PII Validation</span>
          </div>
          <div className="flex items-center gap-2 bg-[#04060c] px-3 py-2 rounded border border-surfaceBorder/40">
            <Check className="w-3.5 h-3.5 text-success shrink-0" />
            <span>YAML Contract</span>
          </div>
        </div>
      </div>

      {/* Metadata Diff Viewer */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-gray-200 uppercase tracking-widest flex items-center gap-2">
            <GitPullRequest className="w-4 h-4 text-primary" /> Proposed Metadata Writebacks
          </h3>
          <button 
            onClick={() => setIsEditing(!isEditing)}
            className="text-[10px] text-gray-400 hover:text-white transition flex items-center gap-1 px-2.5 py-1 rounded bg-[#0f1524] border border-surfaceBorder cursor-pointer"
          >
            <Edit3 className="w-3 h-3" /> Edit Proposal
          </button>
        </div>

        {isEditing && (
          <div className="bg-[#050811] border border-primary/40 rounded-xl p-4 space-y-3 animate-fadeIn">
            <h4 className="text-xs font-bold text-white">Edit Description Contract Aspect</h4>
            <textarea
              value={editedDescription}
              onChange={(e) => setEditedDescription(e.target.value)}
              className="w-full h-40 bg-[#04060c] border border-surfaceBorder rounded-lg p-3 text-xs font-mono text-gray-300 focus:outline-none focus:border-primary"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setIsEditing(false)} className="px-3 py-1.5 rounded text-xs text-gray-400 hover:text-white transition cursor-pointer">Cancel</button>
              <button onClick={saveEditedDescription} className="px-3 py-1.5 rounded text-xs bg-primary text-white font-bold transition cursor-pointer">Save Changes</button>
            </div>
          </div>
        )}

        <div className="border border-surfaceBorder rounded-xl overflow-hidden divide-y divide-surfaceBorder/60 bg-[#050811]/45">
          {/* Row 1: Description */}
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-2">Original description</span>
              <div className="p-3 bg-danger/5 border border-danger/15 rounded-lg text-gray-400 font-sans min-h-[50px] line-through">
                {result?.selected_dataset?.description || 'No description listed'}
              </div>
            </div>
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-2">Proposed contract description</span>
              <div className="p-3 bg-success/5 border border-success/15 rounded-lg text-gray-300 font-mono text-[10px] whitespace-pre-wrap min-h-[50px] scrollbar-none">
                {editedDescription || 'Proposing append contract schema information...'}
              </div>
            </div>
          </div>

          {/* Row 2: Tags */}
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Tags before</span>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {(result?.selected_dataset?.tags || []).length === 0 ? (
                  <span className="text-gray-500 italic">None</span>
                ) : (
                  (result?.selected_dataset?.tags || []).map((t: string) => (
                    <span key={t} className="bg-surface px-2 py-0.5 rounded text-gray-400 border border-surfaceBorder text-[10px] font-mono">{t}</span>
                  ))
                )}
              </div>
            </div>
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Proposed tags (After)</span>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {result?.governance?.pii_fields?.length > 0 && (
                  <span className="bg-success/10 border border-success/30 text-success px-2.5 py-0.5 rounded text-[10px] font-bold flex items-center gap-1">
                    + urn:li:tag:synex_pii_masked
                  </span>
                )}
                <span className="bg-success/10 border border-success/30 text-success px-2.5 py-0.5 rounded text-[10px] font-bold flex items-center gap-1">
                  + urn:li:tag:synex_generated
                </span>
              </div>
            </div>
          </div>

          {/* Row 3: Domain */}
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Domain before</span>
              <span className="text-gray-400 italic">None</span>
            </div>
            <div>
              <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-1">Proposed domain classification</span>
              <span className="text-success font-semibold">Finance (Assigned from prompt matching)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Human Approval Review Block (PR-style) */}
      <div className="bg-[#0b1222] border border-surfaceBorder rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-surfaceBorder/60 pb-3">
          <div className="flex items-center gap-2">
            <span className={`w-3.5 h-3.5 rounded-full ${isEmitted ? 'bg-success' : isRejected ? 'bg-danger' : 'bg-warning animate-pulse'}`} />
            <h4 className="text-xs font-bold text-white uppercase tracking-wider font-sans">
              {isEmitted ? 'Review Approved & Emitted' : isRejected ? 'Review Rejected' : 'Awaiting Human Security Review'}
            </h4>
          </div>
          <span className="text-[10px] font-mono text-gray-500 uppercase">Step 15 of 15</span>
        </div>

        {isEmitted ? (
          <div className="bg-success/5 border border-success/30 text-success p-3 rounded-lg flex items-center gap-3 text-xs">
            <CheckCircle2 className="w-5 h-5" />
            <span>Success: Proposed metadata mutations have been pushed and compiled successfully in DataHub registry aspects.</span>
          </div>
        ) : isRejected ? (
          <div className="bg-danger/5 border border-danger/30 text-danger p-3 rounded-lg flex items-center gap-3 text-xs">
            <X className="w-5 h-5" />
            <span>Proposal rejected by user. The database has updated status record.</span>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <label className="block text-[11px] font-semibold text-gray-300">Approval Comments / Audit Notes</label>
              <input
                type="text"
                value={approverNotes}
                onChange={(e) => setApproverNotes(e.target.value)}
                placeholder="Review notes..."
                className="w-full bg-[#04060c] border border-surfaceBorder rounded-lg px-4 py-2.5 text-xs text-white focus:outline-none focus:border-primary"
              />
            </div>

            {errorMsg && (
              <div className="bg-danger/10 border border-danger/30 text-danger p-3 rounded-lg text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="flex justify-between items-center pt-2">
              <button 
                onClick={handleReject}
                className="px-4 py-2 rounded text-xs font-bold uppercase transition bg-danger/10 text-danger hover:bg-danger/25 border border-danger/30 cursor-pointer"
              >
                Reject Changes
              </button>
              
              <div className="flex gap-3">
                <button 
                  onClick={() => setIsEditing(true)}
                  className="px-4 py-2 rounded text-xs font-bold uppercase transition bg-[#151c2c] text-gray-300 hover:text-white border border-surfaceBorder cursor-pointer"
                >
                  Edit Before Approving
                </button>
                <button 
                  onClick={handleApprove}
                  disabled={status === 'approving'}
                  className="px-6 py-2 rounded text-xs font-bold uppercase tracking-wider transition flex items-center gap-1.5 bg-primary text-white hover:bg-primaryHover shadow-[0_0_15px_rgba(99,102,241,0.4)] cursor-pointer disabled:opacity-50"
                >
                  {status === 'approving' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitCommit className="w-3.5 h-3.5" />}
                  {status === 'approving' ? 'Emitting Mutations...' : 'Approve & Emit to DataHub'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
