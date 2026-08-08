"""Shared workflow DTOs for Synex's autonomous Data Engineering engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class RunOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


@dataclass
class WorkflowStep:
    """One observable stage in the engineering workflow."""

    id: str
    name: str
    label: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_ms: Optional[int] = None
    message: str = ""
    logs: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    reasoning_summary: str = ""
    trust_score: Optional[float] = None

    def start(self, message: str = "") -> None:
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()
        if message:
            self.message = message
            self.logs.append(message)

    def complete(
        self,
        message: str = "",
        outputs: Optional[dict[str, Any]] = None,
        warnings: Optional[list[str]] = None,
        reasoning_summary: str = "",
        trust_score: Optional[float] = None,
    ) -> None:
        self.status = StepStatus.COMPLETED
        self.ended_at = datetime.now(timezone.utc).isoformat()
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.ended_at)
            self.duration_ms = int((end - start).total_seconds() * 1000)
        if message:
            self.message = message
            self.logs.append(message)
        if outputs:
            self.outputs = outputs
        if warnings:
            self.warnings.extend(warnings)
        if reasoning_summary:
            self.reasoning_summary = reasoning_summary
        if trust_score is not None:
            self.trust_score = trust_score

    def fail(self, error: str) -> None:
        self.status = StepStatus.FAILED
        self.ended_at = datetime.now(timezone.utc).isoformat()
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.ended_at)
            self.duration_ms = int((end - start).total_seconds() * 1000)
        self.message = error
        self.errors.append(error)
        self.logs.append(f"ERROR: {error}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, StepStatus) else self.status
        return d

    def to_sse_event(self, step_index: int) -> dict[str, Any]:
        return {
            "step": step_index,
            "type": f"WORKFLOW_{self.id.upper()}",
            "stage": self.id,
            "stage_label": self.label,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "warnings": self.warnings,
            "errors": self.errors,
            "reasoning_summary": self.reasoning_summary,
            "trust_score": self.trust_score,
            "outputs_preview": _preview(self.outputs),
            "workflow_step": self.to_dict(),
        }


def _preview(outputs: dict[str, Any], max_keys: int = 8) -> dict[str, Any]:
    if not outputs:
        return {}
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(outputs.items()):
        if i >= max_keys:
            break
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, list):
            out[k] = f"[{len(v)} items]"
        elif isinstance(v, dict):
            out[k] = f"{{{len(v)} keys}}"
        else:
            out[k] = str(type(v).__name__)
    return out


@dataclass
class IntentResult:
    intent: str = "generate_dbt_model"
    target_dataset_hint: Optional[str] = None
    business_domain: Optional[str] = None
    desired_artifact: str = "dbt_sql_and_schema_yml"
    risk_level: str = "medium"  # low | medium | high
    required_metadata: list[str] = field(default_factory=list)
    confidence: float = 0.7
    ambiguous: bool = False
    clarifying_questions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrustDimensions:
    ownership: float = 0.0
    certification: float = 0.0
    documentation: float = 0.0
    quality: float = 0.0
    freshness: float = 0.0
    popularity: float = 0.0
    schema_completeness: float = 0.0
    pii_governance: float = 0.0
    glossary_coverage: float = 0.0
    business_relevance: float = 0.0
    lineage_confidence: float = 0.0
    usage_statistics: float = 0.0

    def overall(self) -> float:
        vals = list(asdict(self).values())
        return round(sum(vals) / len(vals), 1) if vals else 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EngineeringContext:
    """The ONLY context package passed to the LLM generator."""

    business_context: str = ""
    schema_fields: list[dict[str, Any]] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    ownership: list[str] = field(default_factory=list)
    glossary: list[str] = field(default_factory=list)
    documentation: list[str] = field(default_factory=list)
    sample_sql: list[str] = field(default_factory=list)
    usage: list[str] = field(default_factory=list)
    validation_rules: list[str] = field(default_factory=list)
    governance: dict[str, Any] = field(default_factory=dict)
    recommended_joins: list[str] = field(default_factory=list)
    pii_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trust_scores: dict[str, Any] = field(default_factory=dict)
    reasoning_summary: str = ""
    selected_urn: str = ""
    selected_name: str = ""
    platform: str = ""
    domain: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    institutional_memory: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    previous_sql: Optional[str] = None
    metadata_source: str = "ack"
    plan: list[dict[str, Any]] = field(default_factory=list)
    # Phase-3 context engine fields
    context_manifest: dict[str, Any] = field(default_factory=dict)
    sql_profile: dict[str, Any] = field(default_factory=dict)
    vocabulary: list[dict[str, Any]] = field(default_factory=list)
    pattern_library_hints: list[str] = field(default_factory=list)
    context_sources: list[str] = field(default_factory=list)
    prompt_version: str = "synex-context-v3"
    compressed_block: str = ""

    def to_prompt_block(self) -> str:
        if self.compressed_block:
            return self.compressed_block
        lines = [
            "=== SYNEX ENGINEERING CONTEXT (authoritative — do not invent beyond this) ===",
            f"DATASET: {self.selected_name}",
            f"URN: {self.selected_urn}",
            f"PLATFORM: {self.platform or 'unknown'}",
            f"DOMAIN: {self.domain or '(none)'}",
            f"METADATA_SOURCE: {self.metadata_source}",
            f"BUSINESS_CONTEXT: {self.business_context or '(none)'}",
            f"OWNERS: {', '.join(self.ownership) or '(none)'}",
            f"GLOSSARY: {', '.join(self.glossary) or '(none)'}",
            f"TAGS: {', '.join(self.tags) or '(none)'}",
            f"PII_FIELDS: {', '.join(self.pii_fields) or '(none)'}",
            f"TRUST: {self.trust_scores}",
            f"REASONING: {self.reasoning_summary}",
        ]
        if self.warnings:
            lines.append("WARNINGS:")
            for w in self.warnings[:12]:
                lines.append(f"  - {w}")
        if self.quality:
            lines.append(f"QUALITY: {self.quality}")
        if self.lineage:
            up = self.lineage.get("upstream_names") or []
            down = self.lineage.get("downstream_names") or []
            lines.append(f"UPSTREAM: {', '.join(up[:8]) or '(none)'}")
            lines.append(f"DOWNSTREAM: {', '.join(down[:8]) or '(none)'}")
            if self.lineage.get("safer_choice_reason"):
                lines.append(f"LINEAGE_SAFETY: {self.lineage['safer_choice_reason']}")
        if self.sample_sql:
            lines.append("SAMPLE_SQL:")
            for q in self.sample_sql[:3]:
                lines.append(f"  ---\n  {q[:800]}")
        if self.documentation:
            lines.append("DOCUMENTATION:")
            for d in self.documentation[:5]:
                lines.append(f"  - {d[:300]}")
        if self.institutional_memory:
            lines.append("INSTITUTIONAL_MEMORY:")
            for m in self.institutional_memory[:5]:
                lines.append(f"  - {m[:300]}")
        if self.assertions:
            lines.append(f"ASSERTIONS: {'; '.join(self.assertions[:8])}")
        if self.recommended_joins:
            lines.append("RECOMMENDED_JOINS:")
            for j in self.recommended_joins[:6]:
                lines.append(f"  - {j}")
        if self.validation_rules:
            lines.append("VALIDATION_RULES:")
            for r in self.validation_rules[:8]:
                lines.append(f"  - {r}")
        if self.plan:
            lines.append("ENGINEERING_PLAN:")
            for p in self.plan:
                lines.append(f"  {p.get('step')}. {p.get('type')}: {p.get('description')}")
        if self.previous_sql:
            lines.append("PREVIOUS_SESSION_SQL:")
            lines.append(self.previous_sql[:4000])
        if self.schema_fields:
            lines.append("SCHEMA_FIELDS:")
            for f in self.schema_fields:
                path = f.get("fieldPath", "")
                dtype = f.get("nativeDataType", "VARCHAR")
                desc = f.get("description") or ""
                lines.append(f"  - {path} ({dtype}): {desc}")
        lines.append("=== END ENGINEERING CONTEXT ===")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowState:
    """Mutable state threaded through all workflow stages."""

    prompt: str
    run_id: str
    target_dialect: str = "snowflake"
    allow_deprecated_override: bool = False
    session_id: Optional[str] = None
    previous_sql: Optional[str] = None
    previous_validation_summary: Optional[str] = None
    llm_api_key: str = ""
    llm_model: str = ""
    llm_provider: str = "openrouter"

    intent: Optional[IntentResult] = None
    raw_candidates: list[dict[str, Any]] = field(default_factory=list)
    search_source: str = "ack"
    candidate_evaluations: list[dict[str, Any]] = field(default_factory=list)
    selected_candidate: Optional[dict[str, Any]] = None
    lineage_report: dict[str, Any] = field(default_factory=dict)
    quality_report: dict[str, Any] = field(default_factory=dict)
    enrichment: dict[str, Any] = field(default_factory=dict)
    enriched_ctx: Any = None  # EnrichedContext
    engineering_context: Optional[EngineeringContext] = None
    plan: list[dict[str, Any]] = field(default_factory=list)
    generated: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    proposed_writeback: dict[str, Any] = field(default_factory=dict)
    clarifying_questions: list[str] = field(default_factory=list)
    outcome: RunOutcome = RunOutcome.SUCCESS
    steps: list[WorkflowStep] = field(default_factory=list)
    global_warnings: list[str] = field(default_factory=list)
    # Phase-3
    context_package: Any = None
    sql_explanation: dict[str, Any] = field(default_factory=dict)
    engineering_memory: dict[str, Any] = field(default_factory=dict)
    context_manifest: dict[str, Any] = field(default_factory=dict)
    # Phase-4
    observability: Any = None
    self_critique: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0

    def step_dicts(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.steps]
