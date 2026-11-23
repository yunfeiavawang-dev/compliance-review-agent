"""LangGraph node implementations for the KYC compliance review workflow."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from src.config import AppConfig
from src.models import get_llm_client, chat_completion
from src.knowledge.retrieval import ComplianceKnowledgeBase
from src.prompts.templates import (
    SYSTEM_PROMPT, INTAKE_PROMPT, SCREENING_PROMPT,
    RISK_ASSESSMENT_PROMPT, STANDARD_REVIEW_PROMPT,
    EDD_PROMPT, DECISION_SUMMARY_PROMPT,
)
from src.graph.state import ReviewState


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text, "parse_error": True}


def _add_audit(state: ReviewState, step: str, action: str, details: str = "", sources: str = "") -> list[dict]:
    trail = list(state.get("audit_trail", []))
    trail.append({
        "step": step,
        "action": action,
        "details": details,
        "sources_used": sources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return trail


class NodeRunner:
    """Runs LLM-powered nodes with RAG context."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = get_llm_client(config)
        self.model = config.llm.model
        self.kb = ComplianceKnowledgeBase(config)

    def _call_llm(self, system: str, user: str) -> dict:
        response = chat_completion(
            self.client, self.model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )
        return _parse_json_response(response)

    # --- Node: Intake & Validation ---
    def intake_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        policy_results = self.kb.get_policy_for_step("intake")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        customer_type = submission.get("customer", {}).get("type", "individual")
        prompt = INTAKE_PROMPT.format(
            submission_json=json.dumps(submission, indent=2, default=str),
            customer_type=customer_type.upper(),
            policy_context=policy_context,
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        return {
            "documents_complete": result.get("documents_complete", False),
            "missing_documents": result.get("missing_documents", []),
            "document_verification": result.get("verification_notes", []),
            "current_step": "intake",
            "next_step": "identity_screening" if result.get("can_proceed", False) else "request_info",
            "findings": [result.get("summary", "Intake check completed")],
            "sources_cited": [{"step": "intake", "sources": [r["source"] for r in policy_results]}],
            "audit_trail": _add_audit(
                state, "intake", "document_completeness_check",
                result.get("summary", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Identity Screening ---
    def screening_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        customer = submission.get("customer", {})

        screening_data = submission.get("screening_flags", {})

        policy_results = self.kb.get_policy_for_step("identity_screening")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        prompt = SCREENING_PROMPT.format(
            customer_json=json.dumps(customer, indent=2, default=str),
            screening_data=json.dumps(screening_data, indent=2, default=str) if screening_data else "No pre-existing screening data. Conduct fresh screening based on customer information.",
            policy_context=policy_context,
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        findings = list(state.get("findings", []))
        findings.append(result.get("summary", "Screening completed"))

        return {
            "sanctions_result": result.get("sanctions_result", "clear"),
            "pep_result": result.get("pep_result", "clear"),
            "adverse_media_result": result.get("adverse_media_result", "clear"),
            "screening_details": result.get("screening_details", []),
            "current_step": "identity_screening",
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "screening", "sources": [r["source"] for r in policy_results]}
            ],
            "audit_trail": _add_audit(
                state, "identity_screening", "sanctions_pep_adverse_media_screening",
                result.get("summary", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Risk Assessment ---
    def risk_assessment_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        customer = submission.get("customer", {})
        account = submission.get("account_request", {})

        screening_summary = {
            "sanctions": state.get("sanctions_result", "clear"),
            "pep": state.get("pep_result", "clear"),
            "adverse_media": state.get("adverse_media_result", "clear"),
        }

        policy_results = self.kb.get_policy_for_step("risk_assessment")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        prompt = RISK_ASSESSMENT_PROMPT.format(
            customer_json=json.dumps(customer, indent=2, default=str),
            account_json=json.dumps(account, indent=2, default=str),
            screening_summary=json.dumps(screening_summary, indent=2),
            policy_context=policy_context,
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        findings = list(state.get("findings", []))
        findings.append(result.get("summary", "Risk assessment completed"))

        return {
            "risk_scores": result.get("scores", {}),
            "risk_total": result.get("total_score", 0),
            "risk_rating": result.get("final_rating", "medium"),
            "risk_override": result.get("override_reason") if result.get("override_applied") else None,
            "due_diligence_level": result.get("due_diligence_level", "standard"),
            "current_step": "risk_assessment",
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "risk_assessment", "sources": [r["source"] for r in policy_results]}
            ],
            "audit_trail": _add_audit(
                state, "risk_assessment", "risk_scoring",
                f"Total score: {result.get('total_score', 'N/A')}, Rating: {result.get('final_rating', 'N/A')}",
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Standard Review ---
    def standard_review_node(self, state: ReviewState) -> dict:
        submission = state["submission"]

        policy_results = self.kb.get_policy_for_step("standard_review")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        prompt = STANDARD_REVIEW_PROMPT.format(
            customer_json=json.dumps(submission.get("customer", {}), indent=2, default=str),
            document_summary=json.dumps(state.get("document_verification", []), indent=2, default=str),
            screening_summary=json.dumps(state.get("screening_details", []), indent=2, default=str),
            risk_summary=json.dumps({
                "scores": state.get("risk_scores", {}),
                "total": state.get("risk_total", 0),
                "rating": state.get("risk_rating", ""),
            }, indent=2),
            policy_context=policy_context,
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        findings = list(state.get("findings", []))
        findings.extend(result.get("findings", []))

        return {
            "decision": result.get("recommendation", "approve"),
            "decision_rationale": result.get("rationale", ""),
            "recommendations": result.get("conditions", []),
            "current_step": "standard_review",
            "human_review_required": True,
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "standard_review", "sources": [r["source"] for r in policy_results]}
            ],
            "audit_trail": _add_audit(
                state, "standard_review", "standard_cdd_review",
                result.get("rationale", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Enhanced Due Diligence ---
    def edd_node(self, state: ReviewState) -> dict:
        submission = state["submission"]

        policy_results = self.kb.get_policy_for_step("enhanced_due_diligence")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        prompt = EDD_PROMPT.format(
            customer_json=json.dumps(submission.get("customer", {}), indent=2, default=str),
            document_summary=json.dumps(state.get("document_verification", []), indent=2, default=str),
            screening_summary=json.dumps(state.get("screening_details", []), indent=2, default=str),
            risk_summary=json.dumps({
                "scores": state.get("risk_scores", {}),
                "total": state.get("risk_total", 0),
                "rating": state.get("risk_rating", ""),
                "override": state.get("risk_override"),
            }, indent=2),
            policy_context=policy_context,
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        findings = list(state.get("findings", []))
        findings.extend(result.get("findings", []))

        return {
            "edd_findings": {
                "source_of_wealth": result.get("source_of_wealth_assessment", ""),
                "source_of_funds": result.get("source_of_funds_assessment", ""),
                "additional_info_needed": result.get("additional_info_needed", []),
                "risk_mitigants": result.get("risk_mitigants", []),
                "risk_amplifiers": result.get("risk_amplifiers", []),
            },
            "decision": result.get("recommendation", "escalate"),
            "decision_rationale": result.get("rationale", ""),
            "recommendations": result.get("proposed_monitoring", "").split(". ") if result.get("proposed_monitoring") else [],
            "current_step": "enhanced_due_diligence",
            "human_review_required": True,
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "edd", "sources": [r["source"] for r in policy_results]}
            ],
            "audit_trail": _add_audit(
                state, "enhanced_due_diligence", "edd_review",
                result.get("rationale", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Human Review (passthrough — waits for human input) ---
    def human_review_node(self, state: ReviewState) -> dict:
        return {
            "current_step": "human_review",
            "audit_trail": _add_audit(
                state, "human_review", "awaiting_human_decision",
                f"Agent recommendation: {state.get('decision', 'N/A')}",
            ),
        }

    # --- Node: Final Decision ---
    def decision_node(self, state: ReviewState) -> dict:
        final_decision = state.get("human_decision", state.get("decision", "escalate"))

        review_context = {
            "case_id": state.get("case_id"),
            "customer": state.get("submission", {}).get("customer", {}),
            "risk_rating": state.get("risk_rating"),
            "risk_score": state.get("risk_total"),
            "due_diligence_level": state.get("due_diligence_level"),
            "agent_recommendation": state.get("decision"),
        }

        human_input = {
            "decision": state.get("human_decision", "No human input"),
            "notes": state.get("human_notes", ""),
        }

        policy_results = self.kb.get_policy_for_step("decision")
        policy_context = self.kb.format_sources_for_prompt(policy_results)

        prompt = DECISION_SUMMARY_PROMPT.format(
            review_context=json.dumps(review_context, indent=2, default=str),
            findings_summary=json.dumps(state.get("findings", []), indent=2, default=str),
            human_input=json.dumps(human_input, indent=2),
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt)

        return {
            "decision": final_decision,
            "decision_rationale": result.get("rationale", state.get("decision_rationale", "")),
            "current_step": "decision",
            "audit_trail": _add_audit(
                state, "decision", f"final_decision_{final_decision}",
                result.get("rationale", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Request More Info ---
    def request_info_node(self, state: ReviewState) -> dict:
        info_requests = state.get("missing_documents", [])
        if state.get("edd_findings"):
            info_requests.extend(state["edd_findings"].get("additional_info_needed", []))

        return {
            "decision": "request_more_info",
            "info_requests": info_requests,
            "current_step": "request_info",
            "audit_trail": _add_audit(
                state, "request_info", "information_requested",
                f"Requested: {', '.join(info_requests)}",
            ),
        }
