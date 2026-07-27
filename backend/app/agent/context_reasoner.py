"""Graph-Aware Context Reasoner for Synex.

Ranks and scores dataset candidates deterministically using DataHub metadata graph signals:
certification status, deprecation, ownership, domain/glossary terms, quality signals,
PII tags, upstream lineage risks, and downstream blast radius.
"""

import re
from typing import Any, Dict, List, Tuple


class ContextReasoner:
    """Evaluates and ranks dataset candidates based on DataHub graph governance signals."""

    def evaluate_candidate(
        self,
        candidate_metadata: Dict[str, Any],
        user_prompt: str,
        upstream_nodes: List[Dict[str, Any]] | None = None,
        downstream_nodes: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """Score a single candidate dataset and produce selection/rejection reasons."""
        urn = candidate_metadata.get("urn", "")
        name = candidate_metadata.get("name") or urn.split(":")[-1]
        
        # 1. Deprecation Status
        deprecation_info = candidate_metadata.get("deprecation") or {}
        is_deprecated = bool(deprecation_info.get("deprecated", False))

        # 2. Certification & Trust Tags
        tags_raw = candidate_metadata.get("tags", {}).get("tags", [])
        tag_names = [t.get("tag", {}).get("name", "").upper() for t in tags_raw if t.get("tag")]
        is_certified = any("CERTIFIED" in t or "VERIFIED" in t or "APPROVED" in t or "TRUSTED" in t for t in tag_names)

        # 3. Ownership & Domain
        owners_raw = candidate_metadata.get("ownership", {}).get("owners", [])
        owners = [
            o.get("owner", {}).get("properties", {}).get("displayName") or o.get("owner", {}).get("urn", "")
            for o in owners_raw if o.get("owner")
        ]
        domain_info = candidate_metadata.get("domain", {}).get("domain", {})
        domain = domain_info.get("properties", {}).get("name") if domain_info else None

        # 4. Glossary Terms
        terms_raw = candidate_metadata.get("glossaryTerms", {}).get("terms", [])
        glossary_terms = [
            t.get("term", {}).get("properties", {}).get("name") or t.get("term", {}).get("urn", "")
            for t in terms_raw if t.get("term")
        ]

        # 5. Quality & Health Signals
        health_info = candidate_metadata.get("health") or []
        quality_signals = []
        if isinstance(health_info, list):
            for h in health_info:
                if h.get("type"):
                    quality_signals.append(f"{h.get('type')}: {h.get('status', 'OK')}")
        elif isinstance(health_info, dict) and health_info.get("type"):
            quality_signals.append(f"{health_info.get('type')}: {health_info.get('status', 'OK')}")

        # 6. PII Fields Identification
        fields = candidate_metadata.get("schemaMetadata", {}).get("fields", [])
        pii_fields = []
        pii_pattern = re.compile(r"(email|e_mail|phone|mobile|ssn|social_security|credit_?card|passport|dob|date_?of_?birth|address|salary|revenue)", re.I)
        
        for field in fields:
            f_path = field.get("fieldPath", "")
            f_tags = [t.get("tag", {}).get("name", "").upper() for t in field.get("tags", {}).get("tags", []) if t.get("tag")]
            if any("PII" in t or "SENSITIVE" in t or "CONFIDENTIAL" in t for t in f_tags):
                pii_fields.append(f_path)
            elif pii_pattern.search(f_path) or pii_pattern.search(field.get("description") or ""):
                pii_fields.append(f_path)

        pii_fields = sorted(list(set(pii_fields)))

        # 7. Upstream Lineage Risks
        upstream_nodes = upstream_nodes or []
        upstream_risks = []
        for node in upstream_nodes:
            if node.get("deprecation", {}).get("deprecated"):
                upstream_risks.append(f"Upstream dataset '{node.get('name') or node.get('urn')}' is deprecated.")
            u_tags = [t.get("tag", {}).get("name", "").upper() for t in node.get("tags", {}).get("tags", []) if t.get("tag")]
            if any("PII" in t or "SENSITIVE" in t for t in u_tags):
                upstream_risks.append(f"Upstream dataset '{node.get('name') or node.get('urn')}' contains sensitive PII.")

        # 8. Downstream Blast Radius
        downstream_nodes = downstream_nodes or []
        downstream_impact_count = len(downstream_nodes)

        # 9. Deterministic Trust Scoring
        trust_score = 50  # Base score
        selection_reasons: List[str] = []
        rejection_reasons: List[str] = []

        if is_certified:
            trust_score += 30
            selection_reasons.append("Certified / trusted dataset banner attached in DataHub.")
        else:
            rejection_reasons.append("Missing official DataHub certification tag.")

        if not is_deprecated:
            trust_score += 20
            selection_reasons.append("Active, non-deprecated dataset.")
        else:
            trust_score -= 50
            rejection_reasons.append("Dataset is explicitly flagged as DEPRECATED in DataHub.")

        if owners:
            trust_score += 15
            selection_reasons.append(f"Assigned data owners: {', '.join(owners)}.")
        else:
            rejection_reasons.append("Unassigned ownership in DataHub governance graph.")

        if domain:
            trust_score += 10
            selection_reasons.append(f"Assigned domain: {domain}.")

        if glossary_terms:
            trust_score += 10
            selection_reasons.append(f"Mapped glossary terms: {', '.join(glossary_terms)}.")

        # Check prompt relevance to schema / fields
        prompt_words = set(re.findall(r"\w+", user_prompt.lower()))
        matched_fields = [f.get("fieldPath") for f in fields if any(w in f.get("fieldPath", "").lower() for w in prompt_words if len(w) > 3)]
        if matched_fields:
            trust_score += 15
            selection_reasons.append(f"Matched {len(matched_fields)} schema fields to user request intent.")

        if upstream_risks:
            trust_score -= 15
            rejection_reasons.append(f"Upstream lineage risk detected: {'; '.join(upstream_risks)}.")

        if downstream_impact_count > 0:
            selection_reasons.append(f"Downstream usage verified across {downstream_impact_count} dependent models.")

        # Clamp trust score 0 - 100
        trust_score = max(0, min(100, trust_score))

        return {
            "urn": urn,
            "name": name,
            "trust_score": trust_score,
            "is_deprecated": is_deprecated,
            "is_certified": is_certified,
            "owners": owners,
            "domain": domain,
            "glossary_terms": glossary_terms,
            "quality_signals": quality_signals,
            "pii_fields": pii_fields,
            "upstream_risks": upstream_risks,
            "downstream_impact_count": downstream_impact_count,
            "selection_reasons": selection_reasons,
            "rejection_reasons": rejection_reasons,
        }

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        user_prompt: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Rank all candidate datasets and return (selected_candidate, candidate_evaluations)."""
        evaluations = []
        for cand in candidates:
            eval_res = self.evaluate_candidate(cand, user_prompt)
            evaluations.append(eval_res)

        # Sort candidates descending by trust_score
        evaluations.sort(key=lambda x: x["trust_score"], reverse=True)
        selected = evaluations[0] if evaluations else {}
        return selected, evaluations


context_reasoner = ContextReasoner()
