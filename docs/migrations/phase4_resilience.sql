-- Phase 4: observability + confidence persistence
ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS observability jsonb;

ALTER TABLE synex_runs
  ADD COLUMN IF NOT EXISTS confidence numeric;

COMMENT ON COLUMN synex_runs.observability IS
  'Phase-4 AI metrics: tokens, latency, retries, fallback, provider, model';
COMMENT ON COLUMN synex_runs.confidence IS
  'Phase-4 confidence score 0-100';
