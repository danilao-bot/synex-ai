import { create } from 'zustand'
import { ExecutionStep } from '../types/agent'

interface WorkspaceState {
  prompt: string;
  isExecuting: boolean;
  steps: ExecutionStep[];
  targetUrn: string | null;
  targetName: string | null;
  piiColumns: string[];
  generatedSql: string | null;
  generatedDbtYaml: string | null;
  
  setPrompt: (prompt: string) => void;
  startExecution: () => void;
  addStep: (step: ExecutionStep) => void;
  completeExecution: (data: any) => void;
  resetWorkspace: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  prompt: 'Build a dbt model to calculate monthly customer retention using Tier-1 production tables.',
  isExecuting: false,
  steps: [],
  targetUrn: null,
  targetName: null,
  piiColumns: [],
  generatedSql: null,
  generatedDbtYaml: null,

  setPrompt: (prompt) => set({ prompt }),
  startExecution: () => set({ isExecuting: true, steps: [], generatedSql: null, generatedDbtYaml: null }),
  addStep: (step) => set((state) => ({ steps: [...state.steps, step] })),
  completeExecution: (data) => set({
    isExecuting: false,
    targetUrn: data.target_urn,
    targetName: data.target_name,
    piiColumns: data.pii_columns || [],
    generatedSql: data.sql,
    generatedDbtYaml: data.dbt_yaml
  }),
  resetWorkspace: () => set({
    isExecuting: false,
    steps: [],
    targetUrn: null,
    targetName: null,
    piiColumns: [],
    generatedSql: null,
    generatedDbtYaml: null
  })
}))
