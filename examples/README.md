# Synex sample outputs

Illustrative artifacts similar to what Synex generates after a successful `/api/v1/run`
(grounded in DataHub-style schema + PII masking). Judges can review quality without a live stack.

| File | Description |
|---|---|
| [`fct_revenue_model.sql`](fct_revenue_model.sql) | Sample Snowflake dbt SQL with SHA2 PII hashing |
| [`fct_revenue_schema.yml`](fct_revenue_schema.yml) | Sample dbt `schema.yml` with column tests |

## How these relate to the product

1. User prompt in Workspace Studio (e.g. build a PII-safe revenue model).
2. Backend searches DataHub GMS, scores candidates, synthesizes SQL + YAML, validates.
3. UI shows artifacts; write-back to DataHub happens only after **Approve DataHub Writeback**.

These samples include a rolling-average metric as an example of richer SQL. **Conversational
session memory (feeding prior SQL into a follow-up LLM call) is not wired in the current
codebase** — `session_id` is stored on runs for a later phase.

## Governance features shown in the sample

- `SHA2(..., 256)` on PII-style columns
- Inline SQL comments for masking decisions
- dbt tests (`not_null`, `unique`, `accepted_values`, `relationships`)
