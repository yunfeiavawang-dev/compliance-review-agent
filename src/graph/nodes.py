"""LangGraph node implementations for the KYC compliance review workflow."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from src.config import AppConfig
from src.models import get_llm_client, chat_completion
from src.knowledge.retrieval import ComplianceKnowledgeBase
from src.memory.customer_profile_store import CustomerProfileStore
from src.prompts.templates import (
    SYSTEM_PROMPT, INTAKE_PROMPT, SCREENING_PROMPT,
    RISK_ASSESSMENT_PROMPT, STANDARD_REVIEW_PROMPT,
    EDD_PROMPT, DECISION_SUMMARY_PROMPT,
)
from src.graph.state import ReviewState
from src.graph.edges import MAX_INFO_REQUEST_ROUNDS, RESUMABLE_STAGES, has_red_flag, resume_target


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


_VALID_DECISIONS = {
    "approve", "reject", "request_more_info", "escalate",
    "approve_with_conditions", "escalate_to_compliance_committee",
}


def _extract_recommendation(result: dict, default: str = "escalate") -> str:
    """Robustly extract the recommendation from a ReAct final_answer result."""
    for key in ("recommendation", "decision"):
        val = result.get(key, "")
        if val and val in _VALID_DECISIONS:
            return val
    raw = result.get("raw_response", "")
    if raw:
        for decision in ("approve_with_conditions", "request_more_info",
                         "escalate_to_compliance_committee",
                         "approve", "reject", "escalate"):
            if decision in raw.lower():
                return decision
    return default


def _extract_confidence(result: dict, default: float) -> float:
    """Robustly extract confidence from a ReAct final_answer result."""
    val = result.get("confidence")
    if isinstance(val, (int, float)) and 0 <= val <= 1:
        return float(val)
    raw = result.get("raw_response", "")
    if raw:
        match = re.search(r'"confidence"\s*:\s*(0\.\d+|1\.0|0|1)', raw)
        if match:
            return float(match.group(1))
    return default


def _audit_entry(step: str, action: str, details: str = "", sources: str = "") -> dict:
    return {
        "step": step,
        "action": action,
        "details": details,
        "sources_used": sources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _add_audit(state: ReviewState, step: str, action: str, details: str = "", sources: str = "") -> list[dict]:
    """Return the NEW audit entries for this node.

    ``audit_trail`` has an append reducer (see state.py), so LangGraph appends
    the returned list to the existing trail. ``state`` is kept in the signature
    for call-site compatibility but is deliberately not read: a node must never
    copy-and-rewrite the whole trail.
    """
    return [_audit_entry(step, action, details, sources)]


# Evaluation-only keys carried in the test-case JSON files. They are ground-truth
# labels for the eval harness and must never reach a prompt.
_EVAL_ONLY_KEYS = ("expected_outcome",)


def _submission_for_prompt(submission: dict) -> dict:
    """Copy of the submission without evaluation labels, safe to serialize into a prompt."""
    return {k: v for k, v in submission.items() if k not in _EVAL_ONLY_KEYS}


def _case_background(submission: dict) -> str:
    """Declared funding/wealth facts that SoF/SoW assessment depends on."""
    return (
        f"Account request: {json.dumps(submission.get('account_request', {}), indent=2, default=str)}\n"
        f"Source of funds (declared): {json.dumps(submission.get('source_of_funds', {}), indent=2, default=str)}\n"
        f"Source of wealth (declared): {json.dumps(submission.get('source_of_wealth', {}), indent=2, default=str)}\n"
        f"Declarations: {json.dumps(submission.get('declarations', {}), indent=2, default=str)}"
    )


def _real_evidence(docs: Any) -> list:
    """Supporting documents that are real evidence (a bare self-declaration is not)."""
    return [d for d in (docs or []) if d and d != "self_declaration_only"]


REACT_TOOLS_DESCRIPTION = """You have these tools. IMPORTANT: You MUST respond with ONLY a valid JSON object — no prose, no explanation outside the JSON.

Call ONE tool per turn using the exact JSON format:

1. search_policy — Query the compliance knowledge base.
   {"tool": "search_policy", "query": "your search query"}

2. check_document — Inspect a submitted document.
   {"tool": "check_document", "doc_type": "passport|utility_bill|certificate_of_incorporation|..."}

