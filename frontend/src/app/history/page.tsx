'use client'

import React, { useState } from 'react'
import { Filter, Calendar, Download, RefreshCw, Copy, CheckCircle2, XCircle, Loader2, Database } from 'lucide-react'

// Mock Data
const MOCK_RUNS = [
  { id: 'snx-8921-v4', status: 'SUCCESS', prompt: 'Get daily active user...', platform: 'BIGQUERY', timing: '1.2s' },
  { id: 'snx-8922-v4', status: 'SUCCESS', prompt: 'Summarize revenue...', platform: 'SNOWFLAKE', timing: '0.9s' },
  { id: 'snx-8923-v4', status: 'FAILED', prompt: 'Calculate LTV for ch...', platform: 'REDSHIFT', timing: '3.4s' },
  { id: 'snx-8924-v4', status: 'RUNNING', prompt: 'Monthly trend of shi...', platform: 'SNOWFLAKE', timing: '--' },
  { id: 'snx-8925-v4', status: 'SUCCESS', prompt: 'Inventory audit for w...', platform: 'BIGQUERY', timing: '1.5s' },
  { id: 'snx-8926-v4', status: 'SUCCESS', prompt: 'User retention cohort...', platform: 'SNOWFLAKE', timing: '2.1s' },
]

export default function HistoryPage() {
  const [selectedRun, setSelectedRun] = useState(MOCK_RUNS[1])

  return (
    <div className="flex flex-col h-full bg-background p-6 overflow-hidden">
      {/* Top Metrics Cards */}
      <div className="grid grid-cols-3 gap-6 mb-6 shrink-0">
        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg relative overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-mono text-gray-400 uppercase tracking-widest">Success Rate</h3>
            <CheckCircle2 className="w-5 h-5 text-success" />
          </div>
          <div className="flex items-end gap-4">
            <div className="w-16 h-16 rounded-full border-[4px] border-success border-r-surfaceBorder flex items-center justify-center">
              <span className="text-xs font-bold text-gray-300">98%</span>
            </div>
            <div>
              <div className="text-3xl font-bold text-white">98.4%</div>
              <div className="text-xs text-gray-500 font-mono">+0.2% from yesterday</div>
            </div>
          </div>
        </div>

        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg relative">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-mono text-gray-400 uppercase tracking-widest">Avg Gen Time</h3>
            <ActivityIcon className="w-5 h-5 text-accent" />
          </div>
          <div className="text-3xl font-bold text-accent mb-2">1.4s</div>
          {/* Sparkline mock */}
          <svg className="w-full h-10" viewBox="0 0 100 30">
            <path d="M0 20 Q10 5, 20 20 T40 20 T60 10 T80 25 T100 5" fill="none" stroke="#00E5FF" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>

        <div className="bg-surface border border-surfaceBorder rounded-xl p-5 shadow-lg">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-mono text-gray-400 uppercase tracking-widest">MCPs Emitted</h3>
            <Database className="w-5 h-5 text-[#C678DD]" />
          </div>
          <div className="text-3xl font-bold text-white mb-2">412</div>
          <div className="text-xs text-gray-500 font-mono flex items-center gap-2">
            <span className="bg-surfaceBorder px-1.5 py-0.5 rounded text-[10px]">BQ</span>
            <span className="bg-surfaceBorder px-1.5 py-0.5 rounded text-[10px]">SF</span>
            <span className="bg-surfaceBorder px-1.5 py-0.5 rounded text-[10px]">RD</span>
            across 8 platforms
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex justify-between items-center bg-surface border border-surfaceBorder rounded-lg p-2 mb-6 shrink-0">
        <div className="flex gap-4">
          <button className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-300 hover:text-white transition">
            <Filter className="w-4 h-4" /> Platform: All <span className="text-gray-600 text-[10px]">▼</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-300 hover:text-white transition">
            Status: Success <span className="text-gray-600 text-[10px]">▼</span>
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-300 hover:text-white transition bg-[#0A0E17] rounded">
            <Calendar className="w-4 h-4" /> Last 24 Hours
          </button>
        </div>
        <div className="flex gap-4">
          <input 
            type="text" 
            placeholder="Search prompts..." 
            className="bg-[#0A0E17] border border-surfaceBorder rounded px-3 py-1.5 text-xs text-white placeholder-gray-500 w-64 focus:outline-none focus:border-accent"
          />
          <button className="bg-accent text-black font-bold text-xs px-4 py-1.5 rounded uppercase tracking-wider hover:bg-[#00D0EB] transition flex items-center gap-2">
             Export CSV
          </button>
        </div>
      </div>

      {/* Main Split View */}
      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
        {/* Left Table */}
        <div className="col-span-5 bg-surface border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-surfaceBorder">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase">Execution Log</h3>
            <span className="text-[10px] text-gray-500 font-mono">128 Total Runs</span>
          </div>
          <div className="flex-1 overflow-auto custom-scrollbar">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-surfaceBorder">
                  <th className="p-4 text-[10px] font-mono text-gray-500 tracking-widest uppercase">Status</th>
                  <th className="p-4 text-[10px] font-mono text-gray-500 tracking-widest uppercase">Prompt</th>
                  <th className="p-4 text-[10px] font-mono text-gray-500 tracking-widest uppercase">Platform</th>
                  <th className="p-4 text-[10px] font-mono text-gray-500 tracking-widest uppercase text-right">Timing</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_RUNS.map((run, i) => (
                  <tr 
                    key={i} 
                    onClick={() => setSelectedRun(run)}
                    className={`border-b border-surfaceBorder/50 cursor-pointer transition ${selectedRun.id === run.id ? 'bg-accent/5' : 'hover:bg-surfaceBorder/30'}`}
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {run.status === 'SUCCESS' && <div className="w-2 h-2 rounded-full bg-success shadow-[0_0_8px_rgba(5,242,155,0.6)]" />}
                        {run.status === 'FAILED' && <div className="w-2 h-2 rounded-full bg-danger shadow-[0_0_8px_rgba(239,68,68,0.6)]" />}
                        {run.status === 'RUNNING' && <Loader2 className="w-3 h-3 text-accent animate-spin" />}
                        <span className={`text-[10px] font-mono ${run.status === 'SUCCESS' ? 'text-success' : run.status === 'FAILED' ? 'text-danger' : 'text-accent'}`}>{run.status}</span>
                      </div>
                    </td>
                    <td className="p-4 text-xs text-gray-300 truncate max-w-[150px]">{run.prompt}</td>
                    <td className="p-4">
                      <span className="bg-surfaceBorder px-2 py-1 rounded text-[9px] font-mono text-gray-400">{run.platform}</span>
                    </td>
                    <td className="p-4 text-xs font-mono text-gray-400 text-right">{run.timing}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Detail Pane */}
        <div className="col-span-7 bg-surface border border-surfaceBorder rounded-xl shadow-lg flex flex-col overflow-hidden">
          <div className="flex justify-between items-center p-4 border-b border-surfaceBorder bg-[#0A0E17]">
            <div className="flex items-center gap-3">
              <ActivityIcon className="w-5 h-5 text-accent" />
              <h2 className="text-lg font-bold text-white tracking-wide">Run: {selectedRun.id}</h2>
            </div>
            <div className="flex gap-3 text-gray-400">
              <Copy className="w-4 h-4 hover:text-white cursor-pointer transition" />
              <RefreshCw className="w-4 h-4 hover:text-white cursor-pointer transition" />
            </div>
          </div>

          <div className="flex-1 overflow-auto custom-scrollbar p-6 space-y-6">
            {/* Original Prompt */}
            <div>
              <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2">Original Prompt</h3>
              <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 text-sm text-gray-200 italic font-serif">
                "Summarize revenue from Q3 retail sales, grouping by region and excluding returned items where status is 'REJECTED'."
              </div>
            </div>

            {/* Generated SQL Diff */}
            <div>
              <div className="flex justify-between items-end mb-2">
                <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase">Generated SQL (Diff Mode)</h3>
                <span className="text-[10px] font-mono text-success">Validated AST: OK</span>
              </div>
              <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 font-mono text-xs overflow-x-auto">
                <div className="text-gray-300">SELECT region, SUM(revenue) AS total_revenue</div>
                <div className="text-gray-300">FROM `synex-prod.retail.sales`</div>
                <div className="text-gray-300">WHERE quarter = 'Q3'</div>
                <div className="text-danger bg-danger/10 line-through px-2 py-0.5">- AND return_status != 'CANCELLED'</div>
                <div className="text-success bg-success/10 px-2 py-0.5">+ AND return_status != 'REJECTED'</div>
                <div className="text-gray-300">GROUP BY 1</div>
                <div className="text-gray-300">ORDER BY 2 DESC;</div>
              </div>
            </div>

            {/* Bottom Logs (AST & MCP) */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2">AST Validation</h3>
                <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 font-mono text-[10px] text-[#05F29B] overflow-x-auto h-32">
                  <pre>{`{\n  "status": "VALID",\n  "nodes": 42,\n  "depth": 5,\n  "joins": 0,\n  "syntax": "bigquery"\n}`}</pre>
                </div>
              </div>
              <div>
                <h3 className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2">MCP Emission</h3>
                <div className="bg-[#0A0E17] border border-surfaceBorder rounded p-4 font-mono text-[10px] text-gray-300 overflow-x-auto h-32">
                  <pre>{`{\n  "id": "mcp_7721_z",\n  "type": "WRITE_BACK",\n  "target": "MetadataRepo",\n  "payload": {\n    "entities": ["urn:li..."]\n  }\n}`}</pre>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  )
}

function ActivityIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  )
}
