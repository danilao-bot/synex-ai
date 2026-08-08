'use client'

import React, { useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL, fetchWithAuth, getAuthToken } from '../lib/api'

function applyCompletedPayload(agentMsgId: string, data: any, now: () => string) {
  const { updateAgentMessage, setSelectedMetadata } = useWorkspaceStore.getState()
  const selCandidate = data.selected_dataset || {}
  const artifacts = data.artifacts || {}
  const bundle = artifacts.artifact_bundle || {}
  const workflowSteps = data.workflow_steps || []

  const serverSteps = (data.trace_logs || workflowSteps || []).map((t: any, idx: number) => ({
    step: t.step || idx + 1,
    type: t.type || t.stage || 'WORKFLOW',
    message: t.message
      ? `[${now()}] ${t.type || t.stage_label || 'STEP'}: ${t.message}`
      : `[${now()}] STEP ${idx + 1}`,
    status: t.status,
    duration_ms: t.duration_ms,
    stage: t.stage || t.id,
    stage_label: t.stage_label || t.label,
    reasoning_summary: t.reasoning_summary,
    trust_score: t.trust_score,
    warnings: t.warnings,
  }))

  if (data.status === 'NEEDS_CLARIFICATION') {
    const qs = (data.clarifying_questions || []).map((q: string, i: number) => `${i + 1}. ${q}`).join('\n')
    updateAgentMessage(agentMsgId, {
      status: 'SUCCESS',
      text: `I need a bit more detail before generating SQL:\n${qs}`,
      steps: serverSteps,
      workflowSteps,
      clarifyingQuestions: data.clarifying_questions || [],
      result: undefined,
    })
    return
  }

  updateAgentMessage(agentMsgId, {
    status: data.status === 'FAILED' ? 'FAILED' : 'SUCCESS',
    text:
      data.status === 'FAILED'
        ? 'Workflow failed — see timeline for details.'
        : `Selected '${selCandidate.name || 'target'}' (Trust ${selCandidate.trust_score || 0}/100). Engineering workflow complete — review plan, artifacts, and approve write-back.`,
    steps: serverSteps,
    workflowSteps,
    plan: data.plan || [],
    result: {
      run_id: data.run_id,
      target_urn: selCandidate.urn || data.target_urn || '',
      target_name: selCandidate.name || data.target_name || '',
      dataset_description: selCandidate.description || '',
      pii_columns: data.governance?.pii_fields || selCandidate.pii_fields || [],
      schema_fields: data.schema_fields || data.enriched_context?.schema_fields || [],
      sql: artifacts.sql || '-- No SQL generated',
      dbt_yaml: artifacts.dbt_yaml || '',
      dbt_tests: artifacts.dbt_tests || [],
      change_summary_markdown: bundle.change_summary_markdown || '',
      git_patch: bundle.git_patch || '',
      selected_dataset: selCandidate,
      candidate_datasets: data.candidate_datasets || [],
      validation: data.validation,
      proposed_writeback: data.proposed_writeback,
      writeback_status: 'pending_approval',
      enriched_context: data.enriched_context,
      engineering_context: data.engineering_context,
      context_package: data.context_package,
      context_manifest: data.context_manifest,
      sql_explanation: data.sql_explanation || data.artifacts?.sql_explanation,
      confidence: data.confidence,
      self_critique: data.self_critique,
      observability: data.observability,
      metadata_source: data.metadata_source,
      lineage_impact: data.lineage_impact,
      quality_report: data.quality_report,
      plan: data.plan,
    } as any,
  })

  if (selCandidate.urn || data.target_urn) {
    setSelectedMetadata(
      selCandidate.urn || data.target_urn,
      data.governance?.pii_fields || selCandidate.pii_fields || [],
      data.schema_fields || data.enriched_context?.schema_fields || [],
      selCandidate.name || data.target_name || '',
      data.enriched_context?.description || selCandidate.description || '',
      selCandidate
    )
  }
}

