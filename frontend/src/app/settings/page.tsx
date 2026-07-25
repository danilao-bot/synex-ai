'use client'

import React, { useState, useEffect } from 'react'
import { Server, Key, BrainCircuit, Save, CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { API_BASE_URL } from '../../lib/api'

export default function SettingsPage() {
  const [gmsUrl, setGmsUrl] = useState('http://localhost:8080')
  const [snowflakeAccount, setSnowflakeAccount] = useState('')
  const [provider, setProvider] = useState('OpenAI')
  const [model, setModel] = useState('gpt-4o')
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`)
      if (res.ok) {
        const data = await res.json()
        if (data.datahub_url) setGmsUrl(data.datahub_url)
        if (data.llm_provider) setProvider(data.llm_provider)
        if (data.llm_model) setModel(data.llm_model)
        if (data.llm_api_key_masked) setApiKey(data.llm_api_key_masked)
      }
    } catch (err: any) {
      setError(`Unable to connect to backend engine: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  const handleSave = async () => {
    setIsSaving(true)
    setSaveStatus(null)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          datahub_url: gmsUrl,
          llm_provider: provider,
          llm_model: model,
          llm_api_key: apiKey.includes('...') ? undefined : apiKey
        })
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || `HTTP ${res.status}`)
      }

      setSaveStatus('Configuration saved successfully!')
      setTimeout(() => setSaveStatus(null), 4000)
    } catch (err: any) {
      setError(`Failed to save configuration: ${err.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-y-auto custom-scrollbar">
      <header className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold text-white tracking-wide mb-1 font-display">Configuration & Settings</h1>
          <p className="text-sm text-gray-400 font-sans">Manage connections to DataHub metadata graph and AI reasoning engines.</p>
        </div>
        {saveStatus && (
          <div className="flex items-center gap-2 bg-success/10 border border-success/30 text-success px-4 py-2 rounded text-xs font-semibold animate-fadeIn">
            <CheckCircle2 className="w-4 h-4" /> {saveStatus}
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 bg-danger/10 border border-danger/30 text-danger px-4 py-2 rounded text-xs font-semibold animate-fadeIn">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}
      </header>

      <div className="grid grid-cols-12 gap-8">
        {/* Left Column: Forms */}
        <div className="col-span-8 space-y-8">
          
          {/* DataHub Config */}
          <div className="bg-surface border border-surfaceBorder rounded-xl shadow-lg overflow-hidden">
            <div className="p-4 border-b border-surfaceBorder bg-[#0A0E17] flex items-center gap-3">
              <Server className="w-5 h-5 text-accent" />
              <h2 className="text-xs font-bold tracking-widest uppercase text-white font-mono">DataHub GMS Connection</h2>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">GMS Endpoint URL</label>
                <input 
                  type="text" 
                  value={gmsUrl}
                  onChange={(e) => setGmsUrl(e.target.value)}
                  placeholder="http://localhost:8080"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Snowflake Account Identifier</label>
                <input 
                  type="text" 
                  value={snowflakeAccount}
                  onChange={(e) => setSnowflakeAccount(e.target.value)}
                  placeholder="xy12345.us-east-1"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                />
              </div>
            </div>
          </div>

          {/* LLM Config */}
          <div className="bg-surface border border-surfaceBorder rounded-xl shadow-lg overflow-hidden">
            <div className="p-4 border-b border-surfaceBorder bg-[#0A0E17] flex items-center gap-3">
              <BrainCircuit className="w-5 h-5 text-primary" />
              <h2 className="text-xs font-bold tracking-widest uppercase text-white font-mono">AI Reasoning Engine</h2>
            </div>
            <div className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Provider</label>
                  <select 
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    <option value="openrouter">OpenRouter (Recommended)</option>
                    <option value="openai">OpenAI (Direct)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Model</label>
                  <select 
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    <option value="openai/gpt-4o">openai/gpt-4o</option>
                    <option value="openai/gpt-4-turbo">openai/gpt-4-turbo</option>
                    <option value="anthropic/claude-3-5-sonnet">anthropic/claude-3-5-sonnet</option>
                    <option value="meta-llama/llama-3.1-70b-instruct">meta-llama/llama-3.1-70b</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Provider API Key</label>
                <div className="relative">
                  <input 
                    type="password" 
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-proj-..."
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                  />
                  <Key className="w-4 h-4 text-gray-500 absolute right-4 top-3" />
                </div>
                <p className="text-[11px] text-gray-500 mt-2 font-sans">API keys are stored as server-side environment variables and never exposed to the browser.</p>
              </div>
            </div>
          </div>

          {/* Save Action */}
          <div className="pt-2 flex justify-start">
            <button 
              onClick={handleSave}
              disabled={isSaving || loading}
              className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-8 py-3.5 rounded-xl shadow-lg transition flex items-center gap-2 disabled:opacity-50 font-sans cursor-pointer"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {isSaving ? 'Saving Configuration...' : 'Save Configuration'}
            </button>
          </div>

        </div>

        {/* Right Column: Diagnostics */}
        <div className="col-span-4 space-y-6">
          <h2 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2 font-mono">SYSTEM DIAGNOSTICS</h2>
          
          <div className="bg-[#0A0E17] border border-surfaceBorder rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center border-b border-surfaceBorder/50 pb-3">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-accent" />
                <span className="font-bold text-sm text-white font-sans">FastAPI Engine</span>
              </div>
              <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold font-mono ${error ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'}`}>
                {error ? 'OFFLINE' : 'ONLINE'}
              </span>
            </div>
            <div className="space-y-2 text-xs font-sans">
              <div className="flex items-center gap-2"><span className="text-gray-500 font-sans">Host:</span> <span className="text-gray-200 font-mono">localhost:8000</span></div>
              <div className="flex items-center gap-2"><span className="text-gray-500 font-sans">Status:</span> <span className="text-gray-200 font-mono">{error ? 'Disconnected' : '200 OK'}</span></div>
            </div>
          </div>

          <div className="bg-[#0A0E17] border border-surfaceBorder rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center border-b border-surfaceBorder/50 pb-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-primary" />
                <span className="font-bold text-sm text-white font-sans">Metadata Vault</span>
              </div>
              <span className="bg-success/10 text-success px-2.5 py-0.5 rounded text-[10px] font-bold font-mono">
                OPERATIONAL
              </span>
            </div>
            <div className="space-y-2 text-xs font-sans">
              <div className="flex items-center gap-2"><span className="text-gray-500 font-sans">Storage:</span> <span className="text-gray-200 font-sans">Server-Side Env Vars</span></div>
              <div className="flex items-center gap-2"><span className="text-gray-500 font-sans">Sync:</span> <span className="text-gray-200 font-sans">Real-Time Audit Log</span></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
