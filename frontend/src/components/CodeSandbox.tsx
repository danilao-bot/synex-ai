'use client'

import React, { useState } from 'react'
import { Database, FileText, CheckCircle2, ShieldCheck, Copy, Loader2, GitCommit, GitPullRequest, AlertTriangle } from 'lucide-react'
import Editor from '@monaco-editor/react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL } from '../lib/api'

type TabType = 'sql' | 'yaml' | 'tests' | 'summary' | 'patch'

export const CodeSandbox: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('sql')
  const messages = useWorkspaceStore((state) => state.messages)
  const lastAgentMsg = [...messages].reverse().find((m) => m.sender === 'agent' && m.result)

  const result = lastAgentMsg?.result
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

  return (
    <div className="w-full h-full bg-[#0A0E17] border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden relative z-0 isolate">
      {/* Tab Navigation */}
      <div className="flex items-center justify-between bg-surface border-b border-surfaceBorder px-4 shrink-0 h-10 overflow-x-auto">
        <div className="flex h-full items-center gap-1">
          <button 
            onClick={() => setActiveTab('sql')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition ${activeTab === 'sql' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <Database className="w-3.5 h-3.5" />
            model.sql
          </button>
          <button 
            onClick={() => setActiveTab('yaml')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition ${activeTab === 'yaml' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <FileText className="w-3.5 h-3.5" />
            schema.yml
          </button>
          <button 
            onClick={() => setActiveTab('tests')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition ${activeTab === 'tests' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            dbt Tests ({dbtTests.length})
          </button>
          <button 
            onClick={() => setActiveTab('summary')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition ${activeTab === 'summary' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <GitPullRequest className="w-3.5 h-3.5" />
            Summary
          </button>
          <button 
            onClick={() => setActiveTab('patch')}
            className={`flex items-center gap-1.5 px-3 h-full text-xs font-bold tracking-wider transition ${activeTab === 'patch' ? 'border-b-2 border-accent text-accent bg-[#0A0E17]' : 'text-gray-500 hover:text-gray-300'}`}
          >
            <GitCommit className="w-3.5 h-3.5" />
            Git Patch
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 text-xs font-mono text-gray-500 shrink-0">
          <DataHubApprovalButton result={result} />
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
              dbtTests.map((t, idx) => (
                <div key={idx} className="flex items-center gap-2.5 bg-surface border border-surfaceBorder rounded-lg p-3 text-gray-300">
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                  <span>{t}</span>
                </div>
              ))
            )}
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

interface ApprovalButtonProps {
  result?: any;
}

const DataHubApprovalButton: React.FC<ApprovalButtonProps> = ({ result }) => {
  const [status, setStatus] = useState<'idle' | 'approving' | 'emitted' | 'failed'>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  if (!result || !result.run_id) return null

  const isEmitted = result.writeback_status === 'emitted' || status === 'emitted'
  const validationPassed = result.validation?.passed !== false

  const handleApprove = async () => {
    if (!result.run_id) return
    setStatus('approving')
    setErrorMsg('')
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/runs/${result.run_id}/writeback/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: true, approved_by: 'Lead Data Engineer' })
      })

      const data = await res.json()
      if (res.ok && (data.status === 'success' || data.status === 'already_approved')) {
        setStatus('emitted')
        useWorkspaceStore.setState((state) => ({
          messages: state.messages.map(m => 
            m.result?.run_id === result.run_id 
              ? { ...m, result: { ...m.result!, writeback_status: 'emitted' } } 
              : m
          )
        }))
      } else {
        setStatus('failed')
        setErrorMsg(data.detail || 'Approval failed')
      }
    } catch (err: any) {
      setStatus('failed')
      setErrorMsg(err.message || 'Connection error')
    }
  }

  if (isEmitted) {
    return (
      <span className="px-2.5 py-1 rounded text-[10px] font-bold tracking-wider uppercase bg-success/20 text-success border border-success/30 flex items-center gap-1.5">
        <CheckCircle2 className="w-3 h-3 text-success" />
        DataHub MCP Emitted
      </span>
    )
  }

  if (!validationPassed) {
    return (
      <span className="px-2.5 py-1 rounded text-[10px] font-bold tracking-wider uppercase bg-danger/20 text-danger border border-danger/30 flex items-center gap-1.5" title="Validation failed. Fix blocking errors before approving.">
        <AlertTriangle className="w-3 h-3 text-danger" />
        Writeback Blocked
      </span>
    )
  }

  return (
    <button 
      onClick={handleApprove}
      disabled={status === 'approving'}
      className="px-2.5 py-1 rounded text-[10px] font-bold tracking-wider uppercase transition flex items-center gap-1.5 bg-primary/20 text-primary hover:bg-primary/40 border border-primary/40 cursor-pointer disabled:opacity-50"
    >
      {status === 'approving' ? <Loader2 className="w-3 h-3 animate-spin" /> : <GitCommit className="w-3 h-3" />}
      {status === 'approving' ? 'Emitting MCP...' : 'Approve DataHub Writeback'}
    </button>
  )
}
