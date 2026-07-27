-- Migration 001: Ensure synex_settings table has updated_at column and auto-update trigger
-- Target: Supabase / PostgreSQL database
-- Executed by: Daniel / Database Admin

-- 1. Add updated_at column if missing
ALTER TABLE IF EXISTS public.synex_settings
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 2. Add created_at column if missing
ALTER TABLE IF EXISTS public.synex_settings
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- 3. Trigger to maintain updated_at on modification
CREATE OR REPLACE FUNCTION update_synex_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_synex_settings_updated_at ON public.synex_settings;

CREATE TRIGGER trigger_synex_settings_updated_at
BEFORE UPDATE ON public.synex_settings
FOR EACH ROW
EXECUTE FUNCTION update_synex_settings_updated_at();

-- 4. Add approval and writeback status columns to synex_runs table if missing
ALTER TABLE IF EXISTS public.synex_runs
ADD COLUMN IF NOT EXISTS writeback_approved BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS writeback_approved_by TEXT,
ADD COLUMN IF NOT EXISTS writeback_approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS writeback_status TEXT DEFAULT 'pending_approval';
