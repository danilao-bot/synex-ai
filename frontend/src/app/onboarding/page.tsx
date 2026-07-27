'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Server, BrainCircuit, CheckCircle2, ArrowRight, ArrowLeft,
  Key, ShieldCheck, Database, Sparkles, Loader2, AlertCircle, Zap
} from 'lucide-react'
import { API_BASE_URL } from '../../lib/api'

interface FieldError {
  gmsUrl?: string
  apiKey?: string
}

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)

  // Form State — use correct field names matching Supabase schema
  const [gmsUrl, setGmsUrl] = useState('http://localhost:8080')
  const [provider, setProvider] = useState('openrouter')
  const [model, setModel] = useState('openai/gpt-4o')
  const [apiKey, setApiKey] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldError>({})

  // ─── Validation ──────────────────────────────────────────────────────────────
  const validateStep2 = (): boolean => {
    const errors: FieldError = {}
    if (!gmsUrl.trim()) {
      errors.gmsUrl = 'DataHub GMS URL is required.'
    } else if (!gmsUrl.startsWith('http')) {
      errors.gmsUrl = 'URL must start with http:// or https://'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const validateStep3 = (): boolean => {
    const errors: FieldError = {}
    if (!apiKey.trim()) {
      errors.apiKey = 'API key is required to activate the AI reasoning engine.'
    } else if (apiKey.trim().length < 10) {
      errors.apiKey = 'API key looks too short — please double-check it.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleStep2Next = () => {
    if (validateStep2()) {
      setFieldErrors({})
      setStep(3)
    }
  }

  // ─── Save & Finish ────────────────────────────────────────────────────────────
  const handleFinish = async () => {
    if (!validateStep3()) return

    setIsSaving(true)
    setSaveError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          datahub_url: gmsUrl.trim(),          // ✅ correct Supabase column name
          llm_provider: provider,
          llm_model: model,
          llm_api_key: apiKey.trim(),          // ✅ correct Supabase column name
        })
      })

      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`)
      }

      if (typeof window !== 'undefined') {
        localStorage.setItem('synex_onboarding_completed', 'true')
      }
      router.push('/')
    } catch (err: any) {
      setSaveError(`Setup Error: ${err.message}. You can still proceed — settings can be updated later.`)
      setIsSaving(false)
    }
  }

  // Skip to workspace without saving (e.g. demo mode)
  const handleSkip = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('synex_onboarding_completed', 'true')
    }
    router.push('/')
  }

  return (
    <div className="min-h-screen w-full bg-[#04060C] text-gray-100 flex flex-col justify-between p-8 md:p-12 relative overflow-hidden isolate">
      {/* Ambient Background Glows */}
      <div className="absolute w-[800px] h-[800px] bg-primary/10 rounded-full blur-3xl pointer-events-none -top-60 -left-60 animate-pulse" />
      <div className="absolute w-[800px] h-[800px] bg-accent/10 rounded-full blur-3xl pointer-events-none -bottom-60 -right-60 animate-pulse" />

      {/* TOP HEADER BAR */}
      <header className="w-full flex items-center justify-between border-b border-surfaceBorder/60 pb-6 relative z-10">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-2xl bg-surface border border-primary/40 flex items-center justify-center shadow-[0_0_25px_rgba(99,102,241,0.35)]">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-primary">
              <circle cx="18" cy="6" r="3.5" fill="currentColor"/>
              <circle cx="6" cy="18" r="3.5" fill="currentColor"/>
              <circle cx="12" cy="12" r="3.5" fill="currentColor"/>
              <path d="M16.5 7.5L13.5 10.5M10.5 13.5L7.5 16.5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold font-display text-white tracking-wide">Synex Agent Setup</h1>
            <p className="text-xs text-gray-400 font-sans mt-0.5">Autonomous Data Engineering Co-Pilot Initialization</p>
          </div>
        </div>

        {/* Step Progress */}
        <div className="flex items-center gap-6">
          <div className="hidden sm:flex flex-col items-end">
            <span className="text-xs font-mono font-bold text-gray-300 uppercase tracking-widest">Step {step} of 3</span>
            <span className="text-xs text-gray-500 font-sans">
              {step === 1 ? 'Welcome & Intro' : step === 2 ? 'Metadata Connection' : 'AI Reasoning Engine'}
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`h-3 rounded-full transition-all duration-300 ${
                  s === step ? 'w-12 bg-primary shadow-[0_0_15px_rgba(99,102,241,0.7)]'
                  : s < step ? 'w-3.5 bg-success' : 'w-3.5 bg-surfaceBorder'
                }`}
              />
            ))}
          </div>
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <main className="w-full max-w-5xl mx-auto py-8 relative z-10 flex-1 flex flex-col justify-center">

        {/* Global Save Error */}
        {saveError && (
          <div className="flex items-center gap-3 bg-danger/10 border border-danger/30 text-danger p-4 rounded-2xl text-xs font-semibold mb-6">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{saveError}</span>
          </div>
        )}

        {/* ── STEP 1: WELCOME ── */}
        {step === 1 && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center space-y-3 max-w-2xl mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-primary/15 border border-primary/40 flex items-center justify-center text-primary mx-auto shadow-[0_0_30px_rgba(99,102,241,0.3)] mb-2">
                <Sparkles className="w-8 h-8" />
              </div>
              <h2 className="text-3xl font-bold font-display text-white tracking-tight">Welcome to Synex Studio</h2>
              <p className="text-sm text-gray-400 font-sans leading-relaxed">
                Connect your DataHub metadata graph and AI reasoning engine to activate your autonomous data engineering co-pilot.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-2">
              <div className="bg-[#080D1A]/80 border border-surfaceBorder/80 hover:border-accent/50 rounded-3xl p-8 space-y-4 transition duration-300 backdrop-blur-xl shadow-xl">
                <div className="w-12 h-12 rounded-2xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                  <Server className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-mono uppercase tracking-widest text-gray-200 font-bold">1. Metadata Graph Catalog</h3>
                <p className="text-sm text-gray-400 font-sans leading-relaxed">
                  Synex queries your DataHub GMS to discover dataset schemas, column types, PII tags, and lineage before writing any SQL.
                </p>
              </div>

              <div className="bg-[#080D1A]/80 border border-surfaceBorder/80 hover:border-primary/50 rounded-3xl p-8 space-y-4 transition duration-300 backdrop-blur-xl shadow-xl">
                <div className="w-12 h-12 rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary">
                  <BrainCircuit className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-mono uppercase tracking-widest text-gray-200 font-bold">2. AI Reasoning Engine</h3>
                <p className="text-sm text-gray-400 font-sans leading-relaxed">
                  Connect OpenRouter to access GPT-4o, Claude, or Llama — the LLM generates production dbt models grounded in your real metadata.
                </p>
              </div>
            </div>

            <div className="pt-6 flex justify-center gap-4">
              <button
                onClick={() => setStep(2)}
                className="bg-primary hover:bg-primaryHover text-white font-bold text-sm tracking-wider uppercase px-10 py-4 rounded-2xl shadow-[0_0_30px_rgba(99,102,241,0.5)] transition flex items-center gap-3 font-sans cursor-pointer"
              >
                Begin Setup <ArrowRight className="w-5 h-5" />
              </button>
              <button
                onClick={handleSkip}
                className="border border-surfaceBorder hover:bg-surfaceBorder text-gray-400 font-bold text-sm tracking-wider uppercase px-8 py-4 rounded-2xl transition font-sans cursor-pointer"
              >
                Skip for Now
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 2: DATAHUB CONNECTION ── */}
        {step === 2 && (
          <div className="space-y-8 animate-fadeIn max-w-3xl mx-auto w-full">
            <div className="text-center space-y-2">
              <span className="text-xs font-mono text-gray-400 uppercase tracking-widest font-bold">STEP 2 OF 3</span>
              <h2 className="text-3xl font-bold font-display text-white">DataHub Metadata Connection</h2>
              <p className="text-sm text-gray-400 font-sans">Enter the URL of your DataHub GMS instance.</p>
            </div>

            <div className="bg-[#080D1A]/80 border border-surfaceBorder/80 rounded-3xl p-8 space-y-6 shadow-2xl backdrop-blur-xl">
              {/* GMS URL */}
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-gray-300 font-bold mb-2.5">
                  DataHub GMS Endpoint URL <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  value={gmsUrl}
                  onChange={(e) => { setGmsUrl(e.target.value); setFieldErrors(prev => ({ ...prev, gmsUrl: undefined })) }}
                  placeholder="http://localhost:8080"
                  className={`w-full bg-[#04060C] border rounded-2xl px-5 py-4 text-base text-white focus:outline-none transition font-mono shadow-inner ${
                    fieldErrors.gmsUrl ? 'border-danger focus:border-danger' : 'border-surfaceBorder focus:border-primary'
                  }`}
                />
                {fieldErrors.gmsUrl && (
                  <p className="mt-2 text-xs text-danger flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5" /> {fieldErrors.gmsUrl}
                  </p>
                )}
                <p className="mt-2 text-xs text-gray-500 font-sans">
                  Synex will use this endpoint to query dataset schemas and write back documentation via the DataHub Python SDK.
                </p>
              </div>

              {/* Info box */}
              <div className="bg-[#04060C] border border-accent/30 rounded-2xl p-4 flex items-start gap-3">
                <Database className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                <div className="text-xs text-gray-400 font-sans leading-relaxed">
                  <span className="text-gray-200 font-semibold">No DataHub instance?</span> You can still explore Synex — enter any URL and skip to the workspace. You can update this later in Settings.
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-surfaceBorder/50">
                <button
                  onClick={() => setStep(1)}
                  className="border border-surfaceBorder hover:bg-surfaceBorder text-gray-300 font-bold text-xs tracking-wider uppercase px-7 py-3.5 rounded-2xl transition flex items-center gap-2 font-sans cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>
                <button
                  onClick={handleStep2Next}
                  className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-9 py-3.5 rounded-2xl shadow-[0_0_25px_rgba(99,102,241,0.4)] transition flex items-center gap-2 font-sans cursor-pointer"
                >
                  Next Step <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── STEP 3: AI ENGINE ── */}
        {step === 3 && (
          <div className="space-y-8 animate-fadeIn max-w-3xl mx-auto w-full">
            <div className="text-center space-y-2">
              <span className="text-xs font-mono text-gray-400 uppercase tracking-widest font-bold">STEP 3 OF 3</span>
              <h2 className="text-3xl font-bold font-display text-white">Configure AI Reasoning Engine</h2>
              <p className="text-sm text-gray-400 font-sans">Select your LLM provider and paste your API key.</p>
            </div>

            <div className="bg-[#080D1A]/80 border border-surfaceBorder/80 rounded-3xl p-8 space-y-6 shadow-2xl backdrop-blur-xl">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Provider */}
                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-gray-300 font-bold mb-2.5">Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full bg-[#04060C] border border-surfaceBorder rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans shadow-inner"
                  >
                    <option value="openrouter">OpenRouter (Recommended)</option>
                    <option value="openai">OpenAI (Direct)</option>
                    <option value="anthropic">Anthropic (Claude)</option>
                  </select>
                </div>

                {/* Model */}
                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-gray-300 font-bold mb-2.5">Model</label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full bg-[#04060C] border border-surfaceBorder rounded-2xl px-5 py-4 text-sm text-white focus:outline-none focus:border-primary transition cursor-pointer font-sans shadow-inner"
                  >
                    <option value="openai/gpt-4o">openai/gpt-4o</option>
                    <option value="openai/gpt-4-turbo">openai/gpt-4-turbo</option>
                    <option value="anthropic/claude-3-5-sonnet">anthropic/claude-3-5-sonnet</option>
                    <option value="meta-llama/llama-3.1-70b-instruct">meta-llama/llama-3.1-70b</option>
                  </select>
                </div>
              </div>

              {/* API Key — required */}
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-gray-300 font-bold mb-2.5">
                  Provider API Key <span className="text-danger">*</span>
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => { setApiKey(e.target.value); setFieldErrors(prev => ({ ...prev, apiKey: undefined })) }}
                    placeholder="sk-or-v1-..."
                    className={`w-full bg-[#04060C] border rounded-2xl px-5 py-4 text-base text-white focus:outline-none transition font-mono shadow-inner pr-12 ${
                      fieldErrors.apiKey ? 'border-danger focus:border-danger' : 'border-surfaceBorder focus:border-primary'
                    }`}
                  />
                  <Key className="w-5 h-5 text-gray-500 absolute right-5 top-4" />
                </div>
                {fieldErrors.apiKey && (
                  <p className="mt-2 text-xs text-danger flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5" /> {fieldErrors.apiKey}
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-3 font-sans flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-success inline shrink-0" />
                  Keys are stored as server-side environment variables and never exposed to the browser.
                </p>
              </div>

              {/* OpenRouter hint */}
              <div className="bg-primary/5 border border-primary/20 rounded-2xl p-4 flex items-start gap-3">
                <Zap className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                <div className="text-xs text-gray-400 font-sans leading-relaxed">
                  <span className="text-gray-200 font-semibold">Using OpenRouter?</span> Get your key at{' '}
                  <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-primary underline">openrouter.ai/keys</a>.
                  OpenRouter gives you access to GPT-4o, Claude, and Llama through a single API key.
                </div>
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-surfaceBorder/50">
                <button
                  onClick={() => setStep(2)}
                  disabled={isSaving}
                  className="border border-surfaceBorder hover:bg-surfaceBorder text-gray-300 font-bold text-xs tracking-wider uppercase px-7 py-3.5 rounded-2xl transition flex items-center gap-2 font-sans cursor-pointer disabled:opacity-50"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </button>

                <button
                  onClick={handleFinish}
                  disabled={isSaving}
                  className="bg-primary hover:bg-primaryHover text-white font-bold text-xs tracking-wider uppercase px-10 py-3.5 rounded-2xl shadow-[0_0_30px_rgba(99,102,241,0.5)] transition flex items-center gap-2 font-sans cursor-pointer disabled:opacity-50"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {isSaving ? 'Saving Configuration...' : 'Launch Studio 🚀'}
                </button>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* FOOTER BAR */}
      <footer className="w-full flex items-center justify-center border-t border-surfaceBorder/60 pt-4 relative z-10">
        <div className="flex items-center gap-2 text-xs text-gray-500 font-sans">
          <ShieldCheck className="w-4 h-4 text-gray-600" />
          <span>Credentials stored server-side. Settings can be updated anytime in the Settings page.</span>
        </div>
      </footer>
    </div>
  )
}
