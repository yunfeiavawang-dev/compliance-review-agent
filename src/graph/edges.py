"""Conditional edge logic for the KYC compliance review workflow."""

from __future__ import annotations
from src.graph.state import ReviewState


def route_after_intake(state: ReviewState) -> str:
    """After intake, proceed to screening if basic ID docs exist.

    Even if some documents are missing, we continue the review to identify
    all issues holistically rather than blocking at the first gap.
    Missing docs are recorded in findings and may trigger request_more_info later.
    """
    submission = state.get("submission", {})
    id_docs = submission.get("identification_documents", [])
    has_any_id = any(
        d.get("verified") or d.get("provided")
        for d in id_docs
        if d.get("type") in ("passport", "national_id", "driver_license")
    )
    if has_any_id:
        return "identity_screening"
    return "request_info"


def route_after_screening(state: ReviewState) -> str:
    """After screening, check for immediate escalation or proceed to risk assessment."""
    if state.get("sanctions_result") == "confirmed_match":
        return "request_info"
    return "risk_assessment"


def route_after_risk_assessment(state: ReviewState) -> str:
    """After risk assessment, route to standard review or EDD based on risk rating."""
    rating = state.get("risk_rating", "medium")
    if rating == "high":
        return "enhanced_due_diligence"
    return "standard_review"


def route_after_review(state: ReviewState) -> str:
    """After standard review or EDD, route to human review or request info."""
    decision = state.get("decision", "")
    if decision == "request_more_info":
        return "request_info"
    return "human_review"


def route_after_human_review(state: ReviewState) -> str:
    """After human review, finalize or loop back."""
    human_decision = state.get("human_decision")
    if human_decision == "request_more_info":
        return "request_info"
    return "decision"
