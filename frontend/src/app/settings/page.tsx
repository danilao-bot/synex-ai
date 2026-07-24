'use client'

import React, { useState } from 'react'
import { Server, Key, BrainCircuit, Save, ShieldAlert, CheckCircle2 } from 'lucide-react'

export default function SettingsPage() {
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = () => {
    setIsSaving(true)
    setTimeout(() => setIsSaving(false), 1000)
  }

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-y-auto custom-scrollbar">
      <header className="mb-8">
        <h1 className="text-xl font-bold text-white tracking-wide mb-1">Configuration & Settings</h1>
        <p className="text-sm text-gray-400">Manage connections to DataHub GMS and LLM providers.</p>
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
                  defaultValue="http://localhost:8080"
                  className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Personal Access Token (PAT)</label>
                <div className="relative">
                  <input 
                    type="password" 
                    defaultValue="......................................"
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition"
                  />
                  <ShieldAlert className="w-4 h-4 text-warning absolute right-4 top-3" />
                </div>
                <p className="text-[10px] text-gray-500 mt-2">Requires MetadataWrite privileges to emit MCPs.</p>
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
              <div className="grid grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Provider</label>
                  <select className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition appearance-none">
                    <option>OpenAI</option>
                    <option>Anthropic</option>
                    <option>Local (Ollama)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Model</label>
                  <select className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition appearance-none">
                    <option>gpt-4o</option>
                    <option>gpt-4-turbo</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">API Key</label>
                <div className="relative">
                  <input 
                    type="password" 
                    defaultValue="sk-proj-............................."
                    className="w-full bg-[#0A0E17] border border-surfaceBorder rounded-md px-4 py-2.5 text-sm text-white focus:outline-none focus:border-accent transition"
                  />
                  <Key className="w-4 h-4 text-gray-500 absolute right-4 top-3" />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button 
              onClick={handleSave}
              className="bg-accent hover:bg-[#00D0EB] text-black font-bold text-sm tracking-widest uppercase px-8 py-3 rounded shadow-[0_0_15px_rgba(0,229,255,0.4)] transition flex items-center gap-2"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {isSaving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>

        </div>

        {/* Right Column: Diagnostics */}
        <div className="col-span-4 space-y-6">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">System Diagnostics</h2>
          
          <div className="bg-[#0A0E17] border border-success/50 rounded-lg p-5 shadow-[0_0_20px_rgba(5,242,155,0.05)]">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-success" />
                <span className="font-bold text-sm text-white">DataHub GMS</span>
              </div>
              <div className="flex items-center gap-1 bg-success/10 text-success px-2 py-0.5 rounded text-[10px] font-bold">
                <CheckCircle2 className="w-3 h-3" /> CONNECTED
              </div>
            </div>
            <div className="space-y-2 text-xs font-mono text-gray-400">
              <div className="flex justify-between"><span className="text-gray-500">Latency:</span> <span className="text-white">14ms</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Version:</span> <span className="text-white">v0.13.0</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Entities:</span> <span className="text-white">2,412</span></div>
            </div>
          </div>

          <div className="bg-[#0A0E17] border border-success/50 rounded-lg p-5 shadow-[0_0_20px_rgba(5,242,155,0.05)]">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-success" />
                <span className="font-bold text-sm text-white">OpenAI Engine</span>
              </div>
              <div className="flex items-center gap-1 bg-success/10 text-success px-2 py-0.5 rounded text-[10px] font-bold">
                <CheckCircle2 className="w-3 h-3" /> AUTHENTICATED
              </div>
            </div>
            <div className="space-y-2 text-xs font-mono text-gray-400">
              <div className="flex justify-between"><span className="text-gray-500">Model:</span> <span className="text-white">gpt-4o</span></div>
              <div className="flex justify-between"><span className="text-gray-500">Rate Limit:</span> <span className="text-white">5000/min</span></div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
