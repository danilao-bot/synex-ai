export interface ExecutionStep {
  step: number;
  type: 'ENTITY_DISCOVERY' | 'GOVERNANCE_AUDIT' | 'LINEAGE_TRAVERSAL' | 'CODE_SYNTHESIS' | 'VALIDATION' | 'WRITEBACK' | 'COMPLETED';
  message: string;
  payload?: any;
}

export interface AgentRunState {
  prompt: string;
  isExecuting: boolean;
  steps: ExecutionStep[];
  targetUrn: string | null;
  targetName: string | null;
  piiColumns: string[];
  generatedSql: string | null;
  generatedDbtYaml: string | null;
  mcpStatus: string | null;
}
