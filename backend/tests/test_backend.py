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

@patch("app.routers.agent_router.datahub_context.search_candidates")
@patch("app.routers.agent_router.datahub_context.get_entity_metadata")
@patch("app.routers.agent_router.datahub_context.get_upstream_lineage")
@patch("app.routers.agent_router.datahub_context.get_downstream_lineage")
@patch("app.routers.agent_router.generator.generate_code_and_contract")
def test_run_endpoint_never_writes_directly(
    mock_gen, mock_down, mock_up, mock_meta, mock_search
):
    mock_search.return_value = [{"urn": "urn:li:dataset:(snowflake,fct_revenue,PROD)", "name": "fct_revenue"}]
    mock_meta.return_value = {
        "urn": "urn:li:dataset:(snowflake,fct_revenue,PROD)",
        "name": "fct_revenue",
        "schemaMetadata": {"fields": [{"fieldPath": "id", "nativeDataType": "VARCHAR"}]},
        "tags": {"tags": [{"tag": {"name": "CERTIFIED"}}]},
    }
    mock_up.return_value = []
    mock_down.return_value = []
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

    response = client.post("/api/v1/run", json={"prompt": "Create revenue model"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["proposed_writeback"]["requires_approval"] is True


@patch("app.routers.agent_router.mcp_emitter.emit_documentation_update")
def test_writeback_approval_workflow_and_idempotency(mock_emit):
    mock_emit.return_value = True

    # 1. Reject without explicit approved=True
    resp_reject = client.post("/api/v1/runs/test-run-123/writeback/approve", json={"approved": False})
    assert resp_reject.status_code == 400

    # 2. Seed memory store with passing run
    from app.routers.agent_router import _RUN_MEMORY_STORE
    _RUN_MEMORY_STORE["test-run-123"] = {
        "run_id": "test-run-123",
        "target_urn": "urn:li:dataset:(snowflake,fct_revenue,PROD)",
        "validation": {"passed": True},
        "writeback_status": "pending_approval",
    }

    # 3. Approve successfully
    resp_approve = client.post("/api/v1/runs/test-run-123/writeback/approve", json={"approved": True, "approved_by": "Test Engineer"})
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "success"

    # 4. Check Idempotency (Second approval returns already_approved)
    resp_idempotent = client.post("/api/v1/runs/test-run-123/writeback/approve", json={"approved": True})
    assert resp_idempotent.status_code == 200
    assert resp_idempotent.json()["status"] == "already_approved"
