'use client'

import React, { useState, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  Handle,
  Position,
  NodeProps,
  Edge,
  Node
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  GitBranch, Search, Maximize2, ShieldAlert, Award,
  Bookmark, User, Tag, ChevronDown, ChevronUp, Layers
} from 'lucide-react'
import { useWorkspaceStore } from '../store/useWorkspaceStore'

// Define Custom Node Type for rich visualizations
interface CustomNodeData extends Record<string, unknown> {
  label: string
  urn: string
  type?: string
  owners?: string[]
  tags?: string[]
  glossary?: string[]
  domain?: string
  isCertified?: boolean
  isDeprecated?: boolean
  isCenter?: boolean
  isUpstream?: boolean
  collapsed?: boolean
  onToggleCollapse?: () => void
  highlighted?: boolean
}

const CustomLineageNode: React.FC<NodeProps<Node>> = (props) => {
  const data = props.data as unknown as CustomNodeData
  const isCenter = data.isCenter
  const isUpstream = data.isUpstream
  const hasMetadata = (data.tags && data.tags.length > 0) || (data.glossary && data.glossary.length > 0) || data.owners

  return (
    <div className={`p-3 rounded-xl border text-xs font-sans min-w-[200px] shadow-xl transition-all duration-300 ${
      data.highlighted 
        ? 'border-primary ring-2 ring-primary/30 bg-[#090E1B]' 
        : isCenter 
          ? 'border-accent/80 bg-[#05111E]/95' 
          : 'border-surfaceBorder/80 bg-[#050811]/95'
    }`}>
      {/* Handles */}
      {!isCenter && isUpstream && (
        <Handle type="source" position={Position.Right} style={{ background: '#6366F1' }} />
      )}
      {!isCenter && !isUpstream && (
        <Handle type="target" position={Position.Left} style={{ background: '#05F29B' }} />
      )}
      {isCenter && (
        <>
          <Handle type="target" position={Position.Left} style={{ background: '#6366F1' }} />
          <Handle type="source" position={Position.Right} style={{ background: '#05F29B' }} />
        </>
      )}

      {/* Node Header */}
      <div className="flex items-center justify-between gap-2 border-b border-surfaceBorder/40 pb-1.5 mb-1.5">
        <span className="font-mono text-[9px] text-gray-500 uppercase tracking-widest flex items-center gap-1">
          <Layers className="w-2.5 h-2.5 text-accent" />
          {data.type || 'DATASET'}
        </span>
        <div className="flex gap-1">
          {data.isCertified && (
            <span title="Certified Asset">
              <Award className="w-3.5 h-3.5 text-success fill-success/15" />
            </span>
          )}
          {data.isDeprecated && (
            <span title="Deprecated Asset">
              <ShieldAlert className="w-3.5 h-3.5 text-danger fill-danger/15" />
            </span>
          )}
        </div>
      </div>

      {/* Label */}
      <div className="font-bold text-gray-200 truncate mb-1" title={data.label}>
        {data.label.split('.').pop() || data.label}
      </div>
      <div className="font-mono text-[8px] text-gray-500 truncate" title={data.urn}>
        {data.urn}
      </div>

      {/* Badges / Attributes */}
      {hasMetadata && (
        <div className="flex flex-wrap gap-1 mt-2 border-t border-surfaceBorder/30 pt-1.5">
          {data.domain && (
            <span className="bg-primary/10 border border-primary/20 text-primary px-1 rounded text-[8px] font-semibold">
              {data.domain}
            </span>
          )}
          {data.owners && data.owners.length > 0 && (
            <span className="bg-surface border border-surfaceBorder text-gray-300 px-1 rounded text-[8px] flex items-center gap-0.5">
              <User className="w-2 h-2 text-accent" />
              {data.owners[0].split('@')[0]}
            </span>
          )}
          {data.tags && data.tags.slice(0, 2).map((t, idx) => (
            <span key={idx} className="bg-success/10 border border-success/20 text-success px-1 rounded text-[8px] flex items-center gap-0.5">
              <Tag className="w-2 h-2" />
              {t}
            </span>
          ))}
          {data.glossary && data.glossary.slice(0, 1).map((g, idx) => (
            <span key={idx} className="bg-accent/10 border border-accent/20 text-accent px-1 rounded text-[8px] flex items-center gap-0.5">
              <Bookmark className="w-2 h-2" />
              {g}
            </span>
          ))}
        </div>
      )}

      {/* Interactive collapse handle */}
      {data.onToggleCollapse && (
        <button
          onClick={(e) => { e.stopPropagation(); data.onToggleCollapse?.() }}
          className="w-full flex items-center justify-center border-t border-surfaceBorder/20 mt-1.5 pt-1 text-gray-500 hover:text-white transition-colors cursor-pointer"
        >
          {data.collapsed ? (
            <span className="flex items-center gap-0.5 text-[8px]"><ChevronDown className="w-3 h-3" /> Expand Branch</span>
          ) : (
            <span className="flex items-center gap-0.5 text-[8px]"><ChevronUp className="w-3 h-3" /> Collapse Branch</span>
          )}
        </button>
      )}
    </div>
  )
}

