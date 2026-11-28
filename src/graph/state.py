"""LangGraph state schema for the KYC compliance review workflow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional
from typing_extensions import TypedDict


class ReviewState(TypedDict, total=False):
    """Shared state flowing through the KYC review graph.

    Every node reads from and writes to this state.
    """
    # Case identification
    case_id: str
    review_id: str
    customer_id: str

    # Enterprise: multi-tenant isolation & data classification
    # In production, tenant_id is injected from the SSO token and used to
    # partition all database queries — no cross-tenant data leakage.
    tenant_id: str  # e.g. "pacific_rim_fg", "acme_bank_hk"
    data_classification: str  # "public" | "internal" | "confidential" | "restricted"

    # Raw submission data
    submission: dict

    # Document completeness
    documents_complete: bool
    missing_documents: list[str]
    document_verification: list[dict]

    # Intake three-level classification
    intake_status: str  # "blocked", "conditional", "complete"
    critical_missing: list[str]
    non_critical_missing: list[str]

    # Screening results
    sanctions_result: str  # "clear", "potential_match", "confirmed_match"
    pep_result: str
    adverse_media_result: str
    screening_details: list[dict]

    # Risk assessment
    risk_scores: dict  # individual factor scores
    risk_total: int
    risk_rating: str  # "low", "medium", "high"
    risk_override: Optional[str]
    risk_override_reason: Optional[str]

    # Due diligence
    due_diligence_level: str  # "standard", "enhanced"
    edd_findings: Optional[dict]
    # Mandatory EDD documents still outstanding (set by edd_document_check)
    edd_missing_docs: list[str]
    # True when outstanding EDD docs did NOT block the case because a red flag
    # (potential/confirmed sanctions or PEP match) must reach EDD/escalation.
    edd_docs_bypassed: bool

    # Review findings
    findings: list[str]
    recommendations: list[str]
    sources_cited: list[dict]

    # Decision
    decision: Optional[str]  # "approve", "reject", "request_more_info", "escalate"
    decision_rationale: Optional[str]

    # Human review
    human_review_required: bool
    human_decision: Optional[str]
    human_notes: Optional[str]

    # AI confidence and agreement tracking
    ai_confidence: Optional[float]  # 0.0-1.0 confidence in recommendation
    ai_human_agreement: Optional[bool]  # whether AI and human decisions match
    review_status: str  # "pending", "in_review", "completed"

    # Workflow control
    current_step: str
    next_step: Optional[str]
    info_requests: list[str]
    # Request-info loop: the node that asked for information. After the
    # supplement arrives the graph resumes AT that node (not at intake).
    info_request_stage: str
    info_request_round: int
    info_round_exceeded: bool  # True once MAX_INFO_REQUEST_ROUNDS is hit

    # Audit trail — append-only. The reducer makes the framework concatenate
    # whatever a node returns onto the existing list, so a node can never
    # overwrite earlier entries. Nodes therefore return ONLY their new entries.
    audit_trail: Annotated[list[dict], operator.add]

    # Long-term memory: bank-wide customer behavior profile (pulled once at intake)
    customer_profile: Optional[dict]
    customer_profile_summary: Optional[str]
    is_existing_customer: bool

    # Error handling
    error: Optional[str]