3. assess_risk_factor — Deep-dive into a risk factor.
   {"tool": "assess_risk_factor", "factor": "geography|customer_type|transaction_pattern|..."}

4. search_precedent — Search past case reviews.
   {"tool": "search_precedent", "query": "your search query"}

5. final_answer — Provide your conclusion (use when ready).
   {"tool": "final_answer", "recommendation": "approve|reject|request_more_info|escalate|approve_with_conditions", "rationale": "...", "findings": [...], "confidence": 0.0-1.0, "sources_cited": [...]}

RESPOND WITH JSON ONLY. No markdown, no text before or after the JSON object."""


class NodeRunner:
    """Runs LLM-powered nodes with RAG context."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = get_llm_client(config)
        self.model = config.llm.model
        self.kb = ComplianceKnowledgeBase(config)
        self.profile_store = CustomerProfileStore()

    def _call_llm(self, system: str, user: str, max_tokens: int | None = None) -> dict:
        response = chat_completion(
            self.client, self.model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=self.config.llm.temperature,
            max_tokens=max_tokens or self.config.llm.max_tokens,
        )
        return _parse_json_response(response)

    def _call_llm_raw(self, system: str, messages: list[dict], max_tokens: int | None = None) -> str:
        return chat_completion(
            self.client, self.model,
            [{"role": "system", "content": system}] + messages,
            temperature=self.config.llm.temperature,
            max_tokens=max_tokens or self.config.llm.max_tokens,
        )

    def _execute_react_tool(self, tool_call: dict, state: ReviewState) -> str:
        """Execute a ReAct tool and return the observation string."""
        tool = tool_call.get("tool", "")
        if tool == "search_policy":
            query = tool_call.get("query", "")
            current_step = state.get("current_step", "standard_review")
            results = self.kb.select_context(query, step_name=current_step, n_results=5, max_chars=2000)
            if not results:
                return "No policy documents found for this query."
            parts = []
            for r in results:
                parts.append(
                    f"[{r['source']} — {r.get('section', 'N/A')}] "
                    f"(relevance: {r.get('relevance_score', 0):.2f})\n{r['text']}"
                )
            return "\n---\n".join(parts)

        elif tool == "check_document":
            doc_type = tool_call.get("doc_type", "")
            docs = state.get("submission", {}).get("identification_documents", [])
            matches = [d for d in docs if d.get("type") == doc_type]
            if not matches:
                return f"Document '{doc_type}' not found in submission."
            return json.dumps(matches, indent=2, default=str)

        elif tool == "assess_risk_factor":
            factor = tool_call.get("factor", "")
            risk_scores = state.get("risk_scores", {})
            if factor in risk_scores:
                return json.dumps(risk_scores[factor], indent=2, default=str)
            return f"Risk factor '{factor}' not found. Available: {list(risk_scores.keys())}"

        elif tool == "search_precedent":
            query = tool_call.get("query", "")
            results = self.kb.query(query, n_results=3, where={"document_id": {"$contains": "RETRO"}})
            if not results:
                results = self.kb.query(query, n_results=3)
            if not results:
                return "No precedent cases found."
            parts = []
            budget = 1200
            total = 0
            for r in sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True):
                text = r["text"]
                if total + len(text) > budget and parts:
                    break
                parts.append(f"[{r['source']}] {text}")
                total += len(text)
            return "\n---\n".join(parts)

        return f"Unknown tool: {tool}"

    def _react_loop(
        self, system_prompt: str, initial_user_msg: str, state: ReviewState,
        max_rounds: int = 5, step_name: str = "review",
        max_tokens_per_round: int | None = None,
    ) -> tuple[dict, list[dict]]:
        """Run a ReAct loop: Thought → Action → Observation, up to max_rounds.

        Returns (final_answer_dict, react_trace_list).
        """
        messages: list[dict] = [{"role": "user", "content": initial_user_msg}]
        trace: list[dict] = []

        for i in range(max_rounds):
            raw = self._call_llm_raw(system_prompt, messages, max_tokens=max_tokens_per_round)
            parsed = _parse_json_response(raw)

            if parsed.get("parse_error") and i == 0:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": (
                    "Your response must be a JSON object only — no prose. "
                    "Either call a tool or call final_answer. Example:\n"
                    '{"tool": "final_answer", "recommendation": "approve", '
                    '"rationale": "...", "findings": [...], "confidence": 0.9, '
                    '"sources_cited": [...]}'
                )})
                trace.append({"round": i + 1, "action": "format_retry"})
                continue

            if parsed.get("tool") == "final_answer" or parsed.get("parse_error"):
                trace.append({
                    "round": i + 1, "action": "final_answer",
                    "thought": raw[:200] if parsed.get("parse_error") else "Concluded analysis",
                })
                if parsed.get("parse_error"):
                    parsed = {"raw_response": raw}
                return parsed, trace

            tool_name = parsed.get("tool", "unknown")
            observation = self._execute_react_tool(parsed, state)
            sources_used = parsed.get("query", parsed.get("doc_type", parsed.get("factor", "")))

            trace.append({
                "round": i + 1,
                "action": f"{tool_name}({sources_used})",
                "observation_preview": observation[:150],
            })

            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"Observation from {tool_name}:\n{observation}\n\nContinue your analysis. Use another tool or call final_answer.",
            })

        final_raw = self._call_llm_raw(system_prompt, messages + [
            {"role": "user", "content": "You have used all available rounds. Provide your final_answer now as a concise JSON object."}
        ], max_tokens=max_tokens_per_round)
        final = _parse_json_response(final_raw)
        trace.append({"round": max_rounds + 1, "action": "forced_final_answer"})
        return final, trace

    # --- Node: Intake & Validation (Rule-based + LLM) ---

    @staticmethod
    def _rule_based_doc_check(submission: dict) -> dict:
        """Phase 1: deterministic checks — no LLM needed."""
        customer_type = submission.get("customer", {}).get("type", "individual")
        docs = submission.get("identification_documents", [])
        declarations = submission.get("declarations", {})

        critical_missing: list[str] = []
        non_critical_missing: list[str] = []
        verification_notes: list[str] = []
        doc_issues: list[str] = []
        edge_cases: list[str] = []

        def _has_doc(doc_type: str) -> bool:
            return any(
                d.get("type") == doc_type and (d.get("verified") or d.get("provided"))
                for d in docs
            )

        def _has_category(cat: str) -> bool:
            return any(
                d.get("category") == cat and (d.get("verified") or d.get("provided"))
                for d in docs
            )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for d in docs:
            expiry = d.get("expiry_date", "")
            if expiry and expiry < today:
                doc_issues.append(f"{d.get('type', 'unknown')} expired on {expiry}")

        if customer_type == "individual":
            if not _has_category("A"):
                photo_id_types = {"passport", "national_id", "driver_license"}
                if not any(d.get("type") in photo_id_types and (d.get("verified") or d.get("provided")) for d in docs):
                    critical_missing.append("photo ID (passport, national ID, or driver license)")
                else:
                    edge_cases.append("Photo ID present but not labeled category A — verify classification")
            if not _has_category("B"):
                non_critical_missing.append("proof of address (category B)")
            if not _has_category("C"):
                non_critical_missing.append("tax document (category C)")
            if not declarations.get("declaration_signed"):
                critical_missing.append("signed declaration")
        else:
            for crit_doc in ["certificate_of_incorporation", "board_resolution"]:
                if not _has_doc(crit_doc):
                    critical_missing.append(crit_doc.replace("_", " "))
            bo = submission.get("beneficial_ownership", {})
            if not bo.get("declared_owners"):
                critical_missing.append("beneficial ownership declaration")
            else:
                for owner in bo.get("declared_owners", []):
                    if not owner.get("identification_provided") and owner.get("ownership_percentage", 0) >= 25:
                        edge_cases.append(
                            f"UBO {owner.get('name', 'unknown')} ({owner.get('ownership_percentage')}%) — ID not provided"
                        )
            if not _has_doc("memorandum_of_association"):
                non_critical_missing.append("memorandum of association")
            if not _has_doc("audited_financial_statements"):
                non_critical_missing.append("audited financial statements")
            if not _has_doc("business_license"):
                non_critical_missing.append("business license / local registration")

        for d in docs:
            status = "verified" if d.get("verified") else ("provided" if d.get("provided") else "missing")
            verification_notes.append(f"{d.get('type', 'unknown')}: {status}")

        return {
            "critical_missing": critical_missing,
            "non_critical_missing": non_critical_missing,
            "verification_notes": verification_notes,
            "doc_issues": doc_issues,
            "edge_cases": edge_cases,
        }

    def intake_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        case_id = state.get("case_id", "")
        policy_results = self.kb.get_policy_for_step("intake")

        # Pull long-term customer profile from bank systems
        profile = self.profile_store.get_profile(case_id)
        profile_summary = self.profile_store.format_for_prompt(profile)

        rules = self._rule_based_doc_check(submission)
        critical_missing = rules["critical_missing"]
        non_critical_missing = rules["non_critical_missing"]
        edge_cases = rules["edge_cases"]

        if edge_cases or rules["doc_issues"]:
            policy_context = self.kb.format_sources_for_prompt(policy_results)
            customer_type = submission.get("customer", {}).get("type", "individual")
            prompt = INTAKE_PROMPT.format(
                submission_json=json.dumps(_submission_for_prompt(submission), indent=2, default=str),
                customer_type=customer_type.upper(),
                policy_context=policy_context,
                historical_context=profile_summary,
            )
            llm_result = self._call_llm(SYSTEM_PROMPT, prompt, max_tokens=1024)
            llm_non_critical = llm_result.get("non_critical_missing", non_critical_missing)
            for item in llm_non_critical:
                if item not in non_critical_missing:
                    non_critical_missing.append(item)
            llm_summary = llm_result.get("summary", "LLM reviewed edge cases")
            rules["verification_notes"] = llm_result.get("verification_notes", rules["verification_notes"])
        else:
            llm_summary = None

        if critical_missing:
            intake_status = "blocked"
        elif non_critical_missing:
            intake_status = "conditional"
        else:
            intake_status = "complete"

        all_missing = critical_missing + non_critical_missing
        summary_parts = []
        if intake_status == "complete":
            summary_parts.append("All required documents present and verified")
        elif intake_status == "blocked":
            summary_parts.append(f"BLOCKED — critical documents missing: {', '.join(critical_missing)}")
        else:
            summary_parts.append(f"CONDITIONAL — non-critical missing: {', '.join(non_critical_missing)}")
        if rules["doc_issues"]:
            summary_parts.append(f"Issues: {'; '.join(rules['doc_issues'])}")
        if profile is not None:
            summary_parts.append(
                f"Customer profile loaded: {profile.get('relationship_tenure_years', '?')}yr relationship, "
                f"last KYC={profile.get('compliance_history', {}).get('last_kyc_outcome', '?')}"
            )
        else:
            summary_parts.append("No prior bank relationship — new customer")
        if llm_summary:
            summary_parts.append(f"LLM assessment: {llm_summary}")
        summary = ". ".join(summary_parts)

        return {
            "documents_complete": len(all_missing) == 0,
            "missing_documents": all_missing,
            "document_verification": rules["verification_notes"],
            "intake_status": intake_status,
            "critical_missing": critical_missing,
            "non_critical_missing": non_critical_missing,
            "current_step": "intake",
            "next_step": "identity_screening" if intake_status != "blocked" else "request_info",
            "findings": [summary],
            "sources_cited": [{"step": "intake", "sources": [r["source"] for r in policy_results]}],
            "customer_profile": profile,
            "customer_profile_summary": profile_summary,
            "is_existing_customer": profile is not None,
            "audit_trail": _add_audit(
                state, "intake", "document_completeness_check",
                f"[{intake_status.upper()}] {summary}",
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
            historical_context=state.get("customer_profile_summary", "No customer profile available."),
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt, max_tokens=1024)

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

        # The prompt has one "Account Request" slot; SoF/SoW are part of what the
        # Source-of-Funds risk factor is scored on, so they go in with it.
        account_context = {
            "account_request": account,
            "source_of_funds": submission.get("source_of_funds", {}),
            "source_of_wealth": submission.get("source_of_wealth", {}),
        }

        prompt = RISK_ASSESSMENT_PROMPT.format(
            customer_json=json.dumps(customer, indent=2, default=str),
            account_json=json.dumps(account_context, indent=2, default=str),
            screening_summary=json.dumps(screening_summary, indent=2),
            policy_context=policy_context,
            historical_context=state.get("customer_profile_summary", "No customer profile available."),
        )

        result = self._call_llm(SYSTEM_PROMPT, prompt, max_tokens=1024)

        findings = list(state.get("findings", []))
        findings.append(result.get("summary", "Risk assessment completed"))

        total_score = result.get("total_score", 0)
        if state.get("intake_status") == "conditional":
            total_score += 1
            findings.append("Risk score +1: proceeding with incomplete non-critical documents")

        if total_score >= 12:
            final_rating = "high"
        elif total_score >= 8:
            final_rating = "medium"
        else:
            final_rating = "low"

        override_reason = None
        if has_red_flag(state):
            if final_rating != "high":
                override_reason = (
                    f"Automatic override to HIGH: screening red flag "
                    f"(sanctions={state.get('sanctions_result')}, pep={state.get('pep_result')})"
                )
                findings.append(override_reason)
                final_rating = "high"

        dd_level = "enhanced" if final_rating == "high" else "standard"

        return {
            "risk_scores": result.get("scores", {}),
            "risk_total": total_score,
            "risk_rating": final_rating,
            "risk_override": override_reason or (result.get("override_reason") if result.get("override_applied") else None),
            "due_diligence_level": dd_level,
            "current_step": "risk_assessment",
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "risk_assessment", "sources": [r["source"] for r in policy_results]}
            ],
            "audit_trail": _add_audit(
                state, "risk_assessment", "risk_scoring",
                f"Total score: {total_score}, Rating: {final_rating}, DD: {dd_level}",
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: Standard Review (ReAct loop) ---
    def standard_review_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        profile_ctx = state.get("customer_profile_summary", "No customer profile available.")

        case_summary = (
            f"Customer: {json.dumps(submission.get('customer', {}), indent=2, default=str)}\n"
            f"Documents: {json.dumps(state.get('document_verification', []), indent=2, default=str)}\n"
            f"Screening: {json.dumps(state.get('screening_details', []), indent=2, default=str)}\n"
            f"Risk: total={state.get('risk_total', 0)}, rating={state.get('risk_rating', '')}, "
            f"scores={json.dumps(state.get('risk_scores', {}), indent=2, default=str)}\n"
            f"{_case_background(submission)}\n\n"
            f"## Customer Historical Profile\n{profile_ctx}"
        )

        initial_msg = (
            f"Conduct a standard CDD review for this customer.\n\n"
            f"## Case summary\n{case_summary}\n\n"
            f"## Available tools\n{REACT_TOOLS_DESCRIPTION}\n\n"
            f"## Decision guidance\n"
            f"- Recommend 'approve' when: all required documents verified, screening clear, "
            f"risk rating low/medium, source of funds documented and consistent with profile.\n"
            f"- Recommend 'request_more_info' ONLY when specific critical information is "
            f"genuinely missing that prevents a decision (not for nice-to-haves).\n"
            f"- Recommend 'reject' when: confirmed sanctions match, fraudulent documents, "
            f"or irreconcilable risk factors.\n\n"
            f"Use tools to verify, then call final_answer:\n"
            f'{{"tool": "final_answer", "recommendation": "approve/reject/request_more_info", '
            f'"rationale": "...", "findings": [...], "conditions": [...], '
            f'"confidence": 0.0-1.0, "sources_cited": [...]}}'
        )

        result, trace = self._react_loop(
            SYSTEM_PROMPT, initial_msg, state,
            max_rounds=3, step_name="standard_review",
            max_tokens_per_round=768,
        )

        findings = list(state.get("findings", []))
        findings.extend(result.get("findings", []))

        react_sources = []
        for t in trace:
            action = t.get("action", "")
            if "search_policy" in action or "search_precedent" in action:
                react_sources.append(action)

        audit_trail = [
            _audit_entry(
                "standard_review",
                f"react_round_{t['round']}: {t['action']}",
                t.get("observation_preview", ""),
            )
            for t in trace
        ]

        return {
            "decision": _extract_recommendation(result, default="escalate"),
            "decision_rationale": result.get("rationale", ""),
            "ai_confidence": _extract_confidence(result, default=0.85),
            "recommendations": result.get("conditions", []),
            "current_step": "standard_review",
            "human_review_required": True,
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "standard_review", "sources": result.get("sources_cited", react_sources)}
            ],
            "audit_trail": audit_trail,
        }

    @staticmethod
    def _pep_mitigant_override(state: ReviewState, llm_decision: str) -> str:
        """Override conservative LLM decisions for retired PEPs with strong
        mitigants (clean screening + documented wealth)."""
        if llm_decision in ("approve", "approve_with_conditions", "reject"):
            return llm_decision
        decl = state.get("submission", {}).get("declarations", {})
        if not decl.get("pep_status"):
            return llm_decision
        if state.get("sanctions_result") not in ("clear", None):
            return llm_decision
        if state.get("adverse_media_result") not in ("clear", None):
            return llm_decision
        sof = state.get("submission", {}).get("source_of_funds", {})
        sow = state.get("submission", {}).get("source_of_wealth", {})
        sof_docs = _real_evidence(sof.get("supporting_documents"))
        sow_docs = _real_evidence(sow.get("supporting_documents"))
        if not sof_docs and not sow_docs:
            return llm_decision
        return "approve_with_conditions"

    # --- Node: Enhanced Due Diligence (ReAct loop) ---
    def edd_node(self, state: ReviewState) -> dict:
        submission = state["submission"]
        profile_ctx = state.get("customer_profile_summary", "No customer profile available.")

        case_summary = (
            f"Customer: {json.dumps(submission.get('customer', {}), indent=2, default=str)}\n"
            f"Documents: {json.dumps(state.get('document_verification', []), indent=2, default=str)}\n"
            f"Screening: {json.dumps(state.get('screening_details', []), indent=2, default=str)}\n"
            f"Risk: total={state.get('risk_total', 0)}, rating={state.get('risk_rating', '')}, "
            f"override={state.get('risk_override')}\n"
            f"Beneficial ownership: {json.dumps(submission.get('beneficial_ownership', {}), indent=2, default=str)}\n"
            f"{_case_background(submission)}\n\n"
            f"## Customer Historical Profile\n{profile_ctx}"
        )
        outstanding = state.get("edd_missing_docs") or []
        if outstanding:
            case_summary += (
                "\nMandatory EDD documents STILL OUTSTANDING (the case proceeds to EDD because "
                "of a screening red flag, so treat these as conditions, include them in "
                f"additional_info_needed, and do not recommend approval without them): {json.dumps(outstanding)}"
            )

        initial_msg = (
            f"Conduct Enhanced Due Diligence (EDD) for this HIGH-RISK customer.\n\n"
            f"## Case summary\n{case_summary}\n\n"
            f"## Available tools\n{REACT_TOOLS_DESCRIPTION}\n\n"
            f"EDD requires deeper investigation. You MUST:\n"
            f"1. Search for EDD policy requirements\n"
            f"2. Assess source of wealth and source of funds\n"
            f"3. Check beneficial ownership structure\n"
            f"4. Look for similar precedent cases\n\n"
            f"## Decision guidance\n"
            f"- 'approve_with_conditions': risk is high but mitigants are strong. Specify conditions "
            f"(enhanced monitoring, periodic review, transaction thresholds). Examples:\n"
            f"  * PEP who has been retired/out of office for 3+ years, with clean sanctions/adverse media "
            f"screening, documented source of wealth (audited financials, not just self-declaration), "
            f"and transparent ownership → approve with enhanced monitoring + annual PEP review.\n"
            f"  * High-risk geography but legitimate documented business, clean screening, cooperating "
            f"with all information requests → approve with transaction monitoring conditions.\n"
            f"- 'escalate': ONLY for unresolvable concerns that require Compliance Committee judgment:\n"
            f"  * Potential or confirmed sanctions match that cannot be dismissed\n"
            f"  * Unverified source of wealth combined with other red flags (adverse media, "
            f"suspicious transaction patterns)\n"
            f"  * Multiple simultaneous high-risk indicators with no mitigants\n"
            f"- 'request_more_info': ONLY when specific critical documents are genuinely missing "
            f"that would change the decision. Do not request info already in the case summary.\n"
            f"- 'reject': clear grounds for rejection (confirmed fraud, confirmed sanctions).\n\n"
            f"## IMPORTANT RULE for retired PEPs\n"
            f"If the customer is a PEP who left office 3+ years ago AND sanctions screening is clear "
            f"AND adverse media is clear AND source of wealth is supported by audited financials or "
            f"verifiable business records (not just self-declaration), then the correct decision is "
            f"'approve_with_conditions' with enhanced monitoring. Do NOT escalate — the cooling-off "
            f"period, clean screening, and documented wealth are sufficient mitigants for conditional "
            f"approval. Escalation is only appropriate when screening raises active concerns.\n\n"
            f"You MUST make a decision based on available evidence. Use tools, then call final_answer:\n"
            f'{{"tool": "final_answer", "recommendation": "approve_with_conditions/reject/request_more_info/escalate", '
            f'"rationale": "...", "findings": [...], '
            f'"source_of_wealth_assessment": "...", "source_of_funds_assessment": "...", '
            f'"additional_info_needed": [...], "risk_mitigants": [...], "risk_amplifiers": [...], '
            f'"proposed_monitoring": "...", "confidence": 0.0-1.0, "sources_cited": [...]}}'
        )

        result, trace = self._react_loop(
            SYSTEM_PROMPT, initial_msg, state,
            max_rounds=3, step_name="edd",
            max_tokens_per_round=768,
        )

        decision = _extract_recommendation(result, default="escalate")

        if decision in ("escalate", "request_more_info"):
            decision = self._pep_mitigant_override(state, decision)

        findings = list(state.get("findings", []))
        findings.extend(result.get("findings", []))

        audit_trail = [
            _audit_entry(
                "enhanced_due_diligence",
                f"react_round_{t['round']}: {t['action']}",
                t.get("observation_preview", ""),
            )
            for t in trace
        ]

        react_sources = [t.get("action", "") for t in trace if "search_" in t.get("action", "")]

        return {
            "edd_findings": {
                "source_of_wealth": result.get("source_of_wealth_assessment", ""),
                "source_of_funds": result.get("source_of_funds_assessment", ""),
                "additional_info_needed": result.get("additional_info_needed", []),
                "risk_mitigants": result.get("risk_mitigants", []),
                "risk_amplifiers": result.get("risk_amplifiers", []),
            },
            "decision": decision,
            "decision_rationale": result.get("rationale", ""),
            "ai_confidence": _extract_confidence(result, default=0.7),
            "recommendations": result.get("proposed_monitoring", "").split(". ") if isinstance(result.get("proposed_monitoring"), str) else result.get("proposed_monitoring", []),
            "current_step": "enhanced_due_diligence",
            "human_review_required": True,
            "findings": findings,
            "sources_cited": state.get("sources_cited", []) + [
                {"step": "edd", "sources": result.get("sources_cited", react_sources)}
            ],
            "audit_trail": audit_trail,
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

    def _summarize_for_memory(self, state: ReviewState) -> dict:
        """Build a compact summary of the review for long-term memory."""
        findings = state.get("findings", [])
        key_findings = []
        for f in findings[:5]:
            if isinstance(f, dict):
                key_findings.append(f.get("summary", str(f)))
            else:
                key_findings.append(str(f))
        return {
            "case_id": state.get("case_id"),
            "decision": state.get("decision"),
            "risk_rating": state.get("risk_rating"),
            "risk_score": state.get("risk_total"),
            "due_diligence_level": state.get("due_diligence_level"),
            "key_findings": key_findings,
            "conditions": state.get("recommendations", []),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

    # --- Node: Final Decision ---
    def decision_node(self, state: ReviewState) -> dict:
        final_decision = state.get("human_decision") or state.get("decision") or "escalate"
        ai_decision = state.get("decision")
        ai_human_agreement = (final_decision == ai_decision) if ai_decision else None

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

        result = self._call_llm(SYSTEM_PROMPT, prompt, max_tokens=1024)

        try:
            mem_summary = self._summarize_for_memory(state)
            self.profile_store.write_case_summary(
                state.get("case_id", ""), state.get("customer_id", ""), mem_summary,
            )
        except Exception:
            pass

        return {
            "decision": final_decision,
            "decision_rationale": result.get("rationale", state.get("decision_rationale", "")),
            "ai_human_agreement": ai_human_agreement,
            "review_status": "completed",
            "current_step": "decision",
            "audit_trail": _add_audit(
                state, "decision", f"final_decision_{final_decision}",
                result.get("rationale", ""),
                ", ".join(r["document_id"] for r in policy_results),
            ),
        }

    # --- Node: EDD document gate (deterministic, no LLM) ---
    @staticmethod
    def _check_edd_documents(submission: dict) -> list[str]:
        """Mandatory EDD evidence per CDD guidelines §7.1: source-of-wealth
        documentation and source-of-funds evidence. A bare self-declaration
        does not count as evidence."""
        missing: list[str] = []
        sow = submission.get("source_of_wealth") or {}
        if not _real_evidence(sow.get("supporting_documents")):
            missing.append(
                "source of wealth supporting documentation "
                "(independent evidence — a self-declaration alone is insufficient)"
            )
        sof = submission.get("source_of_funds") or {}
        if not _real_evidence(sof.get("supporting_documents")):
            missing.append("source of funds supporting documentation (initial deposit / expected transactions)")
        return missing

    def edd_document_check_node(self, state: ReviewState) -> dict:
        missing = self._check_edd_documents(state["submission"])
        red_flag = has_red_flag(state)
        bypassed = bool(missing) and red_flag

        if not missing:
            summary = "All mandatory EDD documents present"
        elif red_flag:
            summary = (
                f"EDD documents outstanding: {'; '.join(missing)}. NOT blocking — screening red flag "
                f"(sanctions={state.get('sanctions_result')}, pep={state.get('pep_result')}) must reach EDD/escalation; "
                f"gaps carried into EDD as conditions"
            )
        else:
            summary = f"EDD blocked pending documents: {'; '.join(missing)}"

        return {
            "edd_missing_docs": missing,
            "edd_docs_bypassed": bypassed,
            "current_step": "edd_document_check",
            "audit_trail": _add_audit(state, "edd_document_check", "edd_document_gate", summary),
        }

    # --- Node: Request More Info ---
    @staticmethod
    def _resolve_info_stage(state: ReviewState) -> str:
        """Which node is asking for information (= where the graph resumes)."""
        if state.get("human_decision") == "request_more_info":
            return "human_review"
        step = state.get("current_step", "")
        return step if step in RESUMABLE_STAGES else "intake"

    @staticmethod
    def _collect_info_requests(state: ReviewState, stage: str) -> list[str]:
        if stage == "human_review":
            requests = [state.get("human_notes") or "Reviewer requested additional information"]
        elif stage == "edd_document_check":
            requests = list(state.get("edd_missing_docs", []))
        elif stage == "enhanced_due_diligence":
            requests = list((state.get("edd_findings") or {}).get("additional_info_needed", []))
            requests += list(state.get("edd_missing_docs", []))
        elif stage == "standard_review":
            requests = [state.get("decision_rationale") or "Additional information requested by standard review"]
        else:  # intake, identity_screening
            requests = list(state.get("missing_documents", []))

        seen: set[str] = set()
        unique = []
        for r in requests:
            text = str(r).strip()
            if text and text not in seen:
                seen.add(text)
                unique.append(text)
        return unique or ["Additional information required — see review findings"]

    def request_info_node(self, state: ReviewState) -> dict:
        stage = self._resolve_info_stage(state)
        info_requests = self._collect_info_requests(state, stage)
        round_no = state.get("info_request_round", 0) + 1
        exceeded = round_no > MAX_INFO_REQUEST_ROUNDS

        if exceeded:
            details = (
                f"Round {round_no} would exceed the limit of {MAX_INFO_REQUEST_ROUNDS}; "
                f"information still outstanding from '{stage}': {'; '.join(info_requests)}. "
                f"Handing to human review with an escalate recommendation."
            )
            update = {
                "decision": "escalate",
                "decision_rationale": details,
                "human_review_required": True,
            }
        else:
            details = f"Round {round_no}, requested by '{stage}': {'; '.join(info_requests)}"
            update = {"decision": "request_more_info"}

        return {
            **update,
            "info_requests": info_requests,
            "info_request_stage": stage,
            "info_request_round": round_no,
            "info_round_exceeded": exceeded,
            "current_step": "request_info",
            "audit_trail": _add_audit(state, "request_info", "information_requested", details),
        }

    def await_info_node(self, state: ReviewState) -> dict:
        """Passthrough that runs only after the graph was resumed with the
        supplemental information (the graph pauses before this node)."""
        target = resume_target(state)
        update: dict = {}
        if "edd_missing_docs" in state:
            # Refresh the outstanding-EDD-docs list against the supplemented
            # submission so a resumed EDD run is not told that documents that
            # have now arrived are still missing.
            update["edd_missing_docs"] = self._check_edd_documents(state["submission"])
        return {
            **update,
            # The request that triggered the loop has been answered.
            "human_decision": None,
            "human_notes": None,
            "current_step": "await_info",
            "audit_trail": _add_audit(
                state, "await_info", "information_received",
                f"Supplement received for '{state.get('info_request_stage', '')}'; resuming at '{target}'",
            ),
        }
