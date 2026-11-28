"""Auto-categorize closed cases and generate wiki entry drafts.

This module demonstrates a weekly batch job concept: after each review
cycle, closed cases are classified by scenario type and formatted as
draft wiki entries for human review before publication.

Design: uses simple keyword matching for topic classification (no LLM
call needed for the demo). In production, this could use an LLM to
generate richer summaries, but keyword matching keeps it deterministic
and auditable — important for compliance operations.

Usage (batch):
    from src.knowledge.wiki_builder import build_weekly_wiki_updates
    updates = build_weekly_wiki_updates(closed_cases)
    # updates: {"expired_documents": [...], "sanctions_potential_match": [...], ...}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


# Topic classification rules: keyword sets mapped to wiki slugs
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "expired_documents": [
        "expired", "expiry", "near-expiry", "approaching expiry",
        "document validity", "expired passport", "expired utility",
        "doc_issue", "document_date",
    ],
    "sanctions_potential_match": [
        "sanctions", "sanction", "sanctioned", "OFAC", "EU sanctions",
        "UN sanctions", "potential_match", "confirmed_match",
        "sanctions_screening", "fuzzy match", "transliteration",
        "matched_list", "match_confidence",
    ],
    "pep_with_mitigants": [
        "PEP", "pep_status", "politically exposed", "former minister",
        "government official", "cooling-off", "retired from politics",
        "pep_screening", "domestic PEP", "foreign PEP",
    ],
    "cross_border_corporate": [
        "corporate", "cross-border", "multi-jurisdiction", "subsidiary",
        "holding company", "beneficial_ownership", "nominee",
        "certificate_of_incorporation", "board_resolution",
        "shell company", "offshore",
    ],
}


def classify_case(case_state: dict) -> Optional[str]:
    """Classify a closed case into a wiki topic by keyword matching.

    Scans findings, decision rationale, screening flags, and customer
    type for topic keywords. Returns the best-matching topic slug,
    or None if no topic matches strongly enough.
    """
    text_parts = []

    for finding in case_state.get("findings", []):
        text_parts.append(str(finding).lower())

    rationale = case_state.get("decision_rationale", "")
    if rationale:
        text_parts.append(rationale.lower())

    submission = case_state.get("submission", {})
    flags = submission.get("screening_flags", {})
    for flag_data in flags.values():
        if isinstance(flag_data, dict):
            text_parts.append(str(flag_data.get("result", "")).lower())
            text_parts.append(str(flag_data.get("details", "")).lower())

    customer = submission.get("customer", {})
    if customer.get("type") == "corporate":
        text_parts.append("corporate")

    decl = submission.get("declarations", {})
    if decl.get("pep_status"):
        text_parts.append("pep pep_status politically exposed")

    combined = " ".join(text_parts)

    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in combined)
        if score > 0:
            scores[topic] = score

    if not scores:
        return None
    return max(scores, key=scores.get)


def generate_wiki_entry(case_state: dict) -> tuple[Optional[str], str]:
    """Generate a draft wiki entry from a closed case.

    Returns (topic_slug, formatted_markdown). If no topic matches,
    topic_slug is None and markdown is a generic entry.
    """
    topic = classify_case(case_state)

    case_id = case_state.get("case_id", "UNKNOWN")
    decision = case_state.get("decision", "N/A")
    risk_rating = case_state.get("risk_rating", "N/A")
    risk_score = case_state.get("risk_total", 0)

    submission = case_state.get("submission", {})
    customer = submission.get("customer", {})
    customer_type = customer.get("type", "individual")
    nationality = customer.get("nationality", customer.get("country_of_incorporation", "N/A"))

    findings_summary = []
    for f in case_state.get("findings", [])[:3]:
        text = str(f)
        if len(text) > 120:
            text = text[:117] + "..."
        findings_summary.append(f"  - {text}")

    conditions = case_state.get("recommendations", [])
    conditions_text = "; ".join(str(c) for c in conditions[:3]) if conditions else "None"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = (
        f"### Case Pattern: {case_id} ({now})\n\n"
        f"- **Profile:** {customer_type.title()}, {nationality}\n"
        f"- **Risk:** {risk_rating.upper()} (score {risk_score})\n"
        f"- **Decision:** {decision.replace('_', ' ').title()}\n"
        f"- **Key Findings:**\n"
        + "\n".join(findings_summary) + "\n"
        f"- **Conditions:** {conditions_text}\n"
    )

    return topic, entry


def build_weekly_wiki_updates(
    cases: list[dict],
) -> dict[str, list[str]]:
    """Process a batch of closed cases and group entries by wiki topic.

    Returns a dict mapping topic slugs to lists of markdown entries.
    Cases that don't match any topic are grouped under "uncategorized".
    """
    updates: dict[str, list[str]] = {}
    for case in cases:
        topic, entry = generate_wiki_entry(case)
        key = topic or "uncategorized"
        updates.setdefault(key, []).append(entry)
    return updates
