"""Streamlit demo app for the KYC Compliance Review Agent."""

import json
import sys
from datetime import datetime, timezone
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
from src.graph.resume import pause_point, supply_information
from src.memory.long_term import LongTermMemory


# --- Page Config ---
st.set_page_config(
    page_title="KYC Compliance Review Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .risk-badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-weight: 600; font-size: 13px; text-transform: uppercase;
    }
    .risk-low { background: #d4edda; color: #155724; }
    .risk-medium { background: #fff3cd; color: #856404; }
    .risk-high { background: #f8d7da; color: #721c24; }
    .status-badge {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 12px; font-weight: 500;
    }
    .status-pending { background: #e2e3e5; color: #383d41; }
    .status-in-review { background: #cce5ff; color: #004085; }
    .status-completed { background: #d4edda; color: #155724; }
    .timeline-item {
        position: relative; padding-left: 28px; padding-bottom: 20px;
        border-left: 2px solid #dee2e6; margin-left: 8px;
    }
    .timeline-item:last-child { border-left: 2px solid transparent; }
    .timeline-dot {
        position: absolute; left: -7px; top: 4px; width: 12px; height: 12px;
        border-radius: 50%; border: 2px solid #fff;
    }
    .timeline-dot-ai { background: #007bff; }
    .timeline-dot-human { background: #28a745; }
    .timeline-dot-system { background: #6c757d; }
    .timeline-dot-rag { background: #17a2b8; }
    .timeline-ts { font-size: 11px; color: #999; }
    .timeline-label { font-weight: 600; font-size: 14px; }
    .timeline-detail { font-size: 13px; color: #555; margin-top: 2px; }
    .source-ref {
        display: inline-block; background: #e9ecef; padding: 1px 6px;
        border-radius: 4px; font-size: 11px; color: #495057; margin-right: 4px;
        cursor: help; position: relative;
    }
    .source-ref:hover { background: #dee2e6; }
    .source-ref .tip {
        visibility: hidden; opacity: 0; position: absolute; bottom: 125%;
        left: 50%; transform: translateX(-50%); width: 320px;
        background: #1a1a2e; color: #e0e0e0; padding: 10px 12px;
        border-radius: 6px; font-size: 12px; line-height: 1.5;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); z-index: 999;
        pointer-events: none; transition: opacity 0.15s;
    }
    .source-ref .tip::after {
        content: ""; position: absolute; top: 100%; left: 50%;
        margin-left: -5px; border-width: 5px; border-style: solid;
        border-color: #1a1a2e transparent transparent transparent;
    }
    .source-ref:hover .tip { visibility: visible; opacity: 1; }
    .tip-title { font-weight: 600; color: #90caf9; margin-bottom: 4px; }
    .tip-chunk { color: #bbb; font-size: 11px; }
    .decision-panel {
        background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
        padding: 16px; position: sticky; top: 20px;
    }
    .confidence-bar {
        height: 8px; border-radius: 4px; background: #e9ecef; overflow: hidden;
    }
    .confidence-fill {
        height: 100%; border-radius: 4px;
    }
    .agreement-match { color: #28a745; font-weight: 600; }
    .agreement-mismatch { color: #dc3545; font-weight: 600; }
    .info-card {
        background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)


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


def get_all_cases() -> list[dict]:
    cases = []
    data_dir = Path("data/customers")
    for f in sorted(data_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        data["_file_path"] = str(f)
        cases.append(data)
    return cases


# --- Sidebar ---
with st.sidebar:
    st.header("System Info")
    config = get_config()
    st.text(f"LLM: {config.llm.provider} / {config.llm.model}")
    st.text(f"Embedding: {config.embedding.provider}")
    kb = get_knowledge_base()
    st.text(f"Knowledge base: {kb.count()} chunks")
    mem = get_long_term_memory()
    mem_stats = mem.get_stats()
    st.text(f"Policy versions tracked: {mem_stats['policy_versions_tracked']}")

    st.divider()
    st.header("RAG Inspector")
    rag_query = st.text_input("Query the knowledge base:")
    if rag_query:
        results = kb.query(rag_query, n_results=3)
        for r in results:
            with st.expander(f"[{r['relevance_score']:.2f}] {r['source']} — {r['section']}"):
                st.text(r["text"][:500])
                st.caption(f"Doc: {r['document_id']} v{r['version']}")


# --- Navigation ---
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "queue"

# Initialize per-case review tracking
if "case_reviews" not in st.session_state:
    st.session_state["case_reviews"] = {}


def go_to_case(case_id: str, case_data: dict):
    st.session_state["current_page"] = "detail"
    st.session_state["case_data"] = case_data
    if case_id not in st.session_state["case_reviews"]:
        st.session_state["case_reviews"][case_id] = {
            "review_state": None,
            "step_results": [],
            "current_step": "ready",
            "session_memory": None,
        }
    st.session_state["active_case_id"] = case_id


def go_to_queue():
    st.session_state["current_page"] = "queue"


# =============================================================================
# PAGE: REVIEW QUEUE (default landing)
# =============================================================================
def render_queue_page():
    st.title("KYC Compliance Review Agent")
    st.caption("AI-assisted compliance review for customer onboarding at Pacific Rim Financial Group")

    all_cases = get_all_cases()

    # Tab filters
    tab_all, tab_pending, tab_escalated, tab_completed = st.tabs(
        ["All Cases", "Pending Review", "Escalated", "Completed"]
    )

    def render_case_table(cases_to_show, tab_prefix="all"):
        if not cases_to_show:
            st.info("No cases in this category.")
            return

        for case_data in cases_to_show:
            case_id = case_data["case_id"]
            customer = case_data["customer"]
            name = customer.get("full_name", customer.get("company_name", "Unknown"))
            ctype = customer.get("type", "unknown").title()

            review_info = st.session_state["case_reviews"].get(case_id, {})
            review_state_snap = review_info.get("review_state")
            current_step = review_info.get("current_step", "ready")

            # Derive display values
            if review_state_snap:
                vals = review_state_snap.values if review_state_snap else {}
                risk_rating = vals.get("risk_rating", "pending")
                ai_decision = vals.get("decision", "N/A")
                ai_confidence = vals.get("ai_confidence")
            else:
                risk_rating = "pending"
                ai_decision = "—"
                ai_confidence = None

            if current_step == "complete":
                status = "completed"
            elif current_step in ("human_review", "awaiting_info", "running"):
                status = "in_review"
            else:
                status = "pending"

            risk_class = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high"}.get(
                risk_rating, "status-pending"
            )
            status_class = {
                "pending": "status-pending",
                "in_review": "status-in-review",
                "completed": "status-completed",
            }.get(status, "status-pending")

            # Render row
            cols = st.columns([1.2, 2, 1.2, 1.2, 1.5, 1.2, 1.2])
            with cols[0]:
                st.markdown(f"**{case_id}**")
            with cols[1]:
                st.markdown(f"{name} ({ctype})")
            with cols[2]:
                risk_label = risk_rating.upper() if risk_rating != "pending" else "PENDING"
                st.markdown(
                    f'<span class="risk-badge {risk_class}">{risk_label}</span>',
                    unsafe_allow_html=True,
                )
            with cols[3]:
                ai_label = ai_decision.upper().replace("_", " ") if ai_decision != "—" else "—"
                st.markdown(ai_label)
            with cols[4]:
                if ai_confidence is not None:
                    pct = int(ai_confidence * 100)
                    bar_color = "#28a745" if pct >= 80 else ("#ffc107" if pct >= 60 else "#dc3545")
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:6px;">'
                        f'<div class="confidence-bar" style="flex:1;">'
                        f'<div class="confidence-fill" style="width:{pct}%;background:{bar_color};"></div>'
                        f'</div><span style="font-size:12px;font-weight:600;">{pct}%</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("—")
            with cols[5]:
                st.markdown(
                    f'<span class="status-badge {status_class}">{status.replace("_", " ").upper()}</span>',
                    unsafe_allow_html=True,
                )
            with cols[6]:
                st.button("Review", key=f"review_{tab_prefix}_{case_id}", on_click=go_to_case, args=(case_id, case_data))

            st.divider()

    def _filter_by_status(cases, target_status):
        filtered = []
        for c in cases:
            cid = c["case_id"]
            review_info = st.session_state["case_reviews"].get(cid, {})
            step = review_info.get("current_step", "ready")
            if target_status == "completed" and step == "complete":
                filtered.append(c)
            elif target_status == "in_review" and step in ("human_review", "awaiting_info", "running"):
                filtered.append(c)
            elif target_status == "escalated":
                review_state_snap = review_info.get("review_state")
                if review_state_snap:
                    vals = review_state_snap.values if review_state_snap else {}
                    if vals.get("decision") == "escalate" or vals.get("risk_rating") == "high":
                        filtered.append(c)
            elif target_status == "pending" and step in ("ready",):
                filtered.append(c)
        return filtered

    # Table header
    def _render_header():
        cols = st.columns([1.2, 2, 1.2, 1.2, 1.5, 1.2, 1.2])
        headers = ["Case ID", "Customer", "Risk Level", "AI Decision", "Confidence", "Status", "Action"]
        for col, h in zip(cols, headers):
            with col:
                st.markdown(f"**{h}**")
        st.divider()

    with tab_all:
        _render_header()
        render_case_table(all_cases, "all")
    with tab_pending:
        _render_header()
        render_case_table(_filter_by_status(all_cases, "pending"), "pending")
    with tab_escalated:
        _render_header()
        render_case_table(_filter_by_status(all_cases, "escalated"), "escalated")
    with tab_completed:
        _render_header()
        render_case_table(_filter_by_status(all_cases, "completed"), "completed")


# =============================================================================
# PAGE: CASE DETAIL
# =============================================================================
def render_detail_page():
    case_data = st.session_state.get("case_data")
    if not case_data:
        st.warning("No case selected.")
        go_to_queue()
        st.rerun()
        return

    case_id = case_data["case_id"]
    review_info = st.session_state["case_reviews"].get(case_id, {})
    current_step = review_info.get("current_step", "ready")

    # Top bar
    col_back, col_title, col_status = st.columns([1, 6, 2])
    with col_back:
        st.button("← Back to Queue", on_click=go_to_queue)
    with col_title:
        customer = case_data["customer"]
        name = customer.get("full_name", customer.get("company_name", "Unknown"))
        st.markdown(f"## {case_id} — {name}")
    with col_status:
        if current_step == "complete":
            st.success("COMPLETED")
        elif current_step == "human_review":
            st.warning("AWAITING REVIEW")
        elif current_step == "awaiting_info":
            st.warning("AWAITING INFORMATION")
        elif current_step == "running":
            st.info("PROCESSING...")
        else:
            st.markdown("**PENDING**")

    # --- Run review if ready ---
    if current_step == "ready":
        st.info("Click 'Start Review' to begin the automated compliance review workflow.")
        if st.button("Start Review", type="primary", use_container_width=True):
            review_info["current_step"] = "running"
            review_info["session_memory"] = SessionMemory(case_id)
            st.session_state["case_reviews"][case_id] = review_info
            st.rerun()
        _render_case_details_tab(case_data)
        return

    if current_step == "running":
        with st.spinner("Running compliance review workflow..."):
            try:
                config = get_config()
                app = get_app()
                initial_state = ReviewState(
                    case_id=case_id,
                    submission=case_data,
                    findings=[],
                    recommendations=[],
                    sources_cited=[],
                    audit_trail=[],
                    info_requests=[],
                    current_step="intake",
                    intake_status="complete",
                    critical_missing=[],
                    non_critical_missing=[],
                    review_status="in_review",
                )
                # One case = one thread, so the request-info loop keeps its state.
                # A brand-new review of the same case gets a fresh thread, otherwise
                # fields from the previous run would leak into it.
                run_no = review_info.get("run", 1)
                thread_id = case_id if run_no == 1 else f"{case_id}#run{run_no}"
                thread_config = {"configurable": {"thread_id": thread_id}}
                step_results = []
                for event in app.stream(initial_state, thread_config):
                    for node_name, node_output in event.items():
                        step_results.append({"node": node_name, "output": node_output})

                review_info["step_results"] = step_results
                review_info["review_state"] = app.get_state(thread_config)
                review_info["thread_config"] = thread_config
                review_info["current_step"] = _step_from_pause(app, thread_config)
                st.session_state["case_reviews"][case_id] = review_info
            except Exception as e:
                review_info["current_step"] = "error"
                review_info["error_detail"] = str(e)
                st.session_state["case_reviews"][case_id] = review_info
        st.rerun()

    if current_step == "error":
        st.error(f"Review failed: {review_info.get('error_detail', 'Unknown error')}")
        st.warning("Check your LLM configuration. Try switching LLM_PROVIDER to 'openai' in .env if Ark is unreachable.")
        if st.button("Retry"):
            review_info["current_step"] = "ready"
            st.session_state["case_reviews"][case_id] = review_info
            st.rerun()
        return

    # --- Human review or Complete: show 3-column layout ---
    state_snapshot = review_info.get("review_state")
    current_values = state_snapshot.values if state_snapshot else {}

    # Tabs for the detail view
    tab_review, tab_details, tab_audit = st.tabs(["Review", "Case Details", "Audit Timeline"])

    with tab_review:
        _render_review_layout(case_id, case_data, current_values, review_info, current_step)

    with tab_details:
        _render_case_details_tab(case_data)

    with tab_audit:
        _render_audit_timeline(current_values, review_info)


def _step_from_pause(app, thread_config) -> str:
    """UI step for wherever the graph actually stopped (never assume human review)."""
    paused = pause_point(app, thread_config)
    if paused == "await_info":
        return "awaiting_info"
    if paused == "human_review":
        return "human_review"
    return "complete"


def _render_awaiting_info_panel(case_id, current_values, review_info):
    """Shown while the graph is paused at await_info: what was asked, and a form
    to supply it. The graph resumes at the node that asked, not at intake."""
    stage = current_values.get("info_request_stage", "")
    round_no = current_values.get("info_request_round", 1)
    st.warning(f"Information requested by **{stage}** (round {round_no})")
    for item in current_values.get("info_requests", []):
        st.markdown(f"- {item}")

    st.caption(
        "Paste the supplemental information as a JSON patch. It is merged into the "
        "submission (lists append; a document with the same `type` replaces the old one). "
        "The review then continues from the node that asked."
    )
    patch_text = st.text_area(
        "Supplemental information (JSON):",
        height=160,
        placeholder='{"source_of_wealth": {"supporting_documents": ["audited_financials_2023"]}}',
        key=f"patch_{case_id}",
    )
    if st.button("Submit Information", type="primary", use_container_width=True, key=f"supply_{case_id}"):
        try:
            patch = json.loads(patch_text)
            if not isinstance(patch, dict) or not patch:
                raise ValueError("The patch must be a non-empty JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Invalid JSON patch: {e}")
            return
        try:
            app = get_app()
            thread_config = review_info["thread_config"]
            supply_information(app, thread_config, patch)
            results = list(review_info.get("step_results", []))
            for event in app.stream(None, thread_config):
                for node_name, node_output in event.items():
                    results.append({"node": node_name, "output": node_output})
            review_info["step_results"] = results
            review_info["review_state"] = app.get_state(thread_config)
            review_info["current_step"] = _step_from_pause(app, thread_config)
            st.session_state["case_reviews"][case_id] = review_info
        except Exception as e:
            st.error(f"Error resuming review: {e}")
            return
        st.rerun()


def _render_review_layout(case_id, case_data, current_values, review_info, current_step):
    """3-column layout: left=customer info, center=AI reasoning, right=decision panel."""

    col_left, col_center, col_right = st.columns([1.5, 3, 1.8])

    # === LEFT COLUMN: Customer Info Card ===
    with col_left:
        st.markdown("### Customer Info")
        customer = case_data["customer"]
        ctype = customer.get("type", "unknown")

        st.markdown(f'<div class="info-card">', unsafe_allow_html=True)
        if ctype == "individual":
            st.markdown(f"**Name:** {customer.get('full_name', 'N/A')}")
            st.markdown(f"**DOB:** {customer.get('date_of_birth', 'N/A')}")
            st.markdown(f"**Nationality:** {customer.get('nationality', 'N/A')}")
            st.markdown(f"**Occupation:** {customer.get('occupation', 'N/A')}")
            st.markdown(f"**Employer:** {customer.get('employer', 'N/A')}")
            income = customer.get("annual_income")
            currency = customer.get("income_currency", "")
            if income:
                st.markdown(f"**Annual Income:** {currency} {income:,.0f}")
        else:
            st.markdown(f"**Company:** {customer.get('company_name', 'N/A')}")
            st.markdown(f"**Reg. Number:** {customer.get('registration_number', 'N/A')}")
            jurisdiction = customer.get("country_of_incorporation", customer.get("jurisdiction", "N/A"))
            industry = customer.get("business_type", customer.get("industry", "N/A"))
            st.markdown(f"**Jurisdiction:** {jurisdiction}")
            st.markdown(f"**Industry:** {industry}")
            revenue = customer.get("annual_revenue")
            if revenue:
                st.markdown(f"**Annual Revenue:** {customer.get('revenue_currency', 'USD')} {revenue:,.0f}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Risk summary card
        risk_rating = current_values.get("risk_rating", "N/A")
        risk_total = current_values.get("risk_total", 0)
        dd_level = current_values.get("due_diligence_level", "standard")
        # 5 factors x 3 = 15, plus 1 when intake was conditional (see risk_assessment_node)
        max_score = 15 + (1 if current_values.get("intake_status") == "conditional" else 0)
        rating_color = {"low": "#28a745", "medium": "#ffc107", "high": "#dc3545"}.get(risk_rating, "#6c757d")

        st.markdown("### Risk Summary")
        st.markdown(
            f'<div class="info-card" style="border-left:4px solid {rating_color};">'
            f'<div style="font-size:24px;font-weight:bold;color:{rating_color};">{risk_rating.upper()}</div>'
            f'<div style="font-size:13px;color:#666;">Score: {risk_total}/{max_score} | DD: {dd_level.upper()}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Risk factor breakdown
        risk_scores = current_values.get("risk_scores", {})
        if risk_scores:
            factor_labels = {
                "customer_type": "Customer Type",
                "geography": "Geography",
                "product_service": "Product/Service",
                "transaction_pattern": "Transaction",
                "source_of_funds": "Source of Funds",
            }
            for key, data in risk_scores.items():
                score = data.get("score", 0) if isinstance(data, dict) else data
                label = factor_labels.get(key, key.replace("_", " ").title())
                bar_color = "#28a745" if score == 1 else ("#ffc107" if score == 2 else "#dc3545")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:2px;">'
                    f'<span>{label}</span><span style="color:{bar_color};font-weight:600;">{score}/3</span></div>'
                    f'<div class="confidence-bar"><div class="confidence-fill" style="width:{score/3*100}%;background:{bar_color};"></div></div>',
                    unsafe_allow_html=True,
                )

        # Screening results
        st.markdown("### Screening")
        screening_map = {
            "Sanctions": current_values.get("sanctions_result", "N/A"),
            "PEP": current_values.get("pep_result", "N/A"),
            "Adverse Media": current_values.get("adverse_media_result", "N/A"),
        }
        for check_name, result_val in screening_map.items():
            icon = {"clear": "✅", "potential_match": "⚠️", "confirmed_match": "❌"}.get(result_val, "•")
            color = {"clear": "#28a745", "potential_match": "#ffc107", "confirmed_match": "#dc3545"}.get(result_val, "#6c757d")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                f'<span>{icon}</span>'
                f'<span style="font-size:13px;">{check_name}:</span>'
                f'<span style="color:{color};font-weight:600;font-size:13px;">{result_val.upper().replace("_", " ")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # === CENTER COLUMN: AI Reasoning with cited SOP clauses ===
    with col_center:
        # Intake status warning
        intake_status = current_values.get("intake_status", "complete")
        if intake_status == "conditional":
            non_critical = current_values.get("non_critical_missing", [])
            st.warning(
                f"**Conditional Intake** — Proceeding with missing non-critical documents: "
                f"{', '.join(non_critical) if non_critical else 'N/A'}. Risk score adjusted +1."
            )

        st.markdown("### AI Reasoning Steps")

        # Build source lookup: doc_id → {title, chunk_preview}
        all_sources = []
        source_footnotes = {}
        source_details = {}
        ref_counter = 1
        kb = get_knowledge_base()
        for src_group in current_values.get("sources_cited", []):
            step_name = src_group.get("step", "unknown")
            for src in src_group.get("sources", []):
                if src not in source_footnotes:
                    source_footnotes[src] = ref_counter
                    chunks = kb.query(src, n_results=1)
                    if chunks:
                        title = chunks[0].get("source", src)
                        version = chunks[0].get("version", "")
                        section = chunks[0].get("section", "")
                        raw = chunks[0]["text"].replace("#", "").replace("**", "").replace("*", "")
                        raw = " ".join(raw.split())
                        preview = raw[:150].strip()
                        if len(raw) > 150:
                            preview += "..."
                    else:
                        title = src
                        version = ""
                        section = ""
                        preview = ""
                    source_details[ref_counter] = {
                        "doc_id": src, "title": title, "version": version,
                        "section": section, "preview": preview,
                    }
                    all_sources.append({"ref": ref_counter, "doc_id": src, "title": title, "version": version})
                    ref_counter += 1

        def _make_ref_html(ref_num):
            info = source_details.get(ref_num, {})
            title = info.get("title", "")
            section = info.get("section", "")
            preview = info.get("preview", "").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            tip_title = f"{title}"
            if section:
                tip_title += f" — {section}"
            return (
                f'<span class="source-ref">[{ref_num}]'
                f'<span class="tip"><div class="tip-title">{tip_title}</div>'
                f'<div class="tip-chunk">{preview}</div></span>'
                f'</span>'
            )

        findings = current_values.get("findings", [])
        step_sources = current_values.get("sources_cited", [])

        step_display = {
            "intake": "Document Intake & Validation",
            "screening": "Identity Screening (Sanctions / PEP / Adverse Media)",
            "identity_screening": "Identity Screening (Sanctions / PEP / Adverse Media)",
            "risk_assessment": "Risk Assessment & Scoring",
            "standard_review": "Standard Due Diligence Review",
            "edd": "Enhanced Due Diligence",
            "enhanced_due_diligence": "Enhanced Due Diligence",
        }

        # sources_cited uses "edd"; the audit trail uses "enhanced_due_diligence"
        _SOURCE_STEP_ALIASES = {"edd": "enhanced_due_diligence"}

        audit_trail = current_values.get("audit_trail", [])
        displayed_steps = set()
        for entry in audit_trail:
            step = entry.get("step", "")
            if step in displayed_steps or step in ("human_review", "decision"):
                continue
            displayed_steps.add(step)

            step_label = step_display.get(step, step.replace("_", " ").title())
            details = entry.get("details", "")
            sources_used = entry.get("sources_used", "")

            footnote_refs = []
            for src_group in step_sources:
                group_step = _SOURCE_STEP_ALIASES.get(src_group.get("step", ""), src_group.get("step", ""))
                if group_step == step or group_step in step:
                    for s in src_group.get("sources", []):
                        if s in source_footnotes:
                            footnote_refs.append(source_footnotes[s])

            refs_html = " ".join(_make_ref_html(r) for r in footnote_refs)

            st.markdown(
                f'<div class="info-card">'
                f'<div style="font-weight:600;margin-bottom:4px;">{step_label} {refs_html}</div>'
                f'<div style="font-size:13px;color:#555;line-height:1.6;">{details[:400]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # EDD findings
        if current_values.get("edd_findings"):
            edd = current_values["edd_findings"]
            with st.expander("Enhanced Due Diligence Details"):
                if edd.get("source_of_wealth"):
                    st.markdown(f"**Source of Wealth:** {edd['source_of_wealth']}")
                if edd.get("source_of_funds"):
                    st.markdown(f"**Source of Funds:** {edd['source_of_funds']}")
                if edd.get("risk_mitigants"):
                    st.markdown("**Risk Mitigants:** " + "; ".join(edd["risk_mitigants"]))
                if edd.get("risk_amplifiers"):
                    st.markdown("**Risk Amplifiers:** " + "; ".join(edd["risk_amplifiers"]))

        if findings:
            with st.expander("All Findings"):
                for f in findings:
                    st.markdown(f"- {f}")

        # Policy Sources — simple list
        if all_sources:
            st.markdown("### Policy Sources Referenced")
            for src_info in all_sources:
                ref_num = src_info["ref"]
                title = src_info["title"]
                version = src_info["version"]
                ver_str = f" v{version}" if version else ""
                st.markdown(f"**[{ref_num}]** {title}{ver_str}")

    # === RIGHT COLUMN: AI Recommendation + Human Decision (always visible) ===
    with col_right:
        # --- AI Recommendation (read-only) ---
        st.markdown("### AI Recommendation")
        agent_decision = current_values.get("decision", "N/A")
        ai_confidence = current_values.get("ai_confidence")
        rationale = current_values.get("decision_rationale", "")
        decision_colors = {
            "approve": "#28a745", "reject": "#dc3545",
            "request_more_info": "#ffc107", "escalate": "#17a2b8",
            "approve_with_conditions": "#20c997",
        }
        decision_color = decision_colors.get(agent_decision, "#6c757d")

        st.markdown(
            f'<div style="background:linear-gradient(135deg, {decision_color}22, {decision_color}11);'
            f'border-left:4px solid {decision_color};padding:12px;border-radius:6px;">'
            f'<div style="font-size:18px;font-weight:bold;color:{decision_color};">'
            f'{agent_decision.upper().replace("_", " ")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Confidence bar
        if ai_confidence is not None:
            pct = int(ai_confidence * 100)
            bar_color = "#28a745" if pct >= 80 else ("#ffc107" if pct >= 60 else "#dc3545")
            st.markdown(
                f'<div style="margin:8px 0;">'
                f'<div style="font-size:12px;color:#666;margin-bottom:4px;">Confidence: {pct}%</div>'
                f'<div class="confidence-bar">'
                f'<div class="confidence-fill" style="width:{pct}%;background:{bar_color};"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        if rationale:
            with st.expander("AI Rationale"):
                st.markdown(f"<div style='font-size:13px;line-height:1.5;'>{rationale}</div>", unsafe_allow_html=True)

        st.divider()

        # --- Human Decision Panel ---
        st.markdown("### Human Decision")

        if current_step == "human_review":
            st.markdown('<div class="decision-panel">', unsafe_allow_html=True)
            decision_options = ["approve", "approve_with_conditions", "reject", "request_more_info", "escalate"]
            default_idx = decision_options.index(agent_decision) if agent_decision in decision_options else 0
            human_decision = st.selectbox("Decision:", decision_options, index=default_idx, key=f"dec_{case_id}")
            human_notes = st.text_area(
                "Review notes (required):",
                height=100,
                placeholder="Document your reasoning...",
                key=f"notes_{case_id}",
            )

            if st.button("Submit Decision", type="primary", use_container_width=True, key=f"submit_{case_id}"):
                if not human_notes.strip():
                    st.error("Review notes are required.")
                else:
                    try:
                        app = get_app()
                        thread_config = review_info["thread_config"]
                        app.update_state(
                            thread_config,
                            {"human_decision": human_decision, "human_notes": human_notes},
                            as_node="human_review",
                        )
                        final_results = list(review_info.get("step_results", []))
                        for event in app.stream(None, thread_config):
                            for node_name, node_output in event.items():
                                final_results.append({"node": node_name, "output": node_output})

                        review_info["step_results"] = final_results
                        final_state = app.get_state(thread_config)
                        review_info["review_state"] = final_state
                        review_info["current_step"] = _step_from_pause(app, thread_config)
                        st.session_state["case_reviews"][case_id] = review_info
                    except Exception as e:
                        st.error(f"Error finalizing review: {str(e)}")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        elif current_step == "awaiting_info":
            _render_awaiting_info_panel(case_id, current_values, review_info)

        elif current_step == "complete":
            final_values = state_snapshot.values if (state_snapshot := review_info.get("review_state")) else {}
            human_dec = final_values.get("human_decision", "N/A")
            human_notes_val = final_values.get("human_notes", "")
            agreement = final_values.get("ai_human_agreement")

            dec_color = decision_colors.get(human_dec, "#6c757d")
            st.markdown(
                f'<div style="background:linear-gradient(135deg, {dec_color}22, {dec_color}11);'
                f'border-left:4px solid {dec_color};padding:12px;border-radius:6px;">'
                f'<div style="font-size:18px;font-weight:bold;color:{dec_color};">'
                f'{human_dec.upper().replace("_", " ")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Agreement indicator
            if agreement is not None:
                if agreement:
                    st.markdown(
                        '<div class="agreement-match" style="margin-top:8px;">✅ AI and Human decisions AGREE</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="agreement-mismatch" style="margin-top:8px;">⚠️ AI and Human decisions DIFFER</div>',
                        unsafe_allow_html=True,
                    )

            if human_notes_val:
                st.markdown("**Reviewer Notes:**")
                st.markdown(f"<div style='font-size:13px;'>{human_notes_val}</div>", unsafe_allow_html=True)

            st.divider()
            if st.button("Start New Review", key=f"new_{case_id}"):
                review_info["run"] = review_info.get("run", 1) + 1
                review_info["current_step"] = "ready"
                review_info["review_state"] = None
                review_info["step_results"] = []
                st.session_state["case_reviews"][case_id] = review_info
                st.rerun()


def _render_case_details_tab(case_data):
    """Render the case details tab as readable text."""
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Customer Information")
        customer = case_data.get("customer", {})
        ctype = customer.get("type", "unknown")
        if ctype == "individual":
            fields = [
                ("Full Name", customer.get("full_name")),
                ("Date of Birth", customer.get("date_of_birth")),
                ("Nationality", customer.get("nationality")),
                ("Country of Residence", customer.get("country_of_residence")),
                ("Occupation", customer.get("occupation")),
                ("Employer", customer.get("employer")),
            ]
            income = customer.get("annual_income")
            if income:
                currency = customer.get("income_currency", "")
                fields.append(("Annual Income", f"{currency} {income:,.0f}"))
        else:
            fields = [
                ("Company Name", customer.get("company_name")),
                ("Registration No.", customer.get("registration_number")),
                ("Jurisdiction", customer.get("country_of_incorporation", customer.get("jurisdiction"))),
                ("Business Type", customer.get("business_type", customer.get("industry"))),
            ]
            revenue = customer.get("annual_revenue")
            if revenue:
                currency = customer.get("revenue_currency", "USD")
                fields.append(("Annual Revenue", f"{currency} {revenue:,.0f}"))
        for label, value in fields:
            if value:
                st.markdown(f"**{label}:** {value}")

        st.subheader("Account Request")
        acct = case_data.get("account_request", {})
        acct_fields = [
            ("Product Type", acct.get("product_type", "").replace("_", " ").title()),
            ("Purpose", acct.get("purpose")),
            ("Initial Deposit", f"{acct.get('initial_deposit', 0):,.0f}" if acct.get("initial_deposit") else None),
            ("Source of Initial Deposit", acct.get("source_of_initial_deposit")),
        ]
        countries = acct.get("primary_transaction_countries")
        if countries:
            acct_fields.append(("Transaction Countries", ", ".join(countries)))
        for label, value in acct_fields:
            if value:
                st.markdown(f"**{label}:** {value}")

    with col_b:
        st.subheader("Documents")
        for doc in case_data.get("identification_documents", []):
            icon = "✅" if doc.get("verified") or doc.get("provided") else "❌"
            doc_type = doc.get("type", "unknown").replace("_", " ").title()
            note = doc.get("note", doc.get("document_number", "N/A"))
            st.markdown(f"{icon} **{doc_type}** — {note}")

        sof = case_data.get("source_of_funds", {})
        if sof:
            st.subheader("Source of Funds")
            st.markdown(f"**Primary:** {sof.get('primary', 'N/A').replace('_', ' ').title()}")
            if sof.get("details"):
                st.markdown(sof["details"])

        decl = case_data.get("declarations", {})
        if decl:
            st.subheader("Declarations")
            pep = "Yes" if decl.get("pep_status") else "No"
            st.markdown(f"**PEP Status:** {pep}")
            if decl.get("pep_details"):
                st.caption(decl["pep_details"])
            st.markdown(f"**US Person:** {'Yes' if decl.get('us_person') else 'No'}")
            tax = decl.get("tax_residency", [])
            if tax:
                st.markdown(f"**Tax Residency:** {', '.join(tax)}")

        if case_data.get("screening_flags"):
            st.subheader("Pre-existing Screening Flags")
            flags = case_data["screening_flags"]
            for flag_name, flag_data in flags.items():
                label = flag_name.replace("_", " ").title()
                result = flag_data.get("result", "N/A") if isinstance(flag_data, dict) else str(flag_data)
                icon = {"clear": "✅", "confirmed_match": "❌", "potential_match": "⚠️"}.get(result, "•")
                st.markdown(f"{icon} **{label}:** {result.replace('_', ' ').title()}")
                if isinstance(flag_data, dict) and flag_data.get("details"):
                    st.caption(flag_data["details"])


def _render_audit_timeline(current_values, review_info):
    """Render a visual timeline of all workflow steps."""
    audit_trail = current_values.get("audit_trail", [])

    if not audit_trail:
        st.info("No audit entries yet. Run a review to see the audit trail.")
        return

    st.markdown("### Audit Timeline")
    st.caption("Each entry shows the workflow step, action taken, sources consulted, and timestamp.")

    config = get_config()
    model_version = f"{config.llm.provider}/{config.llm.model}"

    ai_steps = {"intake", "identity_screening", "risk_assessment", "standard_review", "enhanced_due_diligence", "decision"}
    human_steps = {"human_review"}

    for entry in audit_trail:
        step = entry.get("step", "unknown")
        action = entry.get("action", "")
        details = entry.get("details", "")
        sources_used = entry.get("sources_used", "")
        ts = entry.get("timestamp", "")

        ts_display = ts[:19].replace("T", " ") if ts else "—"

        if step in human_steps:
            dot_class = "timeline-dot-human"
            step_type = "HUMAN"
        elif sources_used:
            dot_class = "timeline-dot-rag"
            step_type = "AI + RAG"
        elif step in ai_steps:
            dot_class = "timeline-dot-ai"
            step_type = "AI"
        else:
            dot_class = "timeline-dot-system"
            step_type = "SYSTEM"

        step_label = step.replace("_", " ").title()
        action_label = action.replace("_", " ").title()
        details_display = (details[:250] + "...") if len(details) > 250 else details

        source_chips = ""
        if sources_used:
            for src_id in sources_used.split(", ")[:5]:
                if src_id.strip():
                    source_chips += f'<span class="source-ref">{src_id.strip()}</span>'

        st.markdown(
            f'<div class="timeline-item">'
            f'<div class="timeline-dot {dot_class}"></div>'
            f'<div class="timeline-ts">{ts_display} | {step_type} | Model: {model_version}</div>'
            f'<div class="timeline-label">{step_label}: {action_label}</div>'
            f'<div class="timeline-detail">{details_display}</div>'
            f'{f"<div style=margin-top:4px;>{source_chips}</div>" if source_chips else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Also show raw step results expandable
    step_results = review_info.get("step_results", [])
    if step_results:
        st.divider()
        st.markdown("### Detailed Step Outputs")
        for i, step in enumerate(step_results):
            with st.expander(f"Step {i+1}: {step['node'].replace('_', ' ').title()}"):
                output = step["output"]
                if isinstance(output, dict):
                    for k, v in output.items():
                        label = k.replace("_", " ").title()
                        if isinstance(v, list):
                            st.markdown(f"**{label}:**")
                            for item in v:
                                if isinstance(item, dict):
                                    summary = item.get("details", item.get("action", str(item)))
                                    st.markdown(f"- {summary}")
                                else:
                                    st.markdown(f"- {item}")
                        elif isinstance(v, dict):
                            st.markdown(f"**{label}:**")
                            for sk, sv in v.items():
                                st.markdown(f"  - {sk.replace('_', ' ').title()}: {sv}")
                        else:
                            st.markdown(f"**{label}:** {v}")
                else:
                    st.write(output)


# =============================================================================
# ROUTER
# =============================================================================
if st.session_state["current_page"] == "queue":
    render_queue_page()
elif st.session_state["current_page"] == "detail":
    render_detail_page()
