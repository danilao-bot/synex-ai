# PHASE_0_REPORT — Repository Truth & Foundation Audit

**Date:** 2026-07-31  
**Scope:** Integrity / consistency only — no new product features (MCP Server, ACK, Skills, auth, live lineage UI, session memory wiring, streaming UI).  
**Tests:** `pytest backend/tests/test_backend.py` → **9 passed**

---

## Repository Health Score

### **82 / 100**

| Dimension | Score | Notes |
|---|---|---|
| README truthfulness | 18/20 | Marketing claims removed; pending demo explicit |
| API docs ↔ code | 18/20 | Contract rewritten to match FastAPI |
| Env var consistency | 10/10 | Canonical `NEXT_PUBLIC_API_URL` only |
| Dead / fake UI honesty | 14/15 | Lineage placeholder; fake GMS Live removed |
| Schema / status alignment | 10/10 | `RUNNING` / `SUCCESS` / `FAILED` match DB CHECK |
| Examples & license | 8/10 | Examples honesty; Apache 2.0 intact |
| Structure / polish | 4/5 | No abandoned folders; `.env.example` trackable |
| Remaining intentional debt | −0 | Documented below (not deducted as defects) |

**Not 100:** no screenshots folder, demo video still pending, optional `anthropic` package not in `requirements.txt`, `@xyflow/react` unused until lineage UI phase, API still unauthenticated (honest, but not production-hardened).

---

## Files Modified

| File | Change type |
|---|---|
| `README.md` | Full truthful rewrite |
| `PHASE_0_REPORT.md` | **Created** (this report) |
| `backend/API_CONTRACT.md` | Rewritten to match implementation |
| `backend/.env.example` | Expanded; aligned with `Settings` |
| `backend/app/routers/agent_router.py` | Status enum; dead import removed; field comments |
| `backend/app/core/config.py` | TODO on `DATAHUB_MCP_MUTATIONS_ENABLED` |
| `backend/app/db.py` | TODO on `get_last_run_for_session` |
| `backend/app/agent/generator.py` | TODO + suppress unused `previous_sql` |
| `backend/app/services/datahub_context.py` | Honest module/class docs; TODO on unused method |
| `backend/app/services/datahub_client.py` | Documented as unused facade (reserved) |
| `backend/tests/test_backend.py` | Assert `status == SUCCESS` |
| `examples/README.md` | Removed session-memory claims |
| `examples/fct_revenue_model.sql` | Header clarified as sample |
| `frontend/.env.example` | **Created** (`NEXT_PUBLIC_API_URL`) |
| `frontend/src/components/LineageGraph.tsx` | Fake nodes → coming-soon empty state |
| `frontend/src/components/PromptConsole.tsx` | Honest status copy; drop fake “MCP Active” |
| `frontend/src/components/MetadataInspector.tsx` | Removed fake default trust score `85` |
| `frontend/src/components/Sidebar.tsx` | Removed fake “GMS Live” indicator |
| `frontend/src/components/ChatThread.tsx` | Placeholder lineage title; suggestion buttons wired |
| `frontend/src/app/history/page.tsx` | Status filter handles `SUCCESS`/`FAILED` |
| `frontend/src/app/onboarding/page.tsx` | Corrected where keys are stored |
| `.gitignore` | Stop ignoring `backend/.env.example` |

---

## Documentation Fixed

1. Removed claim that session memory loads previous SQL into the LLM.  
2. Removed `#` YouTube demo link; marked demo as **pending before submission**.  
3. Architecture diagram updated to Mermaid reflecting GraphQL GMS + approval MCP write-back (no fake `/entities/search` REST path).  
4. Persistence described as runs + settings — not “session memory product.”  
5. Frontend env documented as **`NEXT_PUBLIC_API_URL` only** (removed `NEXT_PUBLIC_API_BASE_URL`).  
6. DataHub integration docs: GraphQL + MCP **Wrapper** emit — not MCP Server / ACK products.  
7. Supabase DDL in README aligned with live CHECK + write-back columns.  
8. `API_CONTRACT.md`: all 7 routes, ignored `writeback_enabled`, SSE vs JSON UI usage, no auth.  
9. `examples/README.md`: samples only; no conversational memory story.  
10. Security section: honest about no API auth.

