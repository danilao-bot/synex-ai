# Synex Backend API Contract

This document specifies the exact REST & SSE API endpoints for the Synex Governed dbt Change Agent backend.
Daniel can use this specification directly to build and test the Next.js frontend without backend coordination.

---

## Base URL
Local Development: `http://localhost:8000`  
Production: Configured via environment variable (`NEXT_PUBLIC_API_URL`).

---

## Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Backend and DataHub connection status probe |
| `POST` | `/api/v1/run` | Execute agent (returns JSON response with artifacts & proposal) |
| `POST` | `/api/v1/agent/run` | Execute agent (SSE streaming events) |
| `POST` | `/api/v1/runs/{run_id}/writeback/approve` | Explicitly approve DataHub metadata write-back |
| `GET` | `/api/v1/history` | Fetch past execution history |
| `GET` | `/api/v1/settings` | Fetch current non-secret agent configuration |
| `POST` | `/api/v1/settings` | Save agent configuration |

---

## 1. POST `/api/v1/run`

Runs the Governed dbt Change Agent flow.  
**Note:** Generation **NEVER** mutates DataHub directly (`writeback_enabled` is `false` by default).

### Request Body (`application/json`)
```json
{
  "prompt": "Create a PII-safe revenue model for Finance.",
  "target_dialect": "snowflake",
  "writeback_enabled": false,
  "allow_deprecated_override": false,
  "session_id": "optional-session-uuid"
}
```

### Response (`200 OK`)
```json
{
  "run_id": "c9a4b2e1-8f3a-4b92-91d4-28e67a01f912",
  "status": "completed",
  "selected_dataset": {
    "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.analytics.fct_revenue,PROD)",
    "name": "fct_revenue",
    "trust_score": 95,
    "is_deprecated": false,
    "is_certified": true,
    "owners": ["Finance Data Team"],
    "domain": "Finance",
    "glossary_terms": ["Revenue", "MRR"],
    "quality_signals": ["FRESHNESS: OK"],
    "pii_fields": ["customer_email", "phone_number"],
    "upstream_risks": [],
    "downstream_impact_count": 3,
    "selection_reasons": [
      "Certified / trusted dataset banner attached in DataHub.",
      "Active, non-deprecated dataset.",
      "Assigned data owners: Finance Data Team."
    ],
    "rejection_reasons": []
  },
  "candidate_datasets": [
    {
      "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.analytics.fct_revenue,PROD)",
      "name": "fct_revenue",
      "trust_score": 95,
      "is_deprecated": false,
      "is_certified": true,
      "owners": ["Finance Data Team"],
      "domain": "Finance",
      "glossary_terms": ["Revenue"],
      "quality_signals": [],
      "pii_fields": ["customer_email"],
      "upstream_risks": [],
      "downstream_impact_count": 3,
      "selection_reasons": ["Certified dataset banner"],
      "rejection_reasons": []
    },
    {
      "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,raw.legacy_revenue,PROD)",
      "name": "legacy_revenue",
      "trust_score": 20,
      "is_deprecated": true,
      "is_certified": false,
      "owners": [],
      "domain": null,
      "glossary_terms": [],
      "quality_signals": [],
      "pii_fields": ["email"],
      "upstream_risks": ["Upstream legacy source deprecated"],
      "downstream_impact_count": 0,
      "selection_reasons": [],
      "rejection_reasons": [
        "Dataset is explicitly flagged as DEPRECATED in DataHub.",
        "Missing official DataHub certification tag."
      ]
    }
  ],
  "governance": {
    "pii_fields": ["customer_email", "phone_number"],
    "deprecated": false,
    "risks": []
  },
  "lineage_impact": {
    "upstream": ["urn:li:dataset:(urn:li:dataPlatform:snowflake,raw.orders,PROD)"],
    "downstream": [
      "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.dashboard_mrr,PROD)"
    ],
    "downstream_impact_count": 3,
    "truncated": false,
    "upstream_risks": []
  },
  "artifacts": {
    "sql": "SELECT id, SHA2(customer_email, 256) AS customer_email_hash, revenue_amount FROM {{ ref('fct_revenue') }}",
    "dbt_yaml": "version: 2\nmodels:\n  - name: fct_revenue_model\n    columns:\n      - name: id\n        tests:\n          - not_null",
    "dbt_tests": [
      "not_null test on primary key fields",
      "unique test on surrogate key for fct_revenue",
      "expression test verifying SHA2 hash length on PII columns"
    ],
    "artifact_bundle": {
      "sql_file_path": "models/generated/fct_revenue.sql",
      "sql": "SELECT id, SHA2(customer_email, 256) AS customer_email_hash, revenue_amount FROM {{ ref('fct_revenue') }}",
      "schema_file_path": "models/generated/schema.yml",
      "dbt_yaml": "version: 2\nmodels:\n  - name: fct_revenue_model",
      "dbt_tests": [
        "not_null test on primary key fields"
      ],
      "change_summary_markdown": "## Synex Governed dbt Change Summary\n...",
      "git_patch": "--- /dev/null\n+++ b/models/generated/fct_revenue.sql\n..."
    }
  },
  "validation": {
    "passed": true,
    "blocking_errors": [],
    "warnings": [],
    "schema_validation": {
      "schema_fields_count": 5,
      "referenced_columns": ["id", "customer_email", "revenue_amount"],
      "absent_fields": []
    },
    "pii_validation": {
      "identified_pii_fields": ["customer_email"],
      "unmasked_pii_detected": [],
      "masked_pii_confirmed": ["customer_email"]
    },
    "sql_validation": {
      "ast_valid": true,
      "ast_error": null,
      "sandbox_success": true,
      "sandbox_error": null
    },
    "yaml_validation": {
      "yaml_valid": true,
      "yaml_error": null
    }
  },
  "proposed_writeback": {
    "requires_approval": true,
    "target_urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.analytics.fct_revenue,PROD)",
    "operations": [
      "Append Synex Generated Contract documentation block"
    ],
    "summary": "Proposed metadata change proposal (MCP) for dataset URN 'urn:li:dataset...'. Requires approval via POST /api/v1/runs/{run_id}/writeback/approve."
  },
  "trace_logs": [
    { "step": 1, "type": "MCP_DISCOVERY", "message": "Searching DataHub catalog..." },
    { "step": 2, "type": "GRAPH_REASONING", "message": "Evaluating candidates..." },
    { "step": 3, "type": "SOURCE_SELECTION", "message": "Selected canonical dataset..." },
    { "step": 4, "type": "LINEAGE_TRAVERSAL", "message": "Lineage mapped..." },
    { "step": 5, "type": "CODE_SYNTHESIS", "message": "Calling LLM..." },
    { "step": 6, "type": "DETERMINISTIC_VALIDATION", "message": "Performing validation..." },
    { "step": 7, "type": "WRITEBACK_PROPOSAL", "message": "Generated proposal." }
  ]
}
```

