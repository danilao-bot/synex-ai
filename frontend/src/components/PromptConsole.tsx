'use client'

import React, { useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL } from '../lib/api'

export const PromptConsole: React.FC = () => {
    const { prompt, setPrompt, addMessage, updateAgentMessage, setSelectedMetadata, activeSessionId, setActiveSessionId } = useWorkspaceStore()
    const [loading, setLoading] = useState(false)
    const [dialect, setDialect] = useState('snowflake')
    const model = 'openai/gpt-4o'

    const handleSend = async (e?: React.FormEvent) => {
      if (e) e.preventDefault()
      if (!prompt.trim() || loading) return

      const userPrompt = prompt.trim()
      setPrompt('')
      setLoading(true)

      let currentSession = activeSessionId
      if (!currentSession) {
        currentSession = 'session-' + Date.now()
        setActiveSessionId(currentSession)
      }

      const now = () => new Date().toLocaleTimeString('en-US', { hour12: false })
      const userMsgId = 'user-' + Date.now()
      const agentMsgId = 'agent-' + Date.now()

      // 1. Add User Message
      addMessage({
        id: userMsgId,
        sender: 'user',
        text: userPrompt,
        timestamp: now()
      })

      // 2. Add Pending Agent Message
      addMessage({
        id: agentMsgId,
        sender: 'agent',
        text: 'Querying DataHub MCP catalog & evaluating governance graph...',
        timestamp: now(),
        status: 'RUNNING',
        steps: [
          { step: 1, type: 'MCP_DISCOVERY', message: `[${now()}] MCP_DISCOVERY: Connecting to DataHub MCP Server...` }
        ]
      })

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            prompt: userPrompt,
            target_dialect: dialect,
            writeback_enabled: false,
            session_id: currentSession
          }),
        })

        if (!response.ok) {
          const errDetail = await response.text()
          throw new Error(`Server error (${response.status}): ${errDetail || response.statusText}`)
        }

        const data = await response.json()

        const serverSteps = (data.trace_logs || []).map((t: any, idx: number) => ({
          step: t.step || idx + 1,
          type: t.type || 'INFO',
          message: t.message ? `[${now()}] ${t.type || 'INFO'}: ${t.message}` : `[${now()}] INFO: Step ${idx + 1}`
        }))

        const selCandidate = data.selected_dataset || {}
        const artifacts = data.artifacts || {}
        const bundle = artifacts.artifact_bundle || {}

        updateAgentMessage(agentMsgId, {
          status: 'SUCCESS',
          text: `Selected canonical dataset '${selCandidate.name || data.target_urn || 'target'}' (Trust Score: ${selCandidate.trust_score || 0}/100). Synthesized governed dbt model & schema contract.`,
          steps: serverSteps,
          result: {
            run_id: data.run_id,
            target_urn: selCandidate.urn || data.target_urn || '',
            target_name: selCandidate.name || data.target_name || '',
            dataset_description: selCandidate.description || '',
            pii_columns: data.governance?.pii_fields || selCandidate.pii_fields || [],
            schema_fields: data.schema_fields || [],
            sql: artifacts.sql || '-- No SQL generated',
            dbt_yaml: artifacts.dbt_yaml || '',
            dbt_tests: artifacts.dbt_tests || [],
            change_summary_markdown: bundle.change_summary_markdown || '',
            git_patch: bundle.git_patch || '',
            selected_dataset: selCandidate,
            candidate_datasets: data.candidate_datasets || [],
            validation: data.validation,
            proposed_writeback: data.proposed_writeback,
            writeback_status: 'pending_approval'
          }
        })

        if (selCandidate.urn || data.target_urn) {
          setSelectedMetadata(
            selCandidate.urn || data.target_urn,
            data.governance?.pii_fields || selCandidate.pii_fields || [],
            data.schema_fields || [],
            selCandidate.name || data.target_name || '',
            selCandidate.description || '',
            selCandidate
          )
        }

      } catch (err: any) {
        updateAgentMessage(agentMsgId, {
          status: 'FAILED',
          text: `Execution Error: ${err.message}`,
          steps: [
            { step: 1, type: 'ERROR', message: `[${now()}] ERROR: ${err.message}` }
          ]
        })
      } finally {
        setLoading(false)
      }
    }

  return (
    <div className="w-full max-w-4xl mx-auto group space-y-2">
      <form onSubmit={handleSend} className="bg-surface border border-surfaceBorder rounded-2xl p-2 flex items-center gap-3 shadow-[0_10px_30px_rgba(0,0,0,0.5)] transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/40 focus-within:border-primary/50">
        
        {/* Dialect Selector */}
        <select 
          value={dialect}
          onChange={(e) => setDialect(e.target.value)}
          disabled={loading}
          className="bg-[#080C16] text-xs font-mono text-accent border border-surfaceBorder rounded-xl px-3 py-2 focus:outline-none cursor-pointer hover:border-accent/50 transition"
        >
          <option value="snowflake">Snowflake</option>
          <option value="postgres">PostgreSQL</option>
          <option value="bigquery">BigQuery</option>
          <option value="databricks">Databricks</option>
        </select>

        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={loading ? "Synex Agent is evaluating DataHub metadata graph..." : "Ask Synex (e.g. 'Create a PII-safe revenue model for Finance')..."}
          disabled={loading}
          className="flex-1 bg-transparent border-none text-base text-gray-100 placeholder-gray-500 focus:outline-none px-2 py-2.5 font-sans"
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="h-10 w-10 rounded-xl bg-primary hover:bg-primaryHover text-white flex items-center justify-center transition-all duration-200 disabled:opacity-40 disabled:hover:bg-primary shrink-0 shadow-lg outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <ArrowUp className="w-5 h-5 stroke-[2.5px]" />
        </button>
      </form>

      {/* Token & DataHub MCP Context Gauge */}
      <div className="flex items-center justify-between px-3 text-[11px] font-mono text-gray-500">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
          <span>DataHub MCP Adapter: <strong className="text-gray-300 font-semibold">Active</strong></span>
        </div>
        <span className="text-gray-600">LLM Engine · {model}</span>
      </div>
    </div>
  )
}
