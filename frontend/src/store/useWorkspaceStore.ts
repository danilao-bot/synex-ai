import { create } from 'zustand'

export interface SchemaField {
  fieldPath: string;
  nativeDataType: string;
  description?: string;
  tags?: { tags: { tag: { name: string } }[] };
}

export interface CandidateDataset {
  urn: string;
  name: string;
  trust_score: number;
  is_deprecated: boolean;
  is_certified: boolean;
  owners: string[];
  domain: string | null;
  glossary_terms: string[];
  quality_signals: string[];
  pii_fields: string[];
  upstream_risks: string[];
  downstream_impact_count: number;
  selection_reasons: string[];
  rejection_reasons: string[];
}

export interface ValidationReport {
  passed: boolean;
  blocking_errors: string[];
  warnings: string[];
  schema_validation?: any;
  pii_validation?: any;
  sql_validation?: any;
  yaml_validation?: any;
}

export interface ProposedWriteback {
  requires_approval: boolean;
  target_urn: string;
  operations: string[];
  summary: string;
}

export interface ExecutionStep {
  step: number;
  type: string;
  message: string;
  status?: string;
  duration_ms?: number | null;
  stage?: string;
  stage_label?: string;
  reasoning_summary?: string;
  trust_score?: number | null;
  warnings?: string[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
  status?: 'RUNNING' | 'SUCCESS' | 'FAILED';
  steps?: ExecutionStep[];
  workflowSteps?: any[];
  plan?: { step: number; type: string; description: string }[];
  clarifyingQuestions?: string[];
  result?: {
    run_id?: string;
    target_urn: string;
    target_name: string;
    dataset_description: string;
    pii_columns: string[];
    schema_fields: SchemaField[];
    sql: string;
    dbt_yaml: string;
    dbt_tests?: string[];
    change_summary_markdown?: string;
    git_patch?: string;
    selected_dataset?: CandidateDataset;
    candidate_datasets?: CandidateDataset[];
    validation?: ValidationReport;
    proposed_writeback?: ProposedWriteback;
    writeback_status?: 'pending_approval' | 'emitted' | 'already_approved' | 'unavailable';
    enriched_context?: any;
    engineering_context?: any;
    metadata_source?: string;
    lineage_impact?: any;
    quality_report?: any;
    plan?: any[];
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
  selectedCandidate?: CandidateDataset | null;
  activeSessionId: string | null;

  setPrompt: (prompt: string) => void;
  addMessage: (message: ChatMessage) => void;
  updateAgentMessage: (id: string, updates: Partial<ChatMessage>) => void;
  setSelectedMetadata: (
    urn: string | null,
    piiColumns?: string[],
    schemaFields?: SchemaField[],
    datasetName?: string,
    description?: string,
    candidate?: CandidateDataset | null
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
      text: 'Hello! I am Synex, your DataHub Governed dbt Change Agent. Instruct me to construct PII-safe models, inspect trust scores, or evaluate lineage blast radius.',
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
    }
  ],
  isExecuting: false,
  selectedUrn: null,
  selectedPiiColumns: [],
  selectedSchemaFields: [],
  selectedDatasetName: '',
  selectedDatasetDescription: '',
  selectedCandidate: null,
  activeSessionId: null,

  setPrompt: (prompt) => set({ prompt }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateAgentMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(msg => msg.id === id ? { ...msg, ...updates } : msg)
  })),
  setSelectedMetadata: (urn, piiColumns = [], schemaFields = [], datasetName = '', description = '', candidate = null) =>
    set({
      selectedUrn: urn,
      selectedPiiColumns: piiColumns,
      selectedSchemaFields: schemaFields,
      selectedDatasetName: datasetName,
      selectedDatasetDescription: description,
      selectedCandidate: candidate,
    }),
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  clearHistory: () => set({
    messages: [
      {
        id: 'welcome',
        sender: 'agent',
        text: 'Workspace cleared. What dataset would you like to model next?',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      }
    ],
    selectedUrn: null,
    selectedPiiColumns: [],
    selectedSchemaFields: [],
    selectedDatasetName: '',
    selectedDatasetDescription: '',
    selectedCandidate: null,
    activeSessionId: null,
  })
}))
