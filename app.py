"""Streamlit demo app for the KYC Compliance Review Agent."""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, ".")

from src.config import load_config
from src.graph.workflow import create_app
from src.graph.state import ReviewState
from src.knowledge.retrieval import ComplianceKnowledgeBase
from src.database.schema import init_database
from src.database import crud
from src.memory.short_term import SessionMemory
from src.memory.long_term import LongTermMemory


# --- Page Config ---
st.set_page_config(
    page_title="KYC Compliance Review Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("KYC Compliance Review Agent")
st.caption("AI-assisted compliance review for customer onboarding at Pacific Rim Financial Group")


# --- Initialize ---
@st.cache_resource
def get_config():
    return load_config()

@st.cache_resource
def get_app():
    config = get_config()
    return create_app(config)

@st.cache_resource
def get_knowledge_base():
    config = get_config()
    return ComplianceKnowledgeBase(config)

@st.cache_resource
def get_long_term_memory():
    return LongTermMemory()


def load_case_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def get_case_files() -> dict:
    cases = {}
    data_dir = Path("data/customers")
    for f in sorted(data_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        label = f"{data['case_id']} — {data['customer'].get('full_name', data['customer'].get('company_name', 'Unknown'))}"
        cases[label] = str(f)
    return cases


# --- Sidebar ---
with st.sidebar:
    st.header("Case Selection")

    case_files = get_case_files()
    selected_case = st.selectbox("Load a sample case:", list(case_files.keys()))

    if st.button("Load Case", type="primary", use_container_width=True):
        case_data = load_case_file(case_files[selected_case])
        st.session_state["case_data"] = case_data
        st.session_state["review_state"] = None
        st.session_state["step_results"] = []
        st.session_state["current_step"] = "ready"
        st.session_state["session_memory"] = SessionMemory(case_data["case_id"])

    st.divider()
    st.header("System Info")
    config = get_config()
    st.text(f"LLM: {config.llm.provider} / {config.llm.model}")
    st.text(f"Embedding: {config.embedding.provider}")
    kb = get_knowledge_base()
    st.text(f"Knowledge base: {kb.count()} chunks")
    mem = get_long_term_memory()
    mem_stats = mem.get_stats()
    st.text(f"Agent memory: {mem_stats['total_memories']} entries")

    st.divider()
    st.header("RAG Inspector")
    rag_query = st.text_input("Query the knowledge base:")
    if rag_query:
        results = kb.query(rag_query, n_results=3)
        for r in results:
            with st.expander(f"[{r['relevance_score']:.2f}] {r['source']} — {r['section']}"):
                st.text(r["text"][:500])
                st.caption(f"Doc: {r['document_id']} v{r['version']}")


# --- Main Content ---
if "case_data" not in st.session_state:
    st.info("Select a sample case from the sidebar and click 'Load Case' to begin.")
    st.stop()

case_data = st.session_state["case_data"]

# Case overview
col1, col2, col3 = st.columns(3)
with col1:
    customer = case_data["customer"]
    name = customer.get("full_name", customer.get("company_name", "Unknown"))
    st.metric("Customer", name)
with col2:
    st.metric("Case ID", case_data["case_id"])
with col3:
    st.metric("Type", customer.get("type", "unknown").title())

# Tabs
tab_review, tab_details, tab_audit = st.tabs(["Review Workflow", "Case Details", "Audit Trail"])

with tab_details:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Customer Information")
        st.json(case_data.get("customer", {}))
        st.subheader("Account Request")
        st.json(case_data.get("account_request", {}))
    with col_b:
        st.subheader("Documents")
        for doc in case_data.get("identification_documents", []):
            icon = "✅" if doc.get("verified") or doc.get("provided") else "❌"
            st.markdown(f"{icon} **{doc.get('type', 'unknown')}** — {doc.get('note', doc.get('document_number', 'N/A'))}")
        if case_data.get("screening_flags"):
            st.subheader("Pre-existing Screening Flags")
            st.json(case_data["screening_flags"])

with tab_review:
    # Run review button
    if st.session_state.get("current_step") == "ready":
        st.info("Case loaded. Click 'Start Review' to begin the automated compliance review workflow.")
        if st.button("Start Review", type="primary", use_container_width=True):
            st.session_state["current_step"] = "running"
            st.rerun()

    elif st.session_state.get("current_step") == "running":
        with st.spinner("Running compliance review workflow..."):
            try:
                config = get_config()
                app = get_app()

                initial_state = ReviewState(
                    case_id=case_data["case_id"],
                    submission=case_data,
                    findings=[],
                    recommendations=[],
                    sources_cited=[],
                    audit_trail=[],
                    info_requests=[],
                    current_step="intake",
                )

                thread_config = {"configurable": {"thread_id": case_data["case_id"]}}

                # Run until human review interrupt
                step_results = []
                for event in app.stream(initial_state, thread_config):
                    for node_name, node_output in event.items():
                        step_results.append({
                            "node": node_name,
                            "output": node_output,
                        })

                st.session_state["step_results"] = step_results
                st.session_state["review_state"] = app.get_state(thread_config)
                st.session_state["thread_config"] = thread_config
                st.session_state["current_step"] = "human_review"
            except Exception as e:
                st.error(f"Error during review: {str(e)}")
                st.session_state["current_step"] = "error"
                st.session_state["error_detail"] = str(e)
            st.rerun()

    elif st.session_state.get("current_step") == "human_review":
        # Show step results
        st.subheader("Workflow Progress")
        for i, step in enumerate(st.session_state.get("step_results", [])):
            node = step["node"]
            output = step["output"]
            with st.expander(f"Step {i+1}: {node.replace('_', ' ').title()}", expanded=(i == len(st.session_state["step_results"]) - 1)):
                if "findings" in output:
                    for finding in output.get("findings", [])[-3:]:
                        st.markdown(f"- {finding}")
                if "risk_rating" in output:
                    rating = output["risk_rating"]
                    color = {"low": "green", "medium": "orange", "high": "red"}.get(rating, "gray")
                    st.markdown(f"**Risk Rating:** :{color}[{rating.upper()}] (Score: {output.get('risk_total', 'N/A')})")
                if "decision" in output:
                    st.markdown(f"**Agent Recommendation:** `{output['decision']}`")
                if "decision_rationale" in output:
                    st.markdown(f"**Rationale:** {output['decision_rationale'][:500]}")
                if output.get("missing_documents"):
                    st.warning(f"Missing documents: {', '.join(output['missing_documents'])}")

        # Human review section
        st.divider()
        st.subheader("Human Review Decision")

        state_snapshot = st.session_state["review_state"]
        current_values = state_snapshot.values if state_snapshot else {}

        agent_decision = current_values.get("decision", "N/A")
        st.info(f"Agent recommendation: **{agent_decision}**")

        col_dec, col_notes = st.columns([1, 2])
        with col_dec:
            human_decision = st.selectbox(
                "Your decision:",
                ["approve", "reject", "request_more_info", "escalate"],
                index=["approve", "reject", "request_more_info", "escalate"].index(agent_decision) if agent_decision in ["approve", "reject", "request_more_info", "escalate"] else 0,
            )
        with col_notes:
            human_notes = st.text_area("Review notes (optional):", height=100)

        if st.button("Submit Decision", type="primary"):
            try:
                app = get_app()
                thread_config = st.session_state["thread_config"]

                app.update_state(
                    thread_config,
                    {"human_decision": human_decision, "human_notes": human_notes},
                    as_node="human_review",
                )

                # Resume after human review
                final_results = list(st.session_state.get("step_results", []))
                for event in app.stream(None, thread_config):
                    for node_name, node_output in event.items():
                        final_results.append({
                            "node": node_name,
                            "output": node_output,
                        })

                st.session_state["step_results"] = final_results
                final_state = app.get_state(thread_config)
                st.session_state["review_state"] = final_state
                st.session_state["current_step"] = "complete"
            except Exception as e:
                st.error(f"Error finalizing review: {str(e)}")
            st.rerun()

    elif st.session_state.get("current_step") == "complete":
        st.success("Review Complete!")

        state_snapshot = st.session_state["review_state"]
        final_values = state_snapshot.values if state_snapshot else {}

        # Decision summary
        col1, col2, col3 = st.columns(3)
        with col1:
            decision = final_values.get("decision", "N/A")
            color_map = {"approve": "green", "reject": "red", "request_more_info": "orange", "escalate": "blue"}
            st.metric("Final Decision", decision.upper())
        with col2:
            st.metric("Risk Rating", final_values.get("risk_rating", "N/A").upper())
        with col3:
            st.metric("Risk Score", final_values.get("risk_total", "N/A"))

        st.subheader("Decision Rationale")
        st.write(final_values.get("decision_rationale", "No rationale provided"))

        st.subheader("Key Findings")
        for finding in final_values.get("findings", []):
            st.markdown(f"- {finding}")

        if final_values.get("info_requests"):
            st.subheader("Information Requested")
            for req in final_values["info_requests"]:
                st.markdown(f"- {req}")

        # Show all step results
        st.divider()
        st.subheader("Workflow Steps")
        for i, step in enumerate(st.session_state.get("step_results", [])):
            with st.expander(f"Step {i+1}: {step['node'].replace('_', ' ').title()}"):
                st.json(step["output"])

        if st.button("Start New Review"):
            for key in ["case_data", "review_state", "step_results", "current_step", "session_memory"]:
                st.session_state.pop(key, None)
            st.rerun()

    elif st.session_state.get("current_step") == "error":
        st.error(f"Review failed: {st.session_state.get('error_detail', 'Unknown error')}")
        st.warning("Check your LLM configuration. Try switching LLM_PROVIDER to 'openai' in .env if Ark is unreachable.")
        if st.button("Retry"):
            st.session_state["current_step"] = "ready"
            st.rerun()

with tab_audit:
    if st.session_state.get("review_state"):
        final_values = st.session_state["review_state"].values if st.session_state["review_state"] else {}
        audit_trail = final_values.get("audit_trail", [])
        if audit_trail:
            st.subheader("Audit Trail")
            for entry in audit_trail:
                ts = entry.get("timestamp", "")[:19]
                st.markdown(f"**[{ts}]** `{entry.get('step', '')}` → {entry.get('action', '')}")
                if entry.get("details"):
                    st.caption(entry["details"][:300])
                if entry.get("sources_used"):
                    st.caption(f"Sources: {entry['sources_used']}")
                st.divider()
        else:
            st.info("No audit entries yet. Run a review to see the audit trail.")

        # Sources cited
        sources = final_values.get("sources_cited", [])
        if sources:
            st.subheader("Policy Sources Referenced")
            for s in sources:
                st.markdown(f"- **{s.get('step', '')}**: {', '.join(s.get('sources', []))}")
    else:
        st.info("Run a review to see the audit trail.")
