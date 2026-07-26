'use client'

import React, { useState, useEffect } from 'react'
import { Server, Key, BrainCircuit, Save, CheckCircle2, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { API_BASE_URL } from '../../lib/api'

// ── Provider → Model catalogue ─────────────────────────────────────────────
const PROVIDER_MODELS: Record<string, { value: string; label: string }[]> = {
  openrouter: [
    { value: 'openai/gpt-4o',                          label: 'openai/gpt-4o' },
    { value: 'openai/gpt-4-turbo',                     label: 'openai/gpt-4-turbo' },
    { value: 'openai/gpt-3.5-turbo',                   label: 'openai/gpt-3.5-turbo' },
    { value: 'anthropic/claude-3-5-sonnet',            label: 'anthropic/claude-3-5-sonnet' },
    { value: 'anthropic/claude-3-opus',                label: 'anthropic/claude-3-opus' },
    { value: 'anthropic/claude-3-haiku',               label: 'anthropic/claude-3-haiku' },
    { value: 'meta-llama/llama-3.1-70b-instruct',      label: 'meta-llama/llama-3.1-70b' },
    { value: 'meta-llama/llama-3.1-8b-instruct',       label: 'meta-llama/llama-3.1-8b' },
    { value: 'google/gemini-pro-1.5',                  label: 'google/gemini-pro-1.5' },
    { value: 'mistralai/mistral-large',                label: 'mistralai/mistral-large' },
    { value: 'deepseek/deepseek-chat',                 label: 'deepseek/deepseek-chat' },
  ],
  openai: [
    { value: 'gpt-4o',        label: 'gpt-4o' },
    { value: 'gpt-4-turbo',   label: 'gpt-4-turbo' },
    { value: 'gpt-4',         label: 'gpt-4' },
    { value: 'gpt-3.5-turbo', label: 'gpt-3.5-turbo' },
  ],
  anthropic: [
    { value: 'claude-3-5-sonnet-20241022', label: 'claude-3.5-sonnet' },
    { value: 'claude-3-opus-20240229',     label: 'claude-3-opus' },
    { value: 'claude-3-haiku-20240307',    label: 'claude-3-haiku' },
  ],
  groq: [
    { value: 'llama-3.1-70b-versatile',   label: 'llama-3.1-70b (Groq)' },
    { value: 'llama-3.1-8b-instant',      label: 'llama-3.1-8b (Groq)' },
    { value: 'mixtral-8x7b-32768',        label: 'mixtral-8x7b (Groq)' },
    { value: 'gemma2-9b-it',              label: 'gemma2-9b (Groq)' },
  ],
  mistral: [
    { value: 'mistral-large-latest',  label: 'mistral-large' },
    { value: 'mistral-medium-latest', label: 'mistral-medium' },
    { value: 'mistral-small-latest',  label: 'mistral-small' },
    { value: 'open-mistral-7b',       label: 'open-mistral-7b' },
  ],
  deepseek: [
    { value: 'deepseek-chat',  label: 'deepseek-chat' },
    { value: 'deepseek-coder', label: 'deepseek-coder' },
  ],
  together: [
    { value: 'meta-llama/Llama-3-70b-chat-hf',  label: 'llama-3-70b (Together)' },
    { value: 'mistralai/Mixtral-8x7B-Instruct-v0.1', label: 'mixtral-8x7b (Together)' },
  ],
}

const PROVIDERS = [
  { value: 'openrouter', label: 'OpenRouter (Recommended — all models)' },
  { value: 'openai',     label: 'OpenAI (Direct)' },
  { value: 'anthropic',  label: 'Anthropic (Claude)' },
  { value: 'groq',       label: 'Groq (Fast inference)' },
  { value: 'mistral',    label: 'Mistral AI' },
  { value: 'deepseek',   label: 'DeepSeek' },
  { value: 'together',   label: 'Together AI' },
]

export default function SettingsPage() {
  const [gmsUrl, setGmsUrl]     = useState('http://localhost:8080')
  const [provider, setProvider] = useState('openrouter')
  const [model, setModel]       = useState('openai/gpt-4o')
  const [apiKey, setApiKey]     = useState('')
  const [loading, setLoading]   = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [error, setError]       = useState<string | null>(null)
  const [backendUrl, setBackendUrl] = useState(API_BASE_URL)

  // When provider changes, reset model to the first option for that provider
  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider)
    const models = PROVIDER_MODELS[newProvider] || PROVIDER_MODELS['openrouter']
    setModel(models[0].value)
  }

  const availableModels = PROVIDER_MODELS[provider] || PROVIDER_MODELS['openrouter']

  const fetchSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`)
      if (res.ok) {
        const data = await res.json()
        if (data.datahub_url)       setGmsUrl(data.datahub_url)
        if (data.llm_provider)      setProvider(data.llm_provider)
        if (data.llm_model)         setModel(data.llm_model)
        if (data.llm_api_key_masked) setApiKey(data.llm_api_key_masked)
      }
    } catch (err: any) {
      setError(`Unable to connect to backend: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchSettings() }, [])

  const handleSave = async () => {
    setIsSaving(true)
    setSaveStatus(null)
    setError(null)
    try {
      const body: Record<string, string> = {
        datahub_url:  gmsUrl,
        llm_provider: provider,
        llm_model:    model,
      }
      // Only send API key if it's not a masked placeholder
      if (apiKey && !apiKey.includes('...')) {
        body.llm_api_key = apiKey
      }

      const res = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)
      setSaveStatus('Configuration saved successfully!')
      setTimeout(() => setSaveStatus(null), 4000)
    } catch (err: any) {
      setError(`Failed to save: ${err.message}`)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-y-auto custom-scrollbar">
      <header className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-xl font-bold text-white tracking-wide mb-1 font-display">Configuration &amp; Settings</h1>
          <p className="text-sm text-gray-400 font-sans">Manage connections to DataHub metadata graph and AI reasoning engines.</p>
        </div>
        <div className="flex items-center gap-3">
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
          <button onClick={fetchSettings} disabled={loading} className="p-2 rounded-lg border border-surfaceBorder text-gray-400 hover:text-white transition" title="Reload Settings">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
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
            <div className="p-6">
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">GMS Endpoint URL</label>
              <input
                type="text"
                value={gmsUrl}
                onChange={(e) => setGmsUrl(e.target.value)}
                placeholder="http://localhost:8080"
                className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
              />
              <p className="text-[11px] text-gray-500 mt-2 font-sans">
                Synex queries this endpoint to fetch dataset schemas, PII tags, lineage, and to emit DataHub documentation MCP write-backs.
              </p>
            </div>
          </div>

          {/* LLM Config */}
          <div className="bg-surface border border-surfaceBorder rounded-xl shadow-lg overflow-hidden">
            <div className="p-4 border-b border-surfaceBorder bg-[#0A0E17] flex items-center gap-3">
              <BrainCircuit className="w-5 h-5 text-primary" />
              <h2 className="text-xs font-bold tracking-widest uppercase text-white font-mono">AI Reasoning Engine</h2>
            </div>
            <div className="p-6 space-y-5">

              {/* Provider + Model row */}
              <div className="grid grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    {PROVIDERS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">
                    Model <span className="text-gray-600 normal-case font-normal">({availableModels.length} available)</span>
                  </label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    {availableModels.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* API Key */}
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 font-sans">Provider API Key</label>
                <div className="relative">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={provider === 'openrouter' ? 'sk-or-v1-...' : provider === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-primary transition font-mono pr-10"
                  />
                  <Key className="w-4 h-4 text-gray-500 absolute right-4 top-3" />
                </div>
                <p className="text-[11px] text-gray-500 mt-2 font-sans">
                  Leave unchanged to keep the existing saved key (shown masked). Only enter a new key to update it.
                  Keys are stored server-side and never returned to the browser.
                </p>
              </div>

              {/* Provider-specific help links */}
              <div className="text-[11px] text-gray-600 font-sans">
                {provider === 'openrouter' && <span>Get your key at <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">openrouter.ai/keys</a> — one key, all models.</span>}
                {provider === 'openai'     && <span>Get your key at <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">platform.openai.com/api-keys</a>.</span>}
                {provider === 'anthropic'  && <span>Get your key at <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">console.anthropic.com</a>.</span>}
                {provider === 'groq'       && <span>Get your key at <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">console.groq.com/keys</a>.</span>}
                {provider === 'mistral'    && <span>Get your key at <a href="https://console.mistral.ai/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">console.mistral.ai</a>.</span>}
                {provider === 'deepseek'   && <span>Get your key at <a href="https://platform.deepseek.com" target="_blank" rel="noopener noreferrer" className="text-primary underline">platform.deepseek.com</a>.</span>}
                {provider === 'together'   && <span>Get your key at <a href="https://api.together.xyz/settings/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">api.together.xyz</a>.</span>}
              </div>
            </div>
          </div>

          {/* Save */}
          <div className="pt-2 flex justify-start">
            <button
              onClick={handleSave}
              disabled={isSaving || loading}
              className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-8 py-3.5 rounded-xl shadow-lg transition flex items-center gap-2 disabled:opacity-50 font-sans cursor-pointer"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {isSaving ? 'Saving...' : 'Save Configuration'}
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
                {loading ? 'CHECKING' : error ? 'OFFLINE' : 'ONLINE'}
              </span>
            </div>
            <div className="space-y-2 text-xs font-sans">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Endpoint:</span>
                <span className="text-gray-200 font-mono text-[11px] break-all">{API_BASE_URL}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Provider:</span>
                <span className="text-gray-200 font-mono">{provider}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Model:</span>
                <span className="text-gray-200 font-mono text-[11px] break-all">{model}</span>
              </div>
            </div>
          </div>

          <div className="bg-[#0A0E17] border border-surfaceBorder rounded-xl p-5 space-y-3">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest font-mono">Active Configuration</h3>
            <div className="space-y-2 text-xs font-sans">
              <div className="flex justify-between">
                <span className="text-gray-500">DataHub GMS</span>
                <span className="text-gray-300 font-mono text-[11px] max-w-[60%] text-right break-all">{gmsUrl || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">API Key</span>
                <span className="text-gray-300 font-mono">{apiKey ? '••••••••' : 'Not set'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Storage</span>
                <span className="text-gray-300 font-sans">Supabase DB + Env</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