export const PromptConsole: React.FC = () => {
  const { prompt, setPrompt, addMessage, updateAgentMessage, activeSessionId, setActiveSessionId } = useWorkspaceStore()
  const [loading, setLoading] = useState(false)
  const [dialect, setDialect] = useState('snowflake')

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

    addMessage({
      id: userMsgId,
      sender: 'user',
      text: userPrompt,
      timestamp: now(),
    })

    addMessage({
      id: agentMsgId,
      sender: 'agent',
      text: 'Starting autonomous Data Engineering workflow…',
      timestamp: now(),
      status: 'RUNNING',
      steps: [],
      workflowSteps: [],
      result: {
        target_urn: '',
        target_name: 'selected',
        dataset_description: '',
        pii_columns: [],
        schema_fields: [],
        sql: '',
        dbt_yaml: '',
      }
    })

    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userPrompt,
          target_dialect: dialect,
          writeback_enabled: false,
          session_id: currentSession,
        }),
      })

      if (!response.ok || !response.body) {
        // Fallback to JSON endpoint if SSE unavailable
        const fallback = await fetchWithAuth(`${API_BASE_URL}/api/v1/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: userPrompt,
            target_dialect: dialect,
            writeback_enabled: false,
            session_id: currentSession,
          }),
        })
        if (!fallback.ok) {
          const errDetail = await fallback.text()
          throw new Error(`Server error (${fallback.status}): ${errDetail || fallback.statusText}`)
        }
        const data = await fallback.json()
        applyCompletedPayload(agentMsgId, data, now)
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const liveSteps: any[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''

        for (const chunk of chunks) {
          const line = chunk.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue
          let event: any
          try {
            event = JSON.parse(line.slice(6))
          } catch {
            continue
          }

          if (event.type === 'ERROR') {
            throw new Error(event.message || 'Workflow stream error')
          }

          if (event.type === 'COMPLETED' && event.payload) {
            applyCompletedPayload(agentMsgId, event.payload, now)
            continue
          }

          if (event.type === 'SQL_TOKEN') {
            const currentMsgs = useWorkspaceStore.getState().messages
            const index = currentMsgs.findIndex(m => m.id === agentMsgId)
            if (index !== -1) {
              const currentMsg = currentMsgs[index]
              const currentSql = currentMsg.result?.sql || ''
              updateAgentMessage(agentMsgId, {
                text: 'Streaming dbt SQL model live…',
                status: 'RUNNING',
                result: {
                  ...(currentMsg.result || {}),
                  sql: currentSql + event.message
                } as any
              })
            }
            continue
          }

          // Live workflow stage event
          const stepView = event.workflow_step || {
            id: event.stage || event.type,
            label: event.stage_label || event.stage || event.type,
            status: event.status,
            message: event.message,
            duration_ms: event.duration_ms,
            reasoning_summary: event.reasoning_summary,
            trust_score: event.trust_score ?? event.confidence,
            warnings: event.warnings,
          }

          const idx = liveSteps.findIndex((s) => (s.id || s.name) === (stepView.id || stepView.name))
          if (idx >= 0) {
            stepView.time = liveSteps[idx].time || now()
            liveSteps[idx] = stepView
          } else {
            stepView.time = now()
            liveSteps.push(stepView)
          }

          updateAgentMessage(agentMsgId, {
            text: event.message || 'Workflow running…',
            status: 'RUNNING',
            workflowSteps: [...liveSteps],
            steps: liveSteps.map((s, i) => ({
              step: i + 1,
              type: `WORKFLOW_${(s.id || 'step').toUpperCase()}`,
              message: `[${s.time || now()}] ${s.label || s.id}: ${s.message || s.status}`,
              status: s.status,
              duration_ms: s.duration_ms,
              stage: s.id,
              stage_label: s.label,
              time: s.time || now()
            })),
          })
        }
      }
    } catch (err: any) {
      updateAgentMessage(agentMsgId, {
        status: 'FAILED',
        text: `Execution Error: ${err.message}`,
        steps: [{ step: 1, type: 'ERROR', message: `[${now()}] ERROR: ${err.message}` }],
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto space-y-2">
      <form
        onSubmit={handleSend}
        className="bg-[#0D1527] border border-surfaceBorder rounded-2xl p-2 flex items-end gap-2 shadow-[0_10px_30px_rgba(0,0,0,0.5)] transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/40 focus-within:border-primary/50"
      >
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder={
            loading
              ? 'Workflow engine running…'
              : "Ask Synex — e.g. 'Create a PII-safe revenue model for Finance'..."
          }
          disabled={loading}
          className="flex-1 bg-transparent border-none text-[14px] text-gray-100 placeholder-gray-600 focus:outline-none px-3 py-2.5 font-sans resize-none leading-relaxed"
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="h-9 w-9 rounded-xl bg-primary hover:bg-primaryHover text-white flex items-center justify-center transition-all duration-200 disabled:opacity-30 disabled:hover:bg-primary shrink-0 shadow-lg"
        >
          {loading
            ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            : <ArrowUp className="w-4 h-4 stroke-[2.5px]" />
          }
        </button>
      </form>

      <div className="flex items-center justify-between px-3">
        <div className="flex items-center gap-2">
          <select
            value={dialect}
            onChange={(e) => setDialect(e.target.value)}
            disabled={loading}
            className="bg-transparent text-[11px] font-mono text-gray-500 border-none focus:outline-none cursor-pointer hover:text-gray-300 transition"
          >
            <option value="snowflake">Snowflake</option>
            <option value="postgres">PostgreSQL</option>
            <option value="bigquery">BigQuery</option>
            <option value="databricks">Databricks</option>
          </select>
        </div>
        <span className="text-[10px] font-mono text-gray-600">Shift+Enter for newline · Enter to send</span>
      </div>
    </div>
  )
}
