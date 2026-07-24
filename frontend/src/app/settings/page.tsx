'use client'

import React, { useState, useEffect } from 'react'
import { Server, Key, BrainCircuit, Save, ShieldAlert, CheckCircle2, Loader2, AlertCircle } from 'lucide-react'

export default function SettingsPage() {
  const [gmsUrl, setGmsUrl] = useState('http://localhost:8080')
  const [snowflakeAccount, setSnowflakeAccount] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('http://localhost:8000/api/v1/settings')
      if (res.ok) {
        const data = await res.json()
        if (data.datahub_gms_url) setGmsUrl(data.datahub_gms_url)
        if (data.snowflake_account) setSnowflakeAccount(data.snowflake_account)
        if (data.openai_api_key_masked) setApiKey(data.openai_api_key_masked)
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
      const res = await fetch('http://localhost:8000/api/v1/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          datahub_gms_url: gmsUrl,
          snowflake_account: snowflakeAccount,
          openai_api_key: apiKey.startsWith('sk-...') ? undefined : apiKey
        })
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText || `HTTP ${res.status}`)
      }

      setSaveStatus('Configuration saved to Supabase successfully!')
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
          <h1 className="text-xl font-bold text-white tracking-wide mb-1">Configuration & Settings</h1>
          <p className="text-sm text-gray-400">Manage connections to DataHub GMS, Supabase, and LLM providers.</p>
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
              <h2 className="text-sm font-bold tracking-widest uppercase text-white">DataHub GMS Connection</h2>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">GMS Endpoint URL</label>
                <input 
                  type="text" 
                  value={gmsUrl}
                  onChange={(e) => setGmsUrl(e.target.value)}
                  placeholder="http://localhost:8080"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Snowflake Account Identifier</label>
                <input 
                  type="text" 
                  value={snowflakeAccount}
                  onChange={(e) => setSnowflakeAccount(e.target.value)}
                  placeholder="xy12345.us-east-1"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition font-mono"
                />
              </div>
            </div>
          </div>

          {/* LLM Config */}
          <div className="bg-surface border border-surfaceBorder rounded-xl shadow-lg overflow-hidden">
            <div className="p-4 border-b border-surfaceBorder bg-[#0A0E17] flex items-center gap-3">
              <BrainCircuit className="w-5 h-5 text-[#C678DD]" />
              <h2 className="text-sm font-bold tracking-widest uppercase text-white">LLM Provider Config</h2>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">OpenAI / Provider API Key</label>
                <div className="relative">
                  <input 
                    type="password" 
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-proj-..."
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition font-mono"
                  />
                  <Key className="w-4 h-4 text-gray-500 absolute right-4 top-3" />
                </div>
                <p className="text-[10px] text-gray-500 mt-2">API Keys are encrypted and stored in Supabase synex_settings.</p>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button 
              onClick={handleSave}
              disabled={isSaving || loading}
              className="bg-primary hover:bg-primaryHover text-white font-bold text-sm tracking-widest uppercase px-8 py-3 rounded shadow-lg transition flex items-center gap-2 disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {isSaving ? 'Saving to Supabase...' : 'Save Configuration'}
            </button>
          </div>

        </div>

        {/* Right Column: Diagnostics */}
        <div className="col-span-4 space-y-6">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">System Diagnostics</h2>
          
          <div className="bg-[#0A0E17] border border-surfaceBorder rounded-lg p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-accent" />
                <span className="font-bold text-sm text-white">FastAPI Engine</span>
              </div>
              <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${error ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'}`}>
                <CheckCircle2 className="w-3 h-3" /> {error ? 'OFFLINE' : 'CONNECTED'}
              </div>
            </div>
            <div className="space-y-2 text-xs font-mono text-gray-400">
              <div className="flex justify-between"><span className="text-gray-500">Host:</span> <span className="text-white">localhost:8000</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Status:</span> <span className="text-white">{error ? 'Error' : '200 OK'}</span></div>
            </div>
          </div>

          <div className="bg-[#0A0E17] border border-surfaceBorder rounded-lg p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-accent" />
                <span className="font-bold text-sm text-white">Supabase Storage</span>
              </div>
              <div className="flex items-center gap-1 bg-success/10 text-success px-2 py-0.5 rounded text-[10px] font-bold">
                <CheckCircle2 className="w-3 h-3" /> ACTIVE
              </div>
            </div>
            <div className="space-y-2 text-xs font-mono text-gray-400">
              <div className="flex justify-between"><span className="text-gray-500">Tables:</span> <span className="text-white">synex_runs, synex_settings</span></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
