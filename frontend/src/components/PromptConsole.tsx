'use client'

import React, { useState } from 'react'
import { Send, ArrowUp } from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'
import { API_BASE_URL } from '../lib/api'

export const PromptConsole: React.FC = () => {
    const { prompt, setPrompt, addMessage, updateAgentMessage, setSelectedMetadata, activeSessionId, setActiveSessionId } = useWorkspaceStore()
    const [loading, setLoading] = useState(false)
    const model = 'openai/gpt-4o'

    const handleSend = async (e?: React.FormEvent) => {
      if (e) e.preventDefault()
      if (!prompt.trim() || loading) return

      const userPrompt = prompt.trim()
      setPrompt('')
      setLoading(true)

      let currentSession = activeSessionId
      if (!currentSession) {
        // Generate a random UUID-like session identifier
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

      // 2. Add Pending Agent Message with initial trace step
      addMessage({
        id: agentMsgId,
        sender: 'agent',
        text: 'Initializing Synex AI Engine...',
        timestamp: now(),
        status: 'RUNNING',
        steps: [
          { step: 1, type: 'INFO', message: `[${now()}] INFO: Connecting to Synex Backend Engine...` }
        ]
      })

      // Helper to push trace logs
      const pushStep = (stepNum: number, type: string, text: string) => {
        useWorkspaceStore.setState((state) => ({
          messages: state.messages.map(m => 
            m.id === agentMsgId 
              ? { ...m, steps: [...(m.steps || []), { step: stepNum, type, message: `[${now()}] ${type}: ${text}` }] } 
              : m
          )
        }))
      }

      try {
        // Make backend API request to FastAPI engine
        const response = await fetch(`${API_BASE_URL}/api/v1/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            prompt: userPrompt,
            session_id: currentSession
          }),
        })

      if (!response.ok) {
        const errDetail = await response.text()
        throw new Error(`Server error (${response.status}): ${errDetail || response.statusText}`)
      }

      const data = await response.json()

      // Format steps from backend trace_logs or construct step objects
      const serverSteps = (data.trace_logs || []).map((t: any, idx: number) => ({
        step: t.step || idx + 1,
        type: t.type || 'INFO',
        message: t.message ? `[${now()}] ${t.type || 'INFO'}: ${t.message}` : `[${now()}] INFO: Step ${idx + 1}`
      }))

      updateAgentMessage(agentMsgId, {
        status: 'SUCCESS',
        text: `Execution completed. Synthesized dbt model for ${data.target_name || data.target_urn || 'target dataset'}.`,
        steps: serverSteps.length > 0 ? serverSteps : [
          { step: 1, type: 'INFO', message: `[${now()}] INFO: Execution finished.` },
          { step: 2, type: 'SUCCESS', message: `[${now()}] SUCCESS: Generated model for ${data.target_name || 'dataset'}.` }
        ],
        result: {
          target_urn: data.target_urn || '',
          target_name: data.target_name || '',
          dataset_description: data.dataset_description || '',
          pii_columns: data.pii_columns || [],
          schema_fields: data.schema_fields || [],
          sql: data.sql || '-- No SQL generated',
          dbt_yaml: data.dbt_yaml || ''
        }
      })

      if (data.target_urn) {
        setSelectedMetadata(
          data.target_urn,
          data.pii_columns || [],
          data.schema_fields || [],
          data.target_name || '',
          data.dataset_description || ''
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

  const { messages } = useWorkspaceStore()
  const totalChars = messages.reduce((acc, m) => acc + m.text.length + (m.result?.sql?.length || 0), 0)
  const estimatedTokens = Math.round(totalChars / 4)
  const formattedTokens = estimatedTokens > 1000 ? `${(estimatedTokens / 1000).toFixed(1)}k` : `${estimatedTokens}`

  return (
    <div className="w-full max-w-4xl mx-auto group space-y-2">
      <form onSubmit={handleSend} className="bg-surface border border-surfaceBorder rounded-2xl p-2 flex items-center gap-3 shadow-[0_10px_30px_rgba(0,0,0,0.5)] transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/40 focus-within:border-primary/50">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={loading ? "Synex Agent is executing..." : "Instruct Synex to model datasets or trace lineage..."}
          disabled={loading}
          className="flex-1 bg-transparent border-none text-base text-gray-100 placeholder-gray-500 focus:outline-none px-4 py-2.5 font-sans"
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="h-10 w-10 rounded-xl bg-primary hover:bg-primaryHover text-white flex items-center justify-center transition-all duration-200 disabled:opacity-40 disabled:hover:bg-primary shrink-0 shadow-lg group-focus-within:shadow-primary/20 motion-reduce:transition-none outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-surface focus-visible:ring-primary"
        >
          <ArrowUp className="w-5 h-5 stroke-[2.5px]" />
        </button>
      </form>

      {/* Token Context Capacity Gauge */}
      <div className="flex items-center justify-between px-3 text-[11px] font-mono text-gray-500">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-accent" />
          <span>LLM Context: <strong className="text-gray-300 font-semibold">{formattedTokens} / 128k</strong> tokens</span>
        </div>
        <span className="text-gray-600">OpenRouter · {model}</span>
      </div>
    </div>
  )
}
