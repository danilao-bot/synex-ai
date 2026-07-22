# Synex — Autonomous AI Data Engineering Agent Powered by DataHub

Synex is an autonomous, metadata-first AI Data Engineering Agent designed for the **Build with DataHub: The Agent Hackathon**.

Instead of blindly generating SQL or pipelines, Synex traverses DataHub's Metadata Graph (`schemaMetadata`, `globalTags`, `deprecation`, `upstreamLineage`, governance tags, and business glossaries) to understand enterprise context before generating SQL queries, dbt models, data contracts, and emitting Metadata Change Proposals (MCPs) back to DataHub.

## Repository Structure

- **`/backend`**: Python 3.11 + FastAPI + `acryl-datahub` SDK + LangChain Agent ReAct Loop + SQLGlot + DuckDB Sandbox.
- **`/frontend`**: Next.js 14 + React 18 + `@xyflow/react` (React Flow) + Monaco Code Editor + Tailwind CSS + Zustand.

## Getting Started

### Backend Setup (Developer A)
```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate | On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup (Developer B)
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
