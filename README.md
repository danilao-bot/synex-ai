# ⚡ Synex — Autonomous AI Data Engineering Agent

> **DataHub Agent Hackathon Submission** | Built by **Daniel** & **Precious**
> **License:** [Apache 2.0](LICENSE) | **Live Demo:** [synex-ai.vercel.app](https://synex-ai.vercel.app) | **Backend:** [Render](https://synex-backend.onrender.com)

Synex is a **metadata-first autonomous AI Data Engineering Agent** powered by DataHub. It queries your DataHub GMS catalog to discover real schemas, PII tags, and lineage — then calls GPT-4o (or Claude, Groq, Mistral, DeepSeek) to generate production-ready dbt SQL models and `schema.yml` contracts grounded in actual metadata. No hallucinated schemas. No templates. Real code.

---

## 🎬 Demo Video

▶ **[Watch the 3-minute demo on YouTube](#)** ← *(link will be added before submission)*

---

## 🌟 What Makes Synex Different

| Without Synex | With Synex |
|---|---|
| Engineer manually reads DataHub, copy-pastes schema | Agent queries DataHub GMS, reads real fields automatically |
| LLM hallucinates column names | SQL grounded in actual `schemaMetadata` fields from DataHub |
| PII masking is easy to forget | Synex auto-detects PII from DataHub tags + column name patterns, injects SHA2 |
| Each prompt starts from scratch | Session memory loads previous SQL from Supabase per `session_id` |
| No audit trail | Every run persisted to Supabase with full trace log, SQL, and dbt contract |
| Code lives in a chat | dbt model written back to DataHub via real MCP (Metadata Change Proposal) |

---

## 🏗️ System Architecture

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Synex Frontend (Next.js — Vercel)                      │
│  Workspace Studio · Run History · Settings              │
└──────────────────────────┬──────────────────────────────┘
                           │ POST /api/v1/run
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Synex Backend (FastAPI — Render)                       │
│                                                         │
│  1. ENTITY_DISCOVERY   → DataHub GMS /entities/search  │
│  2. GOVERNANCE_AUDIT   → DataHub GMS /aspects          │
│  3. LINEAGE_TRAVERSAL  → Schema fields + PII detection │
│  4. CODE_SYNTHESIS     → OpenRouter LLM (GPT-4o)       │
│  5. AST_VALIDATION     → SQLGlot + DuckDB sandbox      │
│  6. DATAHUB_WRITEBACK  → acryl-datahub MCP emit        │
│                                                         │
│  Session Memory: Supabase synex_runs (per session_id)  │
└──────────────┬──────────────────────────────────────────┘
               │
   ┌───────────┼───────────────┐
   ▼           ▼               ▼
DataHub GMS  OpenRouter    Supabase
(Metadata)  (GPT-4o/etc)  (Persistence)
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Zustand, ReactFlow, Monaco Editor |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| **Metadata Graph** | DataHub GMS — `acryl-datahub` Python SDK |
| **LLM Providers** | OpenRouter, OpenAI, Anthropic, Groq, Mistral, DeepSeek, Together |
| **SQL Validation** | SQLGlot (AST) + DuckDB (in-memory sandbox with real DataHub schema) |
| **Persistence** | Supabase (PostgreSQL) — runs, settings, session memory |
| **Deployments** | Vercel (frontend) · Render (backend) |

---

## 🚀 Quickstart (Local)

### Prerequisites
- Node.js 18+ and `npm`
- Python 3.11+ and `pip`
- A Supabase project ([supabase.com](https://supabase.com))
- A DataHub GMS instance (local Docker or cloud)
- An LLM API key (OpenRouter recommended)

### 1. Clone the repo
```bash
git clone https://github.com/danilao-bot/synex-ai.git
cd synex-ai
```

### 2. Supabase — Create tables
Run in your Supabase SQL editor:
```sql
-- Execution run history + session memory
CREATE TABLE public.synex_runs (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id  text,
  prompt      text,
  status      text,
  target_urn  text,
  target_name text,
  pii_columns jsonb,
  sql         text,
  dbt_yaml    text,
  trace_logs  jsonb,
  created_at  timestamptz DEFAULT now()
);

-- Agent configuration / credentials
CREATE TABLE public.synex_settings (
  id           uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  datahub_url  text,
  datahub_pat  text,
  llm_provider text DEFAULT 'openrouter',
  llm_model    text DEFAULT 'openai/gpt-4o',
  llm_api_key  text,
  created_at   timestamptz DEFAULT now()
);
```

### 3. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create backend/.env
cat > .env <<EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
LLM_API_KEY=sk-or-v1-...          # OpenRouter key (or your provider's key)
LLM_MODEL=openai/gpt-4o
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DATAHUB_GMS_URL=http://localhost:8080
EOF

# Start server
uvicorn app.main:app --port 8000 --reload
```

### 4. Frontend setup
```bash
cd frontend
npm install

# Create frontend/.env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## ⚙️ Environment Variables

### Backend (`backend/.env` or Render dashboard)

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side only) |
| `LLM_API_KEY` | API key for your LLM provider |
| `LLM_MODEL` | Model ID e.g. `openai/gpt-4o` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` (for OpenRouter) |
| `DATAHUB_GMS_URL` | Your DataHub GMS endpoint e.g. `http://localhost:8080` |

### Frontend (`frontend/.env.local` or Vercel dashboard)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL e.g. `https://your-backend.onrender.com` |

---

## 🔌 DataHub Integration

Synex uses the **`acryl-datahub` Python SDK** to:

1. **Search entities** — `datahub_client.search_entities(prompt)` → finds matching datasets
2. **Fetch aspects** — `datahub_client.get_dataset_aspects(urn)` → reads `schemaMetadata`, `deprecation`, `ownership`, `datasetProperties`
3. **Write back** — `mcp_emitter.emit_documentation_update(urn, doc)` → emits a real `MetadataChangeProposalWrapper` to document the generated model

**No DataHub instance?** The system surfaces a clear error rather than returning fake data.
For the demo, use a local DataHub via Docker:
```bash
pip install acryl-datahub
datahub docker quickstart
```
This spins up a full DataHub stack at `http://localhost:8080` with sample datasets.

---

## 📁 Sample Outputs

See the [`examples/`](examples/) folder for real outputs generated by Synex:
- [`fct_revenue_model.sql`](examples/fct_revenue_model.sql) — Production Snowflake dbt model with PII masking and rolling averages
- [`fct_revenue_schema.yml`](examples/fct_revenue_schema.yml) — dbt `schema.yml` contract with column tests and governance annotations

---

## 🔒 Security & Honesty

- **API keys** are stored as server-side environment variables — never in the browser or Git
- **No mock fallbacks** — when DataHub is unreachable, the system raises a clear error
- **MCP write-back** uses the DataHub Python SDK (`MetadataChangeProposalWrapper`) — a real graph write, not a REST call
- **PII detection** runs server-side from actual DataHub tags + column name regex patterns

---

## 📄 License

Apache License 2.0 — see [`LICENSE`](LICENSE)

---

<p align="center">Built with ❤️ for the <strong>DataHub Agent Hackathon</strong> by <strong>Daniel</strong> & <strong>Precious</strong></p>
