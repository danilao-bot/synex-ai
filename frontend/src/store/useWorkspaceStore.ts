import { create } from 'zustand'

export interface SchemaField {
  fieldPath: string;
  nativeDataType: string;
  description?: string;
  tags?: { tags: { tag: { name: string } }[] };
}

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
    dataset_description: string;
    pii_columns: string[];
    schema_fields: SchemaField[];
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
  selectedSchemaFields: SchemaField[];
  selectedDatasetName: string;
  selectedDatasetDescription: string;
  activeSessionId: string | null;

  setPrompt: (prompt: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateAgentMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setSelectedMetadata: (
    urn: string | null,
    piiColumns?: string[],
    schemaFields?: SchemaField[],
    datasetName?: string,
    description?: string
  ) => void;
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
  selectedSchemaFields: [],
  selectedDatasetName: '',
  selectedDatasetDescription: '',
  activeSessionId: null,

  setPrompt: (prompt) => set({ prompt }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateAgentMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
  })),
  setSelectedMetadata: (urn, piiColumns = [], schemaFields = [], datasetName = '', description = '') =>
    set({
      selectedUrn: urn,
      selectedPiiColumns: piiColumns,
      selectedSchemaFields: schemaFields,
      selectedDatasetName: datasetName,
      selectedDatasetDescription: description,
    }),
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
    selectedSchemaFields: [],
    selectedDatasetName: '',
    selectedDatasetDescription: '',
    activeSessionId: null,
  })
}))
