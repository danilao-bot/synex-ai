"""Comprehensive Unit Test Suite for Synex Governed dbt Change Agent.

All tests use mocks and fakes — zero external dependencies on real DataHub, Supabase, or LLMs required.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.agent.context_reasoner import context_reasoner
from app.agent.validator import validator
from app.agent.generator import generator
from app.services.datahub_context import DataHubContextAdapter

client = TestClient(app)

# Localize auth override to this file only to prevent leaking into security tests
@pytest.fixture(autouse=True)
def override_auth():
    from app.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"sub": "developer", "role": "admin"}
    yield
    app.dependency_overrides.pop(get_current_user, None)


# --- 1. Trust Scoring & Certified Source Selection Tests ---

def test_trust_scoring_certified_source():
    candidate_meta = {
        "urn": "urn:li:dataset:(snowflake,prod.finance.fct_revenue,PROD)",
        "name": "fct_revenue",
        "deprecation": {"deprecated": False},
        "tags": {"tags": [{"tag": {"name": "CERTIFIED"}}]},
        "ownership": {"owners": [{"owner": {"properties": {"displayName": "Finance Lead"}}}]},
        "domain": {"domain": {"properties": {"name": "Finance"}}},
        "glossaryTerms": {"terms": [{"term": {"properties": {"name": "Revenue"}}}]},
        "schemaMetadata": {"fields": [{"fieldPath": "customer_email", "nativeDataType": "VARCHAR"}]},
    }
    eval_res = context_reasoner.evaluate_candidate(candidate_meta, "revenue model for Finance")
    assert eval_res["is_certified"] is True
    assert eval_res["is_deprecated"] is False
    assert eval_res["trust_score"] >= 80
    assert any("Certified" in r for r in eval_res["selection_reasons"])


def test_trust_scoring_deprecated_source_rejection():
    candidate_meta = {
        "urn": "urn:li:dataset:(snowflake,prod.legacy.old_revenue,PROD)",
        "name": "old_revenue",
        "deprecation": {"deprecated": True, "note": "Use fct_revenue instead"},
        "tags": {"tags": []},
        "ownership": {"owners": []},
        "schemaMetadata": {"fields": []},
    }
    eval_res = context_reasoner.evaluate_candidate(candidate_meta, "revenue model")
    assert eval_res["is_deprecated"] is True
    assert eval_res["trust_score"] < 50
    assert any("DEPRECATED" in r for r in eval_res["rejection_reasons"])


# --- 2. Deterministic Governance Validation Tests ---

def test_validation_raw_pii_rejection():
    sql = "SELECT id, customer_email, revenue_amount FROM {{ ref('fct_revenue') }}"
    dbt_yaml = "version: 2\nmodels:\n  - name: fct_revenue"
    schema_fields = [
        {"fieldPath": "id", "nativeDataType": "VARCHAR"},
        {"fieldPath": "customer_email", "nativeDataType": "VARCHAR"},
        {"fieldPath": "revenue_amount", "nativeDataType": "DOUBLE"},
    ]
    pii_fields = ["customer_email"]

    report = validator.validate_governance(
        sql=sql,
        dbt_yaml=dbt_yaml,
        schema_fields=schema_fields,
        pii_fields=pii_fields,
        is_deprecated=False,
    )
    assert report["passed"] is False
    assert any("Raw unmasked PII detected" in err for err in report["blocking_errors"])


def test_validation_masked_pii_approval():
    sql = "SELECT id, SHA2(customer_email, 256) AS customer_email_hash, revenue_amount FROM {{ ref('fct_revenue') }}"
    dbt_yaml = "version: 2\nmodels:\n  - name: fct_revenue"
    schema_fields = [
        {"fieldPath": "id", "nativeDataType": "VARCHAR"},
        {"fieldPath": "customer_email", "nativeDataType": "VARCHAR"},
        {"fieldPath": "revenue_amount", "nativeDataType": "DOUBLE"},
    ]
    pii_fields = ["customer_email"]

    report = validator.validate_governance(
        sql=sql,
        dbt_yaml=dbt_yaml,
        schema_fields=schema_fields,
        pii_fields=pii_fields,
        is_deprecated=False,
    )
    assert report["passed"] is True
    assert len(report["blocking_errors"]) == 0
    assert "customer_email" in report["pii_validation"]["masked_pii_confirmed"]


def test_validation_absent_schema_field_rejection():
    sql = "SELECT id, nonexistent_column FROM {{ ref('fct_revenue') }}"
    dbt_yaml = "version: 2\nmodels:\n  - name: fct_revenue"
    schema_fields = [{"fieldPath": "id", "nativeDataType": "VARCHAR"}]

    report = validator.validate_governance(
        sql=sql,
        dbt_yaml=dbt_yaml,
        schema_fields=schema_fields,
        pii_fields=[],
        is_deprecated=False,
    )
    assert report["passed"] is False
    assert any("absent from DataHub schema" in err for err in report["blocking_errors"])


def test_validation_yaml_parsing_failure():
    sql = "SELECT id FROM {{ ref('fct_revenue') }}"
    invalid_yaml = "models: [invalid: yaml: :"

    report = validator.validate_governance(
        sql=sql,
        dbt_yaml=invalid_yaml,
        schema_fields=[{"fieldPath": "id", "nativeDataType": "VARCHAR"}],
        pii_fields=[],
        is_deprecated=False,
    )
    assert report["passed"] is False
    assert any("YAML" in err for err in report["blocking_errors"])


# --- 3. DataHub MCP Connection Failure Test ---

@pytest.mark.asyncio
async def test_mcp_adapter_connection_failure():
    adapter = DataHubContextAdapter(gms_url="http://invalid-localhost-99999")
    with pytest.raises(RuntimeError) as exc_info:
        await adapter.search_candidates("revenue")
    assert "Cannot reach DataHub GMS" in str(exc_info.value) or "Unable to connect" in str(exc_info.value) or "returned" in str(exc_info.value)


# --- 4. API Endpoint Integration Tests (Using Mocks) ---

from app.services.datahub.models import EnrichedContext


@patch("app.workflow.stages.generation.generator.generate_code_and_contract")
@patch("app.context.engine.datahub_service.grep_documents", new_callable=AsyncMock)
@patch("app.context.engine.datahub_service.search_documents", new_callable=AsyncMock)
@patch("app.context.engine.datahub_service.get_dataset_queries", new_callable=AsyncMock)
@patch("app.workflow.stages.enrichment.datahub_service.enrich_dataset", new_callable=AsyncMock)
@patch("app.workflow.stages.trust.datahub_service.get_lineage", new_callable=AsyncMock)
@patch("app.workflow.stages.trust.datahub_service.get_entity", new_callable=AsyncMock)
@patch("app.workflow.stages.search.datahub_service.search", new_callable=AsyncMock)
def test_run_endpoint_never_writes_directly(
    mock_search, mock_get_entity, mock_lineage, mock_enrich, mock_queries, mock_docs, mock_grep, mock_gen
):
    urn = "urn:li:dataset:(snowflake,fct_revenue,PROD)"
    meta = {
        "urn": urn,
        "name": "fct_revenue",
        "schemaMetadata": {"fields": [{"fieldPath": "id", "nativeDataType": "VARCHAR"}, {"fieldPath": "revenue_amount", "nativeDataType": "DOUBLE"}]},
        "tags": {"tags": [{"tag": {"name": "CERTIFIED"}}]},
        "deprecation": {"deprecated": False},
        "ownership": {"owners": [{"owner": {"properties": {"displayName": "Finance Lead"}}}]},
        "glossaryTerms": {"terms": [{"term": {"properties": {"name": "Revenue"}}}]},
        "domain": {"domain": {"properties": {"name": "Finance"}}},
    }
    mock_search.return_value = ([{"urn": urn, "name": "fct_revenue"}], "ack")
    mock_get_entity.return_value = (meta, "ack")
    mock_lineage.return_value = []
    mock_queries.return_value = [
        "WITH base AS (SELECT id, SUM(revenue_amount) AS total_revenue FROM fct_revenue r "
        "LEFT JOIN dim_customer c ON r.customer_id = c.id WHERE r.order_date >= CURRENT_DATE - 30 "
        "GROUP BY id)"
    ]
    mock_docs.return_value = ["Finance revenue runbook: use fct_revenue for ARR"]
    mock_grep.return_value = ["Governance: hash PII emails with SHA2"]
    mock_enrich.return_value = EnrichedContext(
        urn=urn,
        name="fct_revenue",
        schema_fields=[
            {"fieldPath": "id", "nativeDataType": "VARCHAR"},
            {"fieldPath": "revenue_amount", "nativeDataType": "DOUBLE"},
            {"fieldPath": "customer_id", "nativeDataType": "VARCHAR"},
        ],
        owners=["Finance Lead"],
        glossary_terms=["Revenue"],
        domain="Finance",
        sample_queries=[],
        documents=[],
        institutional_memory=["Prefer fct_revenue over legacy tables"],
        metadata_source="ack",
        is_certified=True,
    )
    mock_gen.return_value = {
        "sql": "SELECT id FROM {{ ref('fct_revenue') }}",
        "dbt_yaml": "version: 2\nmodels: []",
        "artifact_bundle": {
            "sql_file_path": "models/generated/fct_revenue.sql",
            "sql": "SELECT id FROM {{ ref('fct_revenue') }}",
            "schema_file_path": "models/generated/schema.yml",
            "dbt_yaml": "version: 2",
            "dbt_tests": [],
            "change_summary_markdown": "summary",
            "git_patch": "patch",
        },
    }

    response = client.post("/api/v1/run", json={"prompt": "Create a PII-safe revenue model for Finance"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "SUCCESS"
    assert data["proposed_writeback"]["requires_approval"] is True
    assert data["metadata_source"] == "ack"
    assert isinstance(data["proposed_writeback"]["operations"], list)
    assert "workflow_steps" in data
    assert len(data["workflow_steps"]) >= 8
    assert data.get("plan")
    assert data.get("engineering_context") is not None
    assert data.get("context_package") is not None
    assert data["context_package"]["sql_profile"]["query_count"] >= 1
    assert data.get("context_manifest")
    assert data.get("sql_explanation")
    assert "PRODUCTION SQL PROFILE" in (data["engineering_context"].get("compressed_block") or data["context_package"]["compressed_prompt_block"])
    mock_queries.assert_awaited()
    mock_docs.assert_awaited()
    mock_grep.assert_awaited()
    # Generator must receive context block, not bare schema-only prompt
    gen_kwargs = mock_gen.call_args.kwargs
    assert "PRODUCTION SQL PROFILE" in (gen_kwargs.get("enriched_context_block") or "")
    assert "BUSINESS VOCABULARY" in (gen_kwargs.get("enriched_context_block") or "")
    assert data.get("confidence") is not None
    assert data.get("self_critique") is not None
    assert data.get("observability") is not None
    assert data.get("engineering_memory") is not None


def test_intent_ambiguity_asks_before_generating():
    from app.workflow.stages.intent import IntentAnalyzer
    from app.workflow.models import WorkflowState, RunOutcome, WorkflowStep
    import asyncio

    async def _run():
        state = WorkflowState(prompt="hi", run_id="t1")
        stage = IntentAnalyzer()
        step = WorkflowStep(id="intent", name="intent", label="Understanding request")
        return await stage.execute(state, step)

    state = asyncio.run(_run())
    assert state.outcome == RunOutcome.NEEDS_CLARIFICATION
    assert len(state.clarifying_questions) >= 1


@patch("app.routers.agent_router.datahub_service.execute_mutation", new_callable=AsyncMock)
def test_writeback_approval_workflow_and_idempotency(mock_exec):
    from app.services.datahub.models import MutationOp

    async def _exec(op: MutationOp):
        op.status = "executed"
        return op

    mock_exec.side_effect = _exec

    resp_reject = client.post("/api/v1/runs/test-run-123/writeback/approve", json={"approved": False})
    assert resp_reject.status_code == 400

    from app.routers.agent_router import _RUN_MEMORY_STORE
    _RUN_MEMORY_STORE["test-run-123"] = {
        "run_id": "test-run-123",
        "target_urn": "urn:li:dataset:(snowflake,fct_revenue,PROD)",
        "validation": {"passed": True},
        "writeback_status": "pending_approval",
        "proposed_writeback": {
            "operations": [
                {
                    "op": "update_description",
                    "target_urn": "urn:li:dataset:(snowflake,fct_revenue,PROD)",
                    "params": {"description": "### Synex\n", "operation": "append"},
                    "preview": "Append contract",
                }
            ]
        },
    }

    resp_approve = client.post(
        "/api/v1/runs/test-run-123/writeback/approve",
        json={"approved": True, "approved_by": "Test Engineer"},
    )
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "success"
    assert "mutation_results" in resp_approve.json()

    resp_idempotent = client.post("/api/v1/runs/test-run-123/writeback/approve", json={"approved": True})
    assert resp_idempotent.status_code == 200
    assert resp_idempotent.json()["status"] == "already_approved"


def test_enriched_context_prompt_block_includes_mcp_fields():
    ctx = EnrichedContext(
        urn="urn:li:dataset:(x,y,PROD)",
        name="y",
        owners=["Alice"],
        tags=["CERTIFIED"],
        sample_queries=["SELECT 1"],
        metadata_source="ack",
        previous_sql="SELECT id FROM t",
    )
    block = ctx.to_prompt_block()
    assert "Alice" in block
    assert "CERTIFIED" in block
    assert "SAMPLE_SQL" in block
    assert "PREVIOUS_SESSION_SQL" in block


# --- Phase 3: Context Engine unit tests ---

def test_sql_profiler_extracts_production_patterns():
    from app.context.sql_profiler import profile_queries

    profile = profile_queries([
        """
        WITH base AS (
          SELECT r.id, SUM(r.amount) AS total_revenue
          FROM fct_revenue r
          LEFT JOIN dim_customer c ON r.customer_id = c.id
          WHERE r.order_date >= DATEADD(day, -30, CURRENT_DATE)
          GROUP BY r.id
        )
        SELECT * FROM base
        """
    ])
    assert profile.query_count == 1
    assert any("dim_customer" in t for t in profile.frequently_joined_tables)
    assert profile.common_joins
    assert profile.where_patterns
    assert any("SUM" in a for a in profile.aggregations)
    assert "base" in profile.ctes
    assert profile.date_handling


def test_vocabulary_resolves_revenue_and_customer():
    from app.context.vocabulary import resolve_vocabulary

    mappings = resolve_vocabulary(
        "Build revenue model for customer accounts",
        glossary_terms=["Gross Revenue", "Customer Account"],
        schema_fields=[
            {"fieldPath": "gross_revenue"},
            {"fieldPath": "customer_id"},
        ],
        dataset_name="fct_revenue",
        domain="Finance",
    )
    terms = {m.user_term for m in mappings}
    assert "revenue" in terms or "customer" in terms
    assert any(m.glossary_term or m.canonical_field for m in mappings)


def test_context_ranking_prefers_production_sql():
    from app.context.ranking import score_item, rank_and_filter

    sql_item = score_item("production_sql", "SELECT SUM(revenue) FROM fct_revenue", "revenue model", trust_score=90, is_certified=True)
    weak_doc = score_item("document", "misc note", "revenue model", trust_score=40)
    kept, dropped = rank_and_filter([sql_item, weak_doc], min_score=30)
    assert kept[0].kind == "production_sql"
    assert kept[0].score >= weak_doc.score


def test_context_compression_includes_profile_and_vocab():
    from app.context.compress import compress_package
    from app.context.models import RankedContextItem
    from app.context.pattern_library import PatternLibrary
    from app.context.sql_profiler import profile_queries

    profile = profile_queries(["SELECT id FROM fct_revenue LEFT JOIN dim_date d ON 1=1 WHERE d.ds >= CURRENT_DATE"])
    lib = PatternLibrary()
    lib.ingest_profile(profile)
    block = compress_package(
        prompt="revenue model",
        selected_name="fct_revenue",
        selected_urn="urn:li:dataset:(x,fct_revenue,PROD)",
        schema_fields=[{"fieldPath": "id", "nativeDataType": "VARCHAR"}],
        pii_fields=[],
        sql_profile=profile,
        pattern_library=lib,
        vocabulary_block="=== BUSINESS VOCABULARY ===\n  revenue → Gross Revenue",
        kept_items=[
            RankedContextItem(kind="glossary", content="Gross Revenue", score=80),
            RankedContextItem(kind="document", content="Use fct_revenue", score=70),
        ],
        ownership={"summary": "Finance Lead"},
        domain="Finance",
        trust_breakdown={"overall": 88},
        warnings=[],
        lineage_summary="up=1 down=2",
        quality_summary="pass",
        validation_rules=["Hash PII"],
        engineering_memory={},
    )
    assert "PRODUCTION SQL PROFILE" in block
    assert "BUSINESS VOCABULARY" in block
    assert "SQL PATTERN LIBRARY" in block
    assert "SCHEMA_FIELDS" in block


def test_sql_explanation_cites_evidence():
    from app.context.explanation import build_sql_explanation
    from app.context.models import ContextManifest, ContextPackage, SqlProfile

    pkg = ContextPackage(
        prompt="revenue",
        selected_urn="urn:x",
        selected_name="fct_revenue",
        sql_profile=SqlProfile(query_count=1, sample_queries=["SELECT 1"], common_joins=["LEFT JOIN dim_customer"]),
        documents=["rev docs"],
        glossary=[{"name": "Revenue"}],
        institutional_memory=["use certified"],
        pattern_library_hints=["JOIN: LEFT JOIN dim_customer"],
        context_sources=["ack"],
        trust_breakdown={"overall": 90},
        manifest=ContextManifest(production_sql_examples=1, documentation_pages=1, glossary_definitions=1, trust_score=90),
    )
    expl = build_sql_explanation(pkg, sql="SELECT * FROM fct_revenue LEFT JOIN dim_customer")
    assert "fct_revenue" in expl["why_dataset"]
    assert expl["production_sql_influence"]
    assert expl["summary"]


@pytest.mark.asyncio
async def test_context_engine_build_low_docs_fallback():
    from app.context.engine import ContextEngine
    from unittest.mock import AsyncMock, patch

    enriched = EnrichedContext(
        urn="urn:li:dataset:(s,fct_revenue,PROD)",
        name="fct_revenue",
        schema_fields=[{"fieldPath": "id", "nativeDataType": "VARCHAR"}],
        owners=["Owner A"],
        glossary_terms=["Revenue"],
        metadata_source="ack",
        sample_queries=[],
        documents=[],
        institutional_memory=[],
    )
    selected = {
        "urn": enriched.urn,
        "name": enriched.name,
        "trust_score": 82,
        "is_certified": True,
        "is_deprecated": False,
        "pii_fields": [],
        "owners": ["Owner A"],
        "glossary_terms": ["Revenue"],
        "recommendation": "preferred",
    }
    with patch("app.context.engine.datahub_service.get_dataset_queries", new_callable=AsyncMock) as mq, \
         patch("app.context.engine.datahub_service.search_documents", new_callable=AsyncMock) as md, \
         patch("app.context.engine.datahub_service.grep_documents", new_callable=AsyncMock) as mg:
        mq.return_value = ["SELECT id FROM fct_revenue"]
        md.return_value = []
        mg.return_value = []
        pkg = await ContextEngine().build(
            prompt="Create revenue model for Finance",
            selected=selected,
            enriched=enriched,
            lineage_report={"upstream": [], "downstream": [], "safer_choice_reason": "certified"},
            quality_report={"validation_status": "pass"},
            candidate_evaluations=[selected],
        )
    assert pkg.sql_profile and pkg.sql_profile.query_count >= 1
    assert pkg.manifest
    assert pkg.compressed_prompt_block
    assert "PRODUCTION SQL PROFILE" in pkg.compressed_prompt_block


# --- Phase 4: resilience / memory / confidence ---

def test_engineering_memory_merges_prior_run():
    from app.memory.engineering_memory import build_engineering_memory, memory_to_prompt_section

    mem = build_engineering_memory(
        previous_run={
            "sql": "SELECT id FROM fct_revenue",
            "status": "SUCCESS",
            "target_urn": "urn:x",
            "target_name": "fct_revenue",
            "dbt_yaml": "version: 2",
        },
        prior_memory={"preferred_joins": ["LEFT JOIN dim_customer"], "validation_failures": ["old err"]},
    )
    assert mem["previous_sql"]
    assert "fct_revenue" in mem["preferred_datasets"]
    assert mem["preferred_joins"]
    block = memory_to_prompt_section(mem)
    assert "ENGINEERING MEMORY" in block
    assert "PREVIOUS_SQL" in block


def test_model_selector_chooses_fast_for_simple_and_large_for_complex():
    from app.llm.model_selector import select_model
    from types import SimpleNamespace

    simple = select_model(prompt="hi", provider="openrouter", default_model="openai/gpt-4o", task="generation")
    complex_ = select_model(
        prompt="Build an incremental SCD Type-2 dbt mart with PII masking and multi-hop lineage joins for aggregation windows",
        intent=SimpleNamespace(risk_level="high", desired_artifact="dbt_sql_and_schema_yml", required_metadata=["a", "b", "c", "d", "e"]),
        provider="openrouter",
        default_model="openai/gpt-4o",
    )
    critique = select_model(prompt="x", provider="openrouter", task="critique")
    assert simple.task in ("simple", "generation")
    assert complex_.task == "complex"
    assert critique.task == "critique"
    assert "mini" in critique.model or "haiku" in critique.model or "flash" in critique.model or "8b" in critique.model


def test_confidence_engine_high_when_validation_and_trust():
    from app.llm.confidence import compute_confidence
    from app.context.models import ContextPackage, SqlProfile

    pkg = ContextPackage(
        prompt="revenue",
        selected_name="fct_revenue",
        selected_urn="urn:x",
        schema_fields=[{"fieldPath": "id"}] * 6,
        glossary=[{"name": "Revenue"}],
        documents=["doc"],
        sql_profile=SqlProfile(query_count=2),
        ownership={"all_owners": ["A"]},
        ranked_items=[],
    )
    conf = compute_confidence(
        selected={"trust_score": 90, "owners": ["A"], "trust_dimensions": {"lineage_confidence": 80}},
        validation={"passed": True},
        context_package=pkg,
        engineering_memory={"previous_sql": "SELECT 1"},
        critique={"approved": True},
        retry_count=0,
    )
    assert conf["score"] >= 65
    assert conf["level"] in ("high", "medium")
    assert conf["summary"]


def test_deterministic_critique_flags_validation_failure():
    from app.llm.critique import critique_artifacts

    critique = critique_artifacts(
        sql="SELECT customer_email FROM t",
        dbt_yaml="version: 2",
        prompt="model",
        schema_fields=[{"fieldPath": "customer_email"}],
        pii_fields=["customer_email"],
        validation={"passed": False, "blocking_errors": ["Raw unmasked PII detected"]},
        api_key="",
        provider="openrouter",
        model="x",
        use_llm=False,
    )
    assert critique["needs_revision"] is True
    assert critique["approved"] is False


def test_provider_fallback_chain_orders_primary_first():
    from app.llm.providers import LLMProviderRouter

    router = LLMProviderRouter()
    chain = router.fallback_chain("openrouter", "openai/gpt-4o", api_key="sk-test", task="generation")
    assert chain[0]["provider"] == "openrouter"
    assert chain[0]["model"] == "openai/gpt-4o"
