'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Server, BrainCircuit, CheckCircle2, ArrowRight, ArrowLeft, Key, ShieldCheck, Database, Sparkles, Loader2, AlertCircle } from 'lucide-react'
import { API_BASE_URL } from '../../lib/api'

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)

  // Form State
  const [gmsUrl, setGmsUrl] = useState('http://localhost:8080')
  const [snowflakeAccount, setSnowflakeAccount] = useState('')
  const [provider, setProvider] = useState('OpenAI')
  const [model, setModel] = useState('gpt-4o')
  const [apiKey, setApiKey] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFinish = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          datahub_gms_url: gmsUrl,
          snowflake_account: snowflakeAccount,
          llm_provider: provider,
          llm_model: model,
          openai_api_key: apiKey
        })
      })

      if (!res.ok) {
        throw new Error(`Failed to save settings (${res.status})`)
      }

      router.push('/')
    } catch (err: any) {
      setError(`Setup Error: ${err.message}`)
      setIsSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#04060C] flex flex-col items-center justify-center p-6 text-gray-100 relative overflow-hidden isolate">
      {/* Background Ambient Glows */}
      <div className="absolute w-[500px] h-[500px] bg-primary/10 rounded-full blur-3xl pointer-events-none -top-40 -left-40 animate-pulse" />
      <div className="absolute w-[500px] h-[500px] bg-accent/10 rounded-full blur-3xl pointer-events-none -bottom-40 -right-40 animate-pulse" />

      {/* Main Container */}
      <div className="w-full max-w-2xl bg-surface border border-surfaceBorder rounded-2xl shadow-2xl p-8 relative z-10 space-y-8">
        
        {/* Header Progress Indicators */}
        <div className="flex items-center justify-between border-b border-surfaceBorder pb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-primary/20 border border-primary flex items-center justify-center text-primary font-bold">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold font-display text-white">Synex Agent Setup</h1>
              <p className="text-xs text-gray-400 font-sans">Step {step} of 3</p>
            </div>
          </div>

          {/* Stepper Dots */}
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((s) => (
              <div 
                key={s} 
                className={`h-2 rounded-full transition-all duration-300 ${
                  s === step ? 'w-8 bg-primary' : s < step ? 'w-2 bg-success' : 'w-2 bg-surfaceBorder'
                }`}
              />
            ))}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-3 bg-danger/10 border border-danger/30 text-danger p-4 rounded-xl text-xs font-semibold">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: WELCOME INTRO */}
        {step === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="text-center py-6 space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-primary/20 border border-primary/40 flex items-center justify-center text-primary mx-auto shadow-lg">
                <Sparkles className="w-8 h-8" />
              </div>
              <h2 className="text-2xl font-bold font-display text-white">Welcome to Synex</h2>
              <p className="text-sm text-gray-400 font-sans max-w-md mx-auto leading-relaxed">
                Connect your DataHub metadata catalog and AI reasoning engine to activate your autonomous data engineering assistant.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4">
              <div className="bg-[#0A0E17] border border-surfaceBorder rounded-xl p-4 space-y-2">
                <Server className="w-5 h-5 text-accent" />
                <h3 className="text-xs font-mono uppercase tracking-widest text-gray-400">1. Metadata Graph</h3>
                <p className="text-xs text-gray-500 font-sans">Connect DataHub GMS to discover dataset schemas & PII.</p>
              </div>

              <div className="bg-[#0A0E17] border border-surfaceBorder rounded-xl p-4 space-y-2">
                <BrainCircuit className="w-5 h-5 text-primary" />
                <h3 className="text-xs font-mono uppercase tracking-widest text-gray-400">2. AI Reasoning</h3>
                <p className="text-xs text-gray-500 font-sans">Configure OpenAI/Anthropic keys for SQL synthesis.</p>
              </div>
            </div>

            <div className="pt-6 flex justify-end">
              <button
                onClick={() => setStep(2)}
                className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-6 py-3 rounded-xl shadow-lg transition flex items-center gap-2 font-sans cursor-pointer"
              >
                Begin Setup <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: METADATA & WAREHOUSE CONFIG */}
        {step === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold font-display text-white mb-1">Metadata Graph & Warehouse</h2>
              <p className="text-xs text-gray-400 font-sans">Configure your DataHub GMS endpoint and target Snowflake warehouse.</p>
            </div>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-gray-400 mb-2">DataHub GMS Endpoint URL</label>
                <input 
                  type="text" 
                  value={gmsUrl}
                  onChange={(e) => setGmsUrl(e.target.value)}
                  placeholder="http://localhost:8080"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-gray-400 mb-2">Snowflake Account Identifier</label>
                <input 
                  type="text" 
                  value={snowflakeAccount}
                  onChange={(e) => setSnowflakeAccount(e.target.value)}
                  placeholder="xy12345.us-east-1"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                />
              </div>
            </div>

            <div className="bg-[#0A0E17] border border-success/30 rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-success" />
                <div>
                  <div className="text-xs font-bold text-white font-sans">DataHub GMS Endpoint Configured</div>
                  <div className="text-[10px] text-gray-500 font-mono">Ready to inspect dataset aspects</div>
                </div>
              </div>
              <span className="text-[10px] font-mono text-success bg-success/10 px-2.5 py-1 rounded-full font-bold">✓ READY</span>
            </div>

            <div className="pt-6 flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="border border-surfaceBorder hover:bg-surfaceBorder text-gray-300 font-bold text-xs tracking-wider uppercase px-5 py-3 rounded-xl transition flex items-center gap-2 font-sans cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>

              <button
                onClick={() => setStep(3)}
                className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-6 py-3 rounded-xl shadow-lg transition flex items-center gap-2 font-sans cursor-pointer"
              >
                Next: AI Engine <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: AI ENGINE CONFIG */}
        {step === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-lg font-bold font-display text-white mb-1">AI Reasoning Engine</h2>
              <p className="text-xs text-gray-400 font-sans">Select your LLM provider and paste your secret API key.</p>
            </div>

            <div className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-gray-400 mb-2">Provider</label>
                  <select 
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    <option value="OpenAI">OpenAI</option>
                    <option value="Anthropic">Anthropic (Claude)</option>
                    <option value="Local">Local (Ollama)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-gray-400 mb-2">Model</label>
                  <select 
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans"
                  >
                    <option value="gpt-4o">gpt-4o</option>
                    <option value="gpt-4-turbo">gpt-4-turbo</option>
                    <option value="claude-3-5-sonnet">claude-3-5-sonnet</option>
                    <option value="llama3">llama3 (local)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-gray-400 mb-2">Provider API Key</label>
                <div className="relative">
                  <input 
                    type="password" 
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-proj-..."
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-primary transition font-mono"
                  />
                  <Key className="w-4 h-4 text-gray-500 absolute right-4 top-3.5" />
                </div>
                <p className="text-[11px] text-gray-500 mt-2 font-sans flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-success inline" /> Keys are encrypted at rest using enterprise hardware-backed security.
                </p>
              </div>
            </div>

            <div className="pt-6 flex justify-between">
              <button
                onClick={() => setStep(2)}
                disabled={isSaving}
                className="border border-surfaceBorder hover:bg-surfaceBorder text-gray-300 font-bold text-xs tracking-wider uppercase px-5 py-3 rounded-xl transition flex items-center gap-2 font-sans cursor-pointer disabled:opacity-50"
              >
                <ArrowLeft className="w-4 h-4" /> Back
              </button>

              <button
                onClick={handleFinish}
                disabled={isSaving}
                className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-8 py-3 rounded-xl shadow-lg transition flex items-center gap-2 font-sans cursor-pointer disabled:opacity-50"
              >
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {isSaving ? 'Saving Configuration...' : 'Launch Studio 🚀'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
