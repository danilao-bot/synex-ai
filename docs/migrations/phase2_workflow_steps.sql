-- Phase 2: persist structured workflow steps on synex_runs
-- Run in Supabase SQL editor when ready.

ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS workflow_steps jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN synex_runs.workflow_steps IS
  'Synex Phase-2 workflow engine steps: name, status, duration, inputs, outputs, errors, reasoning';

-- Optional index for history filters
CREATE INDEX IF NOT EXISTS idx_synex_runs_workflow_gin
  ON synex_runs USING gin (workflow_steps);