const nodeTypes = {
  customLineageNode: CustomLineageNode,
}

interface LineageGraphProps {
  result?: any
}

export const LineageGraph: React.FC<LineageGraphProps> = ({ result }) => {
  const storeMessages = useWorkspaceStore((s) => s.messages)
  
  // Find current result if not passed explicitly
  const activeResult = useMemo(() => {
    if (result) return result
    const last = [...storeMessages].reverse().find((m) => m.sender === 'agent' && m.result)
    return last?.result
  }, [result, storeMessages])

  const lineage = activeResult?.lineage_impact
  const targetName = activeResult?.target_name || 'selected'
  const targetUrn = activeResult?.target_urn || ''

  // Node states
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedNodeDetails, setSelectedNodeDetails] = useState<any | null>(null)
  const [collapsedBranches, setCollapsedBranches] = useState<Set<string>>(new Set())
  const [highlightedPath, setHighlightedPath] = useState<string | null>(null)

  // Toggle node branch collapse
  const handleToggleCollapse = (urn: string) => {
    setCollapsedBranches(prev => {
      const next = new Set(prev)
      if (next.has(urn)) next.delete(urn)
      else next.add(urn)
      return next
    })
  }

  // Populate react flow graph elements
  useEffect(() => {
    if (!lineage) {
      setNodes([])
      setEdges([])
      return
    }

    const upRaw = lineage.upstream_nodes || []
    const downRaw = lineage.downstream_nodes || []

    const ns: Node[] = []
    const es: Edge[] = []

    // Center Node details from selected dataset
    const isCenterHighlighted = highlightedPath === 'center' || highlightedPath === targetUrn
    const selectedDataset = activeResult?.selected_dataset || {}
    
    ns.push({
      id: 'center',
      type: 'customLineageNode',
      position: { x: 280, y: 150 },
      data: {
        label: targetName,
        urn: targetUrn,
        type: 'CURRENT MODEL',
        owners: selectedDataset.owners || [],
        tags: selectedDataset.tags || [],
        glossary: selectedDataset.glossary_terms || [],
        domain: selectedDataset.domain || undefined,
        isCertified: selectedDataset.is_certified,
        isDeprecated: selectedDataset.is_deprecated,
        isCenter: true,
        highlighted: isCenterHighlighted || searchTerm.toLowerCase() ? targetName.toLowerCase().includes(searchTerm.toLowerCase()) : false
      }
    })

    // Filter based on collapses
    const isUpstreamCollapsed = collapsedBranches.has('upstream')
    const isDownstreamCollapsed = collapsedBranches.has('downstream')

    // Generate Upstream Nodes
    if (!isUpstreamCollapsed) {
      upRaw.forEach((n: any, i: number) => {
        const id = `up-${i}`
        const nodeUrn = n.urn || id
        const nodeName = n.name || nodeUrn.split(':').pop() || 'dataset'
        const isHighlighted = highlightedPath === id || highlightedPath === nodeUrn || (searchTerm && nodeName.toLowerCase().includes(searchTerm.toLowerCase()))

        ns.push({
          id,
          type: 'customLineageNode',
          position: { x: 30, y: 40 + i * 160 },
          data: {
            label: nodeName,
            urn: nodeUrn,
            type: n.type || 'UPSTREAM',
            owners: n.owners,
            tags: n.tags ? Object.keys(n.tags) : [],
            glossary: n.glossary,
            domain: n.domain,
            isCertified: n.isCertified || n.tags?.Certified,
            isDeprecated: n.isDeprecated || n.deprecation?.deprecated,
            isUpstream: true,
            onToggleCollapse: () => handleToggleCollapse(nodeUrn),
            collapsed: collapsedBranches.has(nodeUrn),
            highlighted: !!isHighlighted
          }
        })

        // Edge connect
        es.push({
          id: `e-${id}`,
          source: id,
          target: 'center',
          animated: true,
          style: { stroke: isHighlighted ? '#6366F1' : '#334155', strokeWidth: isHighlighted ? 2.5 : 1 },
          markerEnd: { type: MarkerType.ArrowClosed, color: isHighlighted ? '#6366F1' : '#334155' }
        })
      })
    }

    // Generate Downstream Nodes
    if (!isDownstreamCollapsed) {
      downRaw.forEach((n: any, i: number) => {
        const id = `down-${i}`
        const nodeUrn = n.urn || id
        const nodeName = n.name || nodeUrn.split(':').pop() || 'dataset'
        const isHighlighted = highlightedPath === id || highlightedPath === nodeUrn || (searchTerm && nodeName.toLowerCase().includes(searchTerm.toLowerCase()))

        ns.push({
          id,
          type: 'customLineageNode',
          position: { x: 530, y: 40 + i * 160 },
          data: {
            label: nodeName,
            urn: nodeUrn,
            type: n.type || 'DOWNSTREAM',
            owners: n.owners,
            tags: n.tags ? Object.keys(n.tags) : [],
            glossary: n.glossary,
            domain: n.domain,
            isCertified: n.isCertified || n.tags?.Certified,
            isDeprecated: n.isDeprecated || n.deprecation?.deprecated,
            isUpstream: false,
            onToggleCollapse: () => handleToggleCollapse(nodeUrn),
            collapsed: collapsedBranches.has(nodeUrn),
            highlighted: !!isHighlighted
          }
        })

        // Edge connect
        es.push({
          id: `e-${id}`,
          source: 'center',
          target: id,
          animated: true,
          style: { stroke: isHighlighted ? '#05F29B' : '#334155', strokeWidth: isHighlighted ? 2.5 : 1 },
          markerEnd: { type: MarkerType.ArrowClosed, color: isHighlighted ? '#05F29B' : '#334155' }
        })
      })
    }

    setNodes(ns)
    setEdges(es)
  }, [lineage, targetName, targetUrn, collapsedBranches, searchTerm, highlightedPath, activeResult])

  // Handle Node Click details
  const onNodeClick = (_e: any, node: Node) => {
    const data = node.data as CustomNodeData
    setSelectedNodeDetails(data)
    setHighlightedPath(node.id === 'center' ? targetUrn : data.urn)
  }

  // Render empty state if no lineage
  if (!lineage || ((lineage.upstream_nodes || []).length === 0 && (lineage.downstream_nodes || []).length === 0)) {
    return (
      <div className="w-full h-full min-h-[16rem] bg-[#060913] border border-surfaceBorder rounded-xl flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-surface border border-surfaceBorder flex items-center justify-center mb-4">
          <GitBranch className="w-6 h-6 text-accent" />
        </div>
        <h3 className="text-sm font-semibold text-white mb-1">No Lineage Mapped</h3>
        <p className="text-xs text-gray-400 max-w-sm leading-relaxed font-sans">
          This model has no upstream sources or downstream dependencies registered in DataHub.
        </p>
      </div>
    )
  }

  return (
    <div className="w-full h-full min-h-[22rem] bg-[#060913] border border-surfaceBorder rounded-xl overflow-hidden flex flex-col relative group">
      
      {/* Header bar controls */}
      <div className="px-4 py-2 border-b border-surfaceBorder bg-surface/50 flex items-center justify-between gap-4 z-10 relative">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-primary" />
          <span className="text-xs font-bold text-gray-200 font-sans uppercase tracking-wider">DataHub Lineage Graph</span>
        </div>

        {/* Node search control */}
        <div className="flex items-center gap-2 bg-[#04060C] border border-surfaceBorder rounded-lg px-2.5 py-1 text-xs max-w-xs w-full">
          <Search className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          <input
            type="text"
            placeholder="Search lineage nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-none text-white focus:outline-none w-full text-[11px]"
          />
        </div>

        <div className="flex gap-2">
          <button 
            onClick={() => { setCollapsedBranches(new Set()); setSearchTerm(''); setHighlightedPath(null); setSelectedNodeDetails(null) }}
            className="text-[10px] font-sans text-gray-400 hover:text-white px-2 py-1 rounded bg-surfaceBorder border border-surfaceBorder transition-all cursor-pointer"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Main Flow Canvas */}
      <div className="flex-1 min-h-[16rem] relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          className="bg-[#060913]"
        >
          <Background color="#1E293B" gap={20} size={1} />
          <Controls className="bg-[#0b101f] border border-surfaceBorder text-white rounded shadow-2xl" />
          <MiniMap 
            nodeColor={(node) => {
              if (node.id === 'center') return '#00E5FF'
              if (node.id.startsWith('up')) return '#6366F1'
              return '#05F29B'
            }}
            maskColor="rgba(4, 6, 12, 0.7)"
            className="border border-surfaceBorder/60 bg-[#04060C] rounded-lg shadow-xl"
            style={{ width: 100, height: 80 }}
          />
        </ReactFlow>
      </div>

      {/* Details Side-Drawer / Footer panel */}
      {selectedNodeDetails && (
        <div className="bg-[#080d19] border-t border-surfaceBorder/85 p-3.5 text-xs text-gray-300 font-sans z-10 relative flex flex-col gap-2 max-h-36 overflow-y-auto animate-fadeIn shrink-0">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white text-[13px]">{selectedNodeDetails.label}</span>
            <button 
              onClick={() => { setSelectedNodeDetails(null); setHighlightedPath(null) }} 
              className="text-gray-500 hover:text-white text-xs font-mono"
            >
              ✕ Close
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-500 font-mono text-[9px] uppercase tracking-wider">URN</p>
              <p className="font-mono text-accent text-[10px] break-all truncate" title={selectedNodeDetails.urn}>{selectedNodeDetails.urn}</p>
            </div>
            <div>
              <p className="text-gray-500 font-mono text-[9px] uppercase tracking-wider">Ownership</p>
              <p className="text-gray-200">{selectedNodeDetails.owners?.join(', ') || 'No Owner Listed'}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 pt-1 border-t border-surfaceBorder/30">
            {selectedNodeDetails.domain && (
              <span className="text-[10px] bg-primary/10 border border-primary/20 text-primary px-1.5 py-0.5 rounded">
                Domain: {selectedNodeDetails.domain}
              </span>
            )}
            {selectedNodeDetails.tags?.map((t: string) => (
              <span key={t} className="text-[10px] bg-success/15 border border-success/30 text-success px-1.5 py-0.5 rounded">
                Tag: {t}
              </span>
            ))}
            {selectedNodeDetails.glossary?.map((g: string) => (
              <span key={g} className="text-[10px] bg-accent/15 border border-accent/30 text-accent px-1.5 py-0.5 rounded">
                Term: {g}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
