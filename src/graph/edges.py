"""Conditional edge logic for the KYC compliance review workflow."""

from __future__ import annotations
from src.graph.state import ReviewState

# After this many request-info rounds the case stops looping and is handed to a
# human reviewer with an "escalate" recommendation instead of asking again.
MAX_INFO_REQUEST_ROUNDS = 3

# Screening results that count as a red flag. A red-flag case must reach EDD /
# escalation even if mandatory EDD documents are still outstanding.
RED_FLAG_RESULTS = {"potential_match", "confirmed_match"}

# Nodes that may issue a request for information, and therefore must be
# resumable once the information arrives.
RESUMABLE_STAGES = {
    "intake",
    "identity_screening",
    "edd_document_check",
    "enhanced_due_diligence",
    "standard_review",
    "human_review",
}


def has_red_flag(state: ReviewState) -> bool:
    """Potential/confirmed sanctions or PEP match."""
    return (
        state.get("sanctions_result") in RED_FLAG_RESULTS
        or state.get("pep_result") in RED_FLAG_RESULTS
    )


def route_after_intake(state: ReviewState) -> str:
    """After intake, route based on three-level document classification.

    - blocked: critical documents missing → request_info
    - conditional: non-critical docs missing → screening (with risk flag)
    - complete: all documents present → screening
    """
    intake_status = state.get("intake_status", "complete")
    if intake_status == "blocked":
        return "request_info"
    return "identity_screening"


def route_after_screening(state: ReviewState) -> str:
    """After screening, check for immediate escalation or proceed to risk assessment."""
    if state.get("sanctions_result") == "confirmed_match":
        return "request_info"
    return "risk_assessment"


def route_after_risk_assessment(state: ReviewState) -> str:
    """After risk assessment, high risk goes through the EDD document gate;
    everything else goes to standard review."""
    rating = state.get("risk_rating", "medium")
    if rating == "high":
        return "edd_document_check"
    return "standard_review"


def route_after_edd_document_check(state: ReviewState) -> str:
    """EDD document gate.

    - nothing outstanding            → EDD
    - outstanding + red flag         → EDD anyway (never delay an escalation;
                                       the gaps are carried into EDD as conditions)
    - outstanding + no red flag      → request_info (ask before spending EDD effort)
    """
    if state.get("edd_missing_docs") and not state.get("edd_docs_bypassed"):
        return "request_info"
    return "enhanced_due_diligence"


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


def route_after_request_info(state: ReviewState) -> str:
    """Pause for the supplement, unless the loop has hit its round limit — in
    that case hand the case to a human instead of asking again."""
    if state.get("info_round_exceeded"):
        return "human_review"
    return "await_info"


def resume_target(state: ReviewState) -> str:
    """Node to resume at once the requested information has arrived.

    The graph returns to the node that asked for the information, so earlier
    results (screening, risk rating, ...) are reused rather than recomputed.
    """
    stage = state.get("info_request_stage", "")
    if stage == "human_review":
        # human_review is a passthrough; the new information must be analysed
        # again by the review node that produced the recommendation.
        return "enhanced_due_diligence" if state.get("risk_rating") == "high" else "standard_review"
    if stage in RESUMABLE_STAGES:
        return stage
    return "intake"


def route_after_await_info(state: ReviewState) -> str:
    return resume_target(state)
