import React, { useState } from 'react'
import { GitBranch, Maximize2, Search, ZoomIn, ChevronDown, ChevronUp } from 'lucide-react'
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

const initialNodes = [
  { id: '1', position: { x: 50, y: 150 }, data: { label: 'S3_RAW_EVENTS' }, style: { background: '#151C2C', color: '#94A3B8', border: '1px solid #334155', fontSize: '10px', fontFamily: 'monospace', padding: '8px' } },
  { id: '2', position: { x: 250, y: 100 }, data: { label: 'stg_orders' }, style: { background: '#151C2C', color: '#00E5FF', border: '1px solid #00E5FF', fontSize: '10px', fontFamily: 'monospace', padding: '8px', boxShadow: '0 0 10px rgba(0,229,255,0.4)' } },
  { id: '3', position: { x: 250, y: 200 }, data: { label: 'stg_users' }, style: { background: '#151C2C', color: '#94A3B8', border: '1px solid #334155', fontSize: '10px', fontFamily: 'monospace', padding: '8px', opacity: 0.7 } },
  { id: '4', position: { x: 450, y: 150 }, data: { label: 'fct_revenue' }, style: { background: 'rgba(0, 229, 255, 0.1)', color: '#00E5FF', border: '1px solid #00E5FF', fontSize: '12px', fontFamily: 'monospace', fontWeight: 'bold', padding: '10px', boxShadow: '0 0 15px rgba(0,229,255,0.2)' } },
  { id: '5', position: { x: 650, y: 150 }, data: { label: 'BIGQUERY_PROD' }, style: { background: '#151C2C', color: '#05F29B', border: '1px solid rgba(5, 242, 155, 0.5)', fontSize: '10px', fontFamily: 'monospace', padding: '8px' } },
]

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#00E5FF' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#00E5FF' } },
  { id: 'e1-3', source: '1', target: '3', animated: false, style: { stroke: '#334155' } },
  { id: 'e2-4', source: '2', target: '4', animated: true, style: { stroke: '#00E5FF' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#00E5FF' } },
  { id: 'e3-4', source: '3', target: '4', animated: false, style: { stroke: '#334155' } },
  { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: '#05F29B' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#05F29B' } },
]

export const LineageGraph: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="w-full bg-surface border border-surfaceBorder rounded-xl relative overflow-hidden shadow-lg flex flex-col transition-all duration-300">
      
      {/* Clickable Header */}
      <div 
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-surfaceBorder/30 transition z-10"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-accent" />
          <span className="text-xs font-bold tracking-widest text-white uppercase">Data Lineage Visualizer</span>
        </div>
        <div className="text-gray-400">
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>

      {/* Expandable Graph Content */}
      {isExpanded && (
        <div className="w-full h-64 border-t border-surfaceBorder relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            className="bg-[#060913]"
          >
            <Background color="#1E293B" gap={20} size={1} />
          </ReactFlow>

          {/* Custom Control Override */}
          <div className="absolute bottom-4 right-4 flex gap-2 z-10">
            <button className="p-2 bg-[#1E293B] hover:bg-[#334155] rounded text-gray-400 transition" onClick={() => document.querySelector('.react-flow__controls-zoomin')?.dispatchEvent(new MouseEvent('click', {bubbles:true}))}>
              <ZoomIn className="w-4 h-4" />
            </button>
            <button className="p-2 bg-[#1E293B] hover:bg-[#334155] rounded text-gray-400 transition" onClick={() => document.querySelector('.react-flow__controls-fitview')?.dispatchEvent(new MouseEvent('click', {bubbles:true}))}>
               <Search className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