---

## 2. POST `/api/v1/runs/{run_id}/writeback/approve`

Triggers the DataHub Metadata Change Proposal (MCP) write-back after explicit user approval in the UI.

### Path Parameter
- `run_id` (string, required): The ID returned in `/api/v1/run`.

### Request Body (`application/json`)
```json
{
  "approved": true,
  "approved_by": "Jane Doe (Lead Data Engineer)"
}
```

### Response (`200 OK`)
```json
{
  "status": "success",
  "message": "DataHub Metadata Change Proposal (MCP) successfully emitted for URN 'urn:li:dataset...'.",
  "run_id": "c9a4b2e1-8f3a-4b92-91d4-28e67a01f912",
  "target_urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.analytics.fct_revenue,PROD)",
  "approved_by": "Jane Doe (Lead Data Engineer)",
  "timestamp": "2026-07-27T13:25:00.000000+00:00"
}
```

### Error Responses
- `400 Bad Request`: `{"detail": "Write-back approval rejected. Field 'approved' must be explicitly true."}`
- `404 Not Found`: `{"detail": "Run ID '...' not found."}`
- `422 Unprocessable Entity`: `{"detail": "Cannot approve write-back for run with validation blocking errors: ..."}`

---

## 3. GET `/health`

Returns health status of the backend and DataHub configuration issues.

### Response (`200 OK`)
```json
{
  "status": "healthy",
  "agent": "Synex Governed dbt Change Agent",
  "datahub_gms": "http://localhost:8080",
  "datahub_mcp_url": "http://localhost:8080",
  "config_issues": {}
}
```
