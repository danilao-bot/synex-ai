# Synex Backend API Contract

Canonical REST & SSE contract for the Synex governed dbt change agent.  
This document matches `app/routers/agent_router.py` and `app/main.py`.

**Authentication:** none. All routes are currently unauthenticated.

---

## Base URL

| Environment | URL |
| :--- | :--- |
| Local | `http://localhost:8000` |
| Production | Set via frontend `NEXT_PUBLIC_API_URL` (e.g. Render URL) |

---

## Endpoints summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Backend config health probe |
| `POST` | `/api/v1/run` | Execute workflow engine (JSON) — fallback |
| `POST` | `/api/v1/agent/run` | Execute workflow engine (**SSE** live stages) — **used by the UI** |
| `POST` | `/api/v1/runs/{run_id}/writeback/approve` | Approve multi-aspect DataHub write-back |
| `GET` | `/api/v1/history` | Recent runs from Supabase |
| `GET` | `/api/v1/settings` | Latest non-secret settings (API key masked) |
| `POST` | `/api/v1/settings` | Insert a new settings row |

---

## 1. `GET /health`

### Response `200`
```json
{
  "status": "healthy",
  "agent": "Synex Governed dbt Change Agent",
  "datahub_gms": "http://localhost:8080",
  "datahub_mcp_url": "Not configured",
  "config_issues": {}
}
```

- `status` is `"degraded"` when `config_issues` is non-empty (e.g. missing `LLM_API_KEY`, localhost GMS on a cloud host).
- Does **not** actively ping DataHub; it validates configuration only.

---

## 2. `POST /api/v1/run`

Runs the agent. **Does not mutate DataHub.** Write-back requires the approve endpoint.

### Request body
```json
{
  "prompt": "Create a PII-safe revenue model for Finance.",
  "target_dialect": "snowflake",
  "allow_deprecated_override": false,
  "session_id": "optional-session-uuid"
}
```

| Field | Type | Notes |
| :--- | :--- | :--- |
| `prompt` | string | Required, length 1–8000 |
| `target_dialect` | string | Default `snowflake` (also used by SQLGlot/DuckDB) |
| `allow_deprecated_override` | bool | Default `false`; if `false`, deprecated sources fail validation |
| `session_id` | string \| null | Stored on the run; used to reload prior SQL + structured context into the LLM |
| `writeback_enabled` | bool | **Accepted for backward compatibility; ignored.** Write-back is approval-only |

### Response `200`
Returns `run_id`, `status` (`SUCCESS` on completion), `selected_dataset`, `candidate_datasets`, `governance`, `lineage_impact`, `enriched_context`, `schema_fields`, `metadata_source`, `artifacts` (sql, dbt_yaml, tests, artifact_bundle), `validation`, `proposed_writeback` (multi-op), `trace_logs`, and a static `plan` list.

`proposed_writeback.operations` is a list of mutation ops (`update_description`, `add_tags`, …) each with a `preview` string. Human approval is still required before any mutate.

### Errors
- `400` — agent `RuntimeError` (e.g. no DataHub candidates, GMS unreachable)
- `500` — unexpected failure

---

## 3. `POST /api/v1/agent/run`

Same execution as `/api/v1/run`, but streams SSE events:

```
data: {"step":1,"type":"MCP_DISCOVERY","message":"..."}

data: {"step":N,"type":"COMPLETED","message":"...","payload":{...full result...}}
```

On failure:
```
data: {"type":"ERROR","message":"..."}
```

`Content-Type: text/event-stream`. The current frontend does **not** call this endpoint.

---

## 4. `POST /api/v1/runs/{run_id}/writeback/approve`

Executes proposed mutations via Agent Context Kit tools when available (`update_description`, `add_tags`, …). Description writes fall back to `MetadataChangeProposalWrapper` if ACK is unavailable. Requires `DATAHUB_MCP_MUTATIONS_ENABLED=true`.

### Request
```json
{
  "approved": true,
  "approved_by": "Jane Doe (Lead Data Engineer)"
}
```

### Response `200` (success)
```json
{
  "status": "success",
  "message": "Executed N/M DataHub mutation(s) for URN '...'.",
  "run_id": "...",
  "target_urn": "...",
  "approved_by": "...",
  "results": [],
  "timestamp": "2026-07-27T13:25:00.000000+00:00"
}
```

### Response `200` (idempotent)
```json
{
  "status": "already_approved",
  "message": "Write-back for run '...' was already executed previously.",
  "target_urn": "...",
  "approved_at": "..."
}
```

### Errors
- `400` — `approved` is not `true`, or target URN missing
- `404` — run not found (memory store or Supabase)
- `422` — run validation has blocking errors
- `502` — MCP emit failed

---

## 5. `GET /api/v1/history`

```json
{
  "runs": [ /* synex_runs rows, newest first, limit 20 */ ],
  "count": 0
}
```

Returns `[]` if Supabase is not configured.

---

## 6. `GET /api/v1/settings`

Returns the latest `synex_settings` row. If `llm_api_key` is present it is replaced with `llm_api_key_masked` (prefix/suffix only). Empty object if no rows / no Supabase.

---

## 7. `POST /api/v1/settings`

### Request (all fields optional)
```json
{
  "datahub_url": "http://localhost:8080",
  "datahub_pat": "...",
  "llm_provider": "openrouter",
  "llm_model": "openai/gpt-4o",
  "llm_api_key": "sk-..."
}
```

Inserts a **new** row (not an upsert). Response:
```json
{ "status": "success", "updated_keys": ["datahub_url", "llm_provider", "llm_model"] }
```

`500` if Supabase save fails (when configured).

---

## Persistence notes

- Run `status` values written by the API: `RUNNING`, `SUCCESS`, `FAILED` (match Supabase CHECK).
- `proposed_writeback.requires_approval` is always `true` after a successful run.
- In-memory `_RUN_MEMORY_STORE` backs write-back when Supabase insert did not return an id, or for the lifetime of a single process.
