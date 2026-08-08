-- Phase 3: Engineering Context Engine persistence
-- Run in Supabase SQL editor when ready.

ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS workflow_steps jsonb DEFAULT '[]'::jsonb;

ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS context_summary jsonb;

ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS sql_explanation jsonb;

COMMENT ON COLUMN synex_runs.context_summary IS
  'Phase-3 Context Engine manifest: checklist, trust, knowledge counts';
COMMENT ON COLUMN synex_runs.sql_explanation IS
  'Phase-3 evidence-backed SQL explanation (why dataset/joins/filters)';
