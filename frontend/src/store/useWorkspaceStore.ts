import { create } from 'zustand'

export interface ExecutionStep {
  step: number;
  type: string;
  message: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  status?: 'RUNNING' | 'SUCCESS' | 'FAILED';
  steps?: ExecutionStep[];
  result?: {
    target_urn: string;
    target_name: string;
    pii_columns: string[];
    sql: string;
    dbt_yaml: string;
  };
}

interface WorkspaceState {
  prompt: string;
  messages: ChatMessage[];
  isExecuting: boolean;
  selectedUrn: string | null;
  selectedPiiColumns: string[];
  activeSessionId: string | null;
  
  setPrompt: (prompt: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateAgentMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setSelectedUrn: (urn: string | null, piiColumns?: string[]) => void;
  setActiveSessionId: (id: string | null) => void;
  clearHistory: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  prompt: '',
  messages: [
    {
      id: 'welcome',
      sender: 'agent',
      text: 'Hello! I am Synex, your DataHub autonomous data engineering agent. Tell me what models or transformations you would like to build today.',
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
    }
  ],
  isExecuting: false,
  selectedUrn: null,
  selectedPiiColumns: [],
  activeSessionId: null,

  setPrompt: (prompt) => set({ prompt }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateAgentMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
  })),
  setSelectedUrn: (urn, piiColumns = []) => set({ selectedUrn: urn, selectedPiiColumns: piiColumns }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  clearHistory: () => set({
    messages: [
      {
        id: 'welcome',
        sender: 'agent',
        text: 'Workspace cleared. What would you like to build next?',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      }
    ],
    selectedUrn: null,
    selectedPiiColumns: [],
    activeSessionId: null
  })
}))
