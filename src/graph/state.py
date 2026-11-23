"""LangGraph state schema for the KYC compliance review workflow."""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict


class ReviewState(TypedDict, total=False):
    """Shared state flowing through the KYC review graph.

    Every node reads from and writes to this state.
    """
    # Case identification
    case_id: str
    review_id: str
    customer_id: str

    # Raw submission data
    submission: dict

    # Document completeness
    documents_complete: bool
    missing_documents: list[str]
    document_verification: list[dict]

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

    # Workflow control
    current_step: str
    next_step: Optional[str]
    info_requests: list[str]

    # Audit trail
    audit_trail: list[dict]

    # Error handling
    error: Optional[str]