---

## Dead Code Removed / Clarified

| Item | Action |
|---|---|
| `get_last_run_for_session` import in `agent_router` | **Removed** (function kept in `db.py` with Phase TODO) |
| `previous_sql` unused | **TODO** + `_ = previous_sql` (reserved for session memory phase) |
| `get_sql_query_context` unused | **TODO** docstring (reserved for context enrichment) |
| `DATAHUB_MCP_MUTATIONS_ENABLED` unused | **TODO** (gate write-back later) |
| `writeback_enabled` ignored | **Documented** in model + API contract (compat; ignored) |
| `datahub_client` wrapper unused | **Kept** with module TODO as optional facade |
| Fake ReactFlow lineage nodes/edges | **Removed** |
| Fake Sidebar “GMS Live” pulse | **Removed** |
| Fake PromptConsole “MCP Adapter: Active” | **Removed** |
| Fake trust score default `85` | **Removed** |
| Non-functional empty-state suggestion buttons | **Wired** to `setPrompt` (tiny honesty fix) |
| Hardcoded PromptConsole model label | **Removed** |

---

## Placeholder Claims Removed

| Misleading claim | Resolution |
|---|---|
| “Session memory loads previous SQL…” | Removed / marked Not wired |
| Demo YouTube `[#]` | Removed; pending note |
| Architecture step “DATAHUB_WRITEBACK” as automatic | Clarified approval-only |
| “MCP Server / Agent Context Kit” as current integration | Corrected to GMS GraphQL + MCP Wrapper |
| Live lineage visualizer | Explicit coming-soon placeholder |
| “DataHub MCP Adapter: Active” | Removed |
| “GMS STATUS: Live” without probe | Removed |
| Default trust `85` without candidate | Shows `—` |
| Examples implying follow-up memory worked | Rewritten |
| README SQL schema missing write-back / wrong status | Replaced with live-aligned DDL |

---

## Remaining Technical Debt (intentionally postponed)

| Item | Target phase (per roadmap) |
|---|---|
| DataHub MCP Server product integration | Later (MCP) |
| Agent Context Kit / DataHub Skills | Later |
| Multi-aspect metadata write-back | Later |
| Wire `get_last_run_for_session` → `previous_sql` | Session memory |
| Live ReactFlow from `lineage_impact` | Lineage UI |
| Consume SSE `/api/v1/agent/run` in UI | Streaming UX |
| Gate emits with `DATAHUB_MCP_MUTATIONS_ENABLED` | Write-back hardening |
| API authentication / rate limiting | Security |
| Add `anthropic` to `requirements.txt` (optional provider) | Dep hygiene |
| `@xyflow/react` unused until lineage UI | Keep or re-add in lineage phase |
| Screenshots / demo video assets | Submission polish |
| `schema_fields` not returned in `/run` JSON (inspector often empty) | Small API payload fix (later) |
| Settings insert-only (no upsert) | Ops polish |
| Status filter UI still labels option “Completed” while API uses `SUCCESS` | Cosmetic |

---

## Repository Ready

### **YES**

**Why:** Documentation and UI no longer claim session memory, MCP Server/ACK, live lineage graphs, or automatic graph mutation. Env vars are canonical. API contract matches FastAPI. Dead imports cleaned or TODO’d. Run statuses match Supabase CHECK. Examples and README describe current behavior. Unit tests pass. The repo is internally consistent and suitable as a truthful baseline for Phase 1 (real DataHub MCP / deeper GMS integration work).

**Caveats (do not block Phase 1):** demo video still pending; no screenshot gallery; public API remains unauthenticated by design for now.
