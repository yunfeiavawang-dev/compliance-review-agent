"""KYC Compliance Review Agent — Document-Flow Layout.

Lark/Feishu-inspired doc-flow: all review sections top-to-bottom,
left sidebar TOC with section confirmation checkboxes, decision
locked until every section is reviewed.
"""

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
from src.models import get_llm_client, chat_completion

from src.auth.rbac import Role, Permission, get_current_user, UserContext
from src.auth.audit_logger import AuditLogger, AuditAction
from src.auth.pii import mask_pii, mask_name


# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════
TENANTS = {
    "Pacific Rim Financial Group": "pacific_rim_fg",
    "ACME Bank HK": "acme_bank_hk",
    "Oceanic Securities": "oceanic_securities",
    "Dragon Capital Asia": "dragon_capital_asia",
}

SECTION_NAMES = [
    "Customer Profile",
    "Document Verification",
    "Screening Results",
    "Risk Assessment",
    "Source of Wealth",
    "Enhanced Due Diligence",
    "AI Analysis & Sources",
    "Findings Summary",
]

SEVERITY_COLORS = {
    "critical": "#f54a45",
    "warning": "#ff7d00",
    "info": "#3370ff",
    "clear": "#34c724",
    "default": "#dee0e3",
}

BADGE_STYLES = {
    "alert": "background:#fff0f0; color:#d83931;",
    "warn": "background:#fff3e5; color:#d4760a;",
    "info": "background:#e8f3ff; color:#3370ff;",
    "pass": "background:#e8fce8; color:#1a8a1a;",
}


# ═══════════════════════════════════════════════════════════════════
# Page Config & CSS
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="KYC Compliance Review",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .risk-badge { display:inline-block; padding:2px 10px; border-radius:12px;
                  font-weight:600; font-size:13px; text-transform:uppercase; }
    .risk-low { background:#d4edda; color:#155724; }
    .risk-medium { background:#fff3cd; color:#856404; }
    .risk-high { background:#f8d7da; color:#721c24; }
    .status-badge { display:inline-block; padding:2px 10px; border-radius:12px;
                    font-size:12px; font-weight:500; }
    .status-pending { background:#e2e3e5; color:#383d41; }
    .status-in-review { background:#cce5ff; color:#004085; }
    .status-completed { background:#d4edda; color:#155724; }
    .severity-bar { height:3px; border-radius:2px; margin-bottom:4px; }
    .sec-badge { padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
    .dgrid { display:grid; grid-template-columns:160px 1fr; gap:0; }
    .dgrid .dl { padding:7px 0; font-size:13px; color:#8f959e; border-bottom:1px solid #f5f6f7; }
    .dgrid .dv { padding:7px 0; font-size:13px; border-bottom:1px solid #f5f6f7; }
    .mem-card { background:#fafbfc; border:1px solid #e8e9eb; border-left:3px solid #3370ff;
                border-radius:0 6px 6px 0; padding:14px 16px; margin:8px 0; }
    .mem-entry { font-size:12px; color:#646a73; padding:6px 0; border-bottom:1px dashed #e8e9eb; }
    .mem-entry:last-child { border-bottom:none; }
    .mem-tag { display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px;
               font-weight:600; margin-right:4px; }
    .mem-tag-high { background:#fff0f0; color:#d83931; }
    .mem-tag-med { background:#fff3e5; color:#d4760a; }
    .mem-tag-low { background:#e8fce8; color:#1a8a1a; }
    .doc-table { width:100%; border-collapse:collapse; font-size:13px; }
    .doc-table th { text-align:left; padding:8px 10px; background:#f5f6f7;
                    font-weight:600; font-size:12px; color:#646a73; }
    .doc-table td { padding:8px 10px; border-bottom:1px solid #f5f6f7; }
    .doc-ok { color:#34c724; font-weight:600; }
    .doc-expired { color:#d83931; font-weight:600; }
    .scr-row { display:flex; gap:12px; margin-bottom:14px; }
    .scr-card { flex:1; border:1px solid #e8e9eb; border-radius:6px; padding:14px; }
    .scr-card.alert { border-color:#ffccc7; background:#fff8f7; }
    .scr-card.clear { border-color:#d4edda; background:#f8fdf8; }
    .scr-label { font-size:11px; font-weight:600; color:#8f959e; text-transform:uppercase;
                 letter-spacing:0.3px; margin-bottom:6px; }
    .scr-result { font-size:14px; font-weight:600; }
    .scr-result.match { color:#d83931; }
    .scr-result.ok { color:#1a8a1a; }
    .scr-detail { font-size:12px; color:#646a73; margin-top:6px; line-height:1.5; }
    .risk-score-big { font-size:40px; font-weight:700; line-height:1; }
    .risk-bar-bg { height:8px; border-radius:4px; overflow:hidden;
                   background:linear-gradient(90deg,#34c724 0%,#34c724 39%,#ff7d00 40%,#ff7d00 59%,#f54a45 60%,#f54a45 100%); }
    .risk-factor { text-align:center; padding:10px 6px; background:#f5f6f7; border-radius:6px; }
    .risk-factor-score { font-size:20px; font-weight:700; }
    .risk-factor-label { font-size:10px; color:#8f959e; margin-top:2px; line-height:1.3; }
    .ai-rec { background:linear-gradient(135deg,#f0f4ff,#f5f0ff); border:1px solid #bdd4ff;
              border-radius:8px; padding:16px 20px; }
    .ai-rec-decision { font-size:16px; font-weight:600; margin-bottom:8px; }
    .src-ref { background:#e9ecef; padding:1px 6px; border-radius:4px; font-size:11px;
               color:#495057; margin-right:4px; }
    .callout { padding:10px 14px; border-radius:6px; font-size:13px; margin-top:12px; }
    .callout-red { background:#fff0f0; border:1px solid #ffccc7; color:#d83931; }
    .callout-orange { background:#fffaf5; border:1px solid #ffe0c2; color:#9a5c00; }
    .callout-blue { background:#f5f8ff; border:1px solid #bdd4ff; color:#2b5baa; }
    .callout-green { background:#f0fdf0; border:1px solid #c6efc6; color:#1a6d1a; }
    .finding { padding:10px 14px; margin-bottom:8px; border-radius:0 6px 6px 0; font-size:13px; }
    .finding-critical { border-left:3px solid #f54a45; background:#fff8f7; }
    .finding-warning { border-left:3px solid #ff7d00; background:#fffaf5; }
    .finding-info { border-left:3px solid #3370ff; background:#f5f8ff; }
    .finding-src { font-size:11px; color:#8f959e; margin-top:4px; }
    .prior-callout { background:#fffaf0; border:1px solid #ffe0c2; border-radius:8px;
                     padding:14px 18px; margin-bottom:16px; font-size:13px; }
    .prior-callout-title { font-weight:600; color:#d4760a; margin-bottom:6px; }
    .audit-row { display:flex; gap:12px; font-size:11px; color:#646a73; padding:3px 0;
                 border-bottom:1px solid #e8e9eb; }
    .audit-row:last-child { border-bottom:none; }
    .audit-time { color:#b0b5bd; min-width:130px; }
    .audit-actor { color:#3370ff; }
    .data-class { display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px;
                  font-weight:600; }
    .data-class-confidential { background:#fff0f0; color:#d83931; }
    .conf-bar { height:8px; border-radius:4px; background:#e9ecef; overflow:hidden; display:inline-block; width:100%; }
    .conf-fill { height:100%; border-radius:4px; }
    .conf-sm { height:4px; width:60px; background:#dee0e3; border-radius:2px;
               display:inline-block; vertical-align:middle; margin-left:6px; overflow:hidden; }
    .conf-sm-fill { height:100%; background:#3370ff; border-radius:2px; }
    .four-eyes { background:#fffaf5; border:1px solid #ffe0c2; border-radius:6px;
                 padding:10px 14px; font-size:13px; color:#9a5c00; margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# Cached Resources
# ═══════════════════════════════════════════════════════════════════
@st.cache_resource
def get_config():
    return load_config()

@st.cache_resource
def get_app():
    return create_app(get_config())

@st.cache_resource
def get_knowledge_base():
    config = get_config()
    kb = ComplianceKnowledgeBase(config)
    if kb.collection.count() == 0:
        from src.knowledge.ingestion import ingest_documents
        ingest_documents(config)
        kb = ComplianceKnowledgeBase(config)
    return kb

@st.cache_resource
def get_long_term_memory():
    return LongTermMemory()

@st.cache_resource
def get_audit_logger():
    return AuditLogger()


# ═══════════════════════════════════════════════════════════════════
# Data Loading & PII Helper
# ═══════════════════════════════════════════════════════════════════
def get_all_cases() -> list[dict]:
    cases = []
    data_dir = Path("data/customers")
    for f in sorted(data_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        data["_file_path"] = str(f)
        cases.append(data)
    return cases


def pii(text: str) -> str:
    if st.session_state.get("pii_visible", True):
        return str(text)
    return mask_name(str(text))


# ═══════════════════════════════════════════════════════════════════
# Session State & Navigation
# ═══════════════════════════════════════════════════════════════════
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "queue"
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


def _step_from_pause(app, thread_config) -> str:
    paused = pause_point(app, thread_config)
    if paused == "await_info":
        return "awaiting_info"
    if paused == "human_review":
        return "human_review"
    return "complete"


# ═══════════════════════════════════════════════════════════════════
# Enterprise Controls — Sidebar (always present)
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### KYC Review")

    tenant_name = st.selectbox(
        "Client (Tenant)",
        list(TENANTS.keys()),
        index=list(TENANTS.keys()).index(
            st.session_state.get("tenant_name", "Pacific Rim Financial Group")
        ),
        key="tenant_select",
    )
    st.session_state["tenant_name"] = tenant_name
    tenant_id = TENANTS[tenant_name]

    role_options = [r.value for r in Role]
    selected_role = st.selectbox(
        "Role (Demo)",
        role_options,
        index=role_options.index(
            st.session_state.get("demo_role", Role.SENIOR_ANALYST.value)
        ),
        key="role_switcher",
    )
    st.session_state["demo_role"] = selected_role
    current_user = UserContext(
        user_id="demo-user-001",
        username="demo_analyst",
        role=Role(selected_role),
        tenant_id=tenant_id,
        email="analyst@pacificrim.example",
        ip_address="127.0.0.1",
    )
    st.caption(f"**{current_user.username}** · `{current_user.role.value}` · `{tenant_id}`")

    st.session_state["pii_visible"] = st.checkbox(
        "PII Visible", value=st.session_state.get("pii_visible", True), key="pii_toggle"
    )

    st.divider()

    config = get_config()
    with st.expander("System Info", expanded=False):
        st.text(f"LLM: {config.llm.provider} / {config.llm.model}")
        st.text(f"Embedding: {config.embedding.provider}")
        kb = get_knowledge_base()
        st.text(f"Knowledge base: {kb.count()} chunks")
        mem = get_long_term_memory()
        st.text(f"Policy versions: {mem.get_stats()['policy_versions_tracked']}")


# ═══════════════════════════════════════════════════════════════════
# PAGE: REVIEW QUEUE
# ═══════════════════════════════════════════════════════════════════
def render_queue_page():
    st.title("KYC Compliance Review Agent")
    st.caption(
        f"AI-assisted compliance review · {st.session_state.get('tenant_name', 'Pacific Rim Financial Group')}"
    )

    all_cases = get_all_cases()

    with st.sidebar:
        st.markdown("**My Queue**")
        st.caption(f"{len(all_cases)} cases assigned")

    tab_all, tab_pending, tab_escalated, tab_completed = st.tabs(
        ["All Cases", "Pending Review", "Escalated", "Completed"]
    )

    def _render_cases(cases_list, prefix="all"):
        if not cases_list:
            st.info("No cases in this category.")
            return
        cols = st.columns([1.2, 2, 1.2, 1.2, 1.5, 1.2, 1.2])
        for col, h in zip(cols, ["Case ID", "Customer", "Risk", "AI Decision", "Confidence", "Status", "Action"]):
            with col:
                st.markdown(f"**{h}**")
        st.divider()

        for case_data in cases_list:
            case_id = case_data["case_id"]
            customer = case_data["customer"]
            name = customer.get("full_name", customer.get("company_name", "Unknown"))

            review_info = st.session_state["case_reviews"].get(case_id, {})
            state_snap = review_info.get("review_state")
            vals = state_snap.values if state_snap else {}
            current_step = review_info.get("current_step", "ready")

            risk_rating = vals.get("risk_rating", "pending")
            ai_decision = vals.get("decision", "—")
            ai_confidence = vals.get("ai_confidence")

            if current_step == "complete":
                status = "completed"
            elif current_step in ("human_review", "awaiting_info", "running"):
                status = "in_review"
            else:
                status = "pending"

            risk_cls = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high"}.get(risk_rating, "status-pending")
            status_cls = {"pending": "status-pending", "in_review": "status-in-review", "completed": "status-completed"}.get(status, "status-pending")

            cols = st.columns([1.2, 2, 1.2, 1.2, 1.5, 1.2, 1.2])
            with cols[0]:
                st.markdown(f"**{case_id}**")
            with cols[1]:
                st.markdown(name)
            with cols[2]:
                label = risk_rating.upper() if risk_rating != "pending" else "PENDING"
                st.markdown(f'<span class="risk-badge {risk_cls}">{label}</span>', unsafe_allow_html=True)
            with cols[3]:
                st.markdown(ai_decision.upper().replace("_", " ") if ai_decision != "—" else "—")
            with cols[4]:
                if ai_confidence is not None:
                    pct = int(ai_confidence * 100)
                    color = "#28a745" if pct >= 80 else ("#ffc107" if pct >= 60 else "#dc3545")
                    st.markdown(
                        f'<div class="conf-bar"><div class="conf-fill" style="width:{pct}%;background:{color};"></div></div>'
                        f'<span style="font-size:12px;font-weight:600;">{pct}%</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("—")
            with cols[5]:
                st.markdown(f'<span class="status-badge {status_cls}">{status.replace("_", " ").upper()}</span>', unsafe_allow_html=True)
            with cols[6]:
                st.button("Review", key=f"rev_{prefix}_{case_id}", on_click=go_to_case, args=(case_id, case_data))
            st.divider()

    def _filter(cases, target):
        out = []
        for c in cases:
            info = st.session_state["case_reviews"].get(c["case_id"], {})
            step = info.get("current_step", "ready")
            if target == "completed" and step == "complete":
                out.append(c)
            elif target == "in_review" and step in ("human_review", "awaiting_info", "running"):
                out.append(c)
            elif target == "escalated":
                snap = info.get("review_state")
                if snap:
                    v = snap.values if snap else {}
                    if v.get("decision") == "escalate" or v.get("risk_rating") == "high":
                        out.append(c)
            elif target == "pending" and step == "ready":
                out.append(c)
        return out

    with tab_all:
        _render_cases(all_cases, "all")
    with tab_pending:
        _render_cases(_filter(all_cases, "pending"), "pend")
    with tab_escalated:
        _render_cases(_filter(all_cases, "escalated"), "esc")
    with tab_completed:
        _render_cases(_filter(all_cases, "completed"), "comp")


# ═══════════════════════════════════════════════════════════════════
# PAGE: CASE DETAIL — Document-Flow Review
# ═══════════════════════════════════════════════════════════════════
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
    customer = case_data["customer"]
    name = customer.get("full_name", customer.get("company_name", "Unknown"))

    # ── Run workflow (use cache if available) ──
    if current_step == "running":
        from src.cache import load_case_cache
        cached = load_case_cache(case_id)
        if cached:
            import time as _time
            with st.spinner("Loading review results..."):
                _time.sleep(1.5)
            step_results, state_values, cached_step = cached

            class _CachedState:
                def __init__(self, v):
                    self.values = v
            review_info["step_results"] = step_results
            review_info["review_state"] = _CachedState(state_values)
            review_info["current_step"] = cached_step
            review_info["thread_config"] = {"configurable": {"thread_id": case_id}}
            review_info["from_cache"] = True
            st.session_state["case_reviews"][case_id] = review_info
            st.rerun()

        with st.spinner("Running compliance review workflow..."):
            try:
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
                    tenant_id=current_user.tenant_id,
                    data_classification="confidential",
                )
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

    # ── Resolve state values ──
    state_snap = review_info.get("review_state")
    cv = state_snap.values if state_snap else {}
    risk_rating = cv.get("risk_rating", "pending")

    # ── Sidebar: Case Queue + TOC ──
    with st.sidebar:
        all_cases = get_all_cases()
        st.markdown("**My Queue**")
        for c in all_cases[:6]:
            cid = c["case_id"]
            cname = c["customer"].get("full_name", c["customer"].get("company_name", "?"))
            is_active = cid == case_id
            label = f"{'▸ ' if is_active else ''}{cname}"
            if st.button(label, key=f"sq_{cid}", use_container_width=True, disabled=is_active):
                go_to_case(cid, c)
                st.rerun()

        if current_step not in ("ready", "running", "error"):
            st.divider()
            st.markdown("**Review Sections**")
            for i, sec_name in enumerate(SECTION_NAMES):
                checked = st.session_state.get(f"sec_{case_id}_{i}", False)
                icon = "✅" if checked else "⬜"
                st.markdown(f"{icon} §{i+1} {sec_name}")

            reviewed_count = sum(
                1 for i in range(8) if st.session_state.get(f"sec_{case_id}_{i}", False)
            )
            st.divider()
            st.progress(reviewed_count / 8)
            st.caption(f"{reviewed_count} of 8 sections confirmed")
            st.markdown("⏰ **SLA:** 46 hours remaining")

    # ── Top bar ──
    col_back, col_title, col_meta = st.columns([1, 5, 3])
    with col_back:
        st.button("← Queue", on_click=go_to_queue)
    with col_title:
        st.markdown(f"### {case_id} — {pii(name)}")
    with col_meta:
        if risk_rating != "pending":
            risk_cls = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high"}.get(risk_rating, "")
            st.markdown(
                f'<span class="risk-badge {risk_cls}">{risk_rating.upper()}</span> '
                f'<span class="data-class data-class-confidential">CONFIDENTIAL</span>',
                unsafe_allow_html=True,
            )
        if current_step == "complete":
            st.success("COMPLETED")
        elif current_step == "human_review":
            st.warning("AWAITING REVIEW")
        elif current_step == "awaiting_info":
            st.warning("AWAITING INFORMATION")

    # ── Ready state ──
    if current_step == "ready":
        st.info("Click **Start Review** to begin the automated compliance review workflow.")
        if st.button("Start Review", type="primary", use_container_width=True):
            review_info["current_step"] = "running"
            review_info["session_memory"] = SessionMemory(case_id)
            st.session_state["case_reviews"][case_id] = review_info
            st.rerun()
        _render_case_preview(case_data)
        return

    if current_step == "error":
        st.error(f"Review failed: {review_info.get('error_detail', 'Unknown error')}")
        st.warning("Check your LLM configuration. Try switching LLM_PROVIDER to 'openai' in .env if Ark is unreachable.")
        if st.button("Retry"):
            review_info["current_step"] = "ready"
            st.session_state["case_reviews"][case_id] = review_info
            st.rerun()
        return

    # ═════════════════════════════════════════════════════════════
    # DOCUMENT-FLOW: Sections §1 – §9
    # ═════════════════════════════════════════════════════════════

    # Prior conditions callout
    recs = cv.get("recommendations", [])
    if recs:
        st.markdown(
            '<div class="prior-callout">'
            '<div class="prior-callout-title">⚠ Conditions from Prior Review</div>'
            '<ul>' + "".join(f"<li>{r}</li>" for r in recs[:5]) + '</ul>'
            '</div>',
            unsafe_allow_html=True,
        )

    _render_s1_customer(case_id, case_data, cv)
    _render_s2_documents(case_id, case_data, cv)
    _render_s3_screening(case_id, cv)
    _render_s4_risk(case_id, cv)
    _render_s5_sow(case_id, case_data, cv)
    _render_s6_edd(case_id, cv)
    _render_s7_ai(case_id, cv)
    _render_s8_findings(case_id, cv)
    _render_s9_decision(case_id, case_data, cv, review_info, current_step)

    with st.expander("Full Audit Trail"):
        _render_audit_timeline(cv, review_info)
    with st.expander("Enterprise Audit Log"):
        _render_enterprise_audit(case_id)


# ═══════════════════════════════════════════════════════════════════
# Section Helpers
# ═══════════════════════════════════════════════════════════════════
def _section_header(num, title, severity="default", badge_text="", badge_type="info"):
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["default"])
    badge_html = ""
    if badge_text:
        style = BADGE_STYLES.get(badge_type, BADGE_STYLES["info"])
        badge_html = f' <span class="sec-badge" style="{style}">{badge_text}</span>'
    st.markdown(
        f'<div class="severity-bar" style="background:{color};"></div>'
        f'<div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">'
        f'<span style="font-size:11px; color:#b0b5bd; font-weight:700; font-family:monospace;">§{num}</span>'
        f'<span style="font-size:15px; font-weight:600; flex:1;">{title}</span>'
        f'{badge_html}</div>',
        unsafe_allow_html=True,
    )


def _section_reviewed_checkbox(case_id, idx):
    key = f"sec_{case_id}_{idx}"
    st.checkbox("Mark as reviewed", key=key, value=st.session_state.get(key, False))


# ───────────────────────────────────────────────────────────────
# §1 Customer Profile
# ───────────────────────────────────────────────────────────────
def _render_s1_customer(case_id, case_data, cv):
    with st.container(border=True):
        _section_header(1, "Customer Profile", "info", "Existing Customer", "info")

        customer = case_data["customer"]
        ctype = customer.get("type", "unknown")

        if ctype == "individual":
            rows = [
                ("Full Name", f"<strong>{pii(customer.get('full_name', 'N/A'))}</strong>"),
                ("Date of Birth", pii(customer.get("date_of_birth", "N/A"))),
                ("Nationality", customer.get("nationality", "N/A")),
                ("Occupation", customer.get("occupation", "N/A")),
                ("Employer", customer.get("employer", "N/A")),
            ]
            income = customer.get("annual_income")
            if income:
                rows.append(("Annual Income", f"{customer.get('income_currency', '')} {income:,.0f}"))
            decl = case_data.get("declarations", {})
            if decl.get("pep_status"):
                rows.append((
                    "PEP Declaration",
                    '<span style="color:#d4760a; font-weight:600;">Yes — '
                    + str(decl.get("pep_details", "declared")) + '</span>',
                ))
        else:
            rows = [
                ("Company", f"<strong>{pii(customer.get('company_name', 'N/A'))}</strong>"),
                ("Reg. Number", customer.get("registration_number", "N/A")),
                ("Jurisdiction", customer.get("country_of_incorporation", customer.get("jurisdiction", "N/A"))),
                ("Industry", customer.get("business_type", customer.get("industry", "N/A"))),
            ]
            revenue = customer.get("annual_revenue")
            if revenue:
                rows.append(("Annual Revenue", f"{customer.get('revenue_currency', 'USD')} {revenue:,.0f}"))

        grid = '<div class="dgrid">' + "".join(
            f'<div class="dl">{l}</div><div class="dv">{v}</div>' for l, v in rows
        ) + '</div>'
        st.markdown(grid, unsafe_allow_html=True)

        with st.expander("🧠 Review History (Long-term Memory)", expanded=False):
            st.markdown(
                '<div class="mem-card">'
                '<div class="mem-entry"><span class="mem-tag mem-tag-high">HIGH</span>'
                '<strong>2023-11</strong> — Score 72 · Approve w/ conditions · Enhanced monitoring, PEP re-screen</div>'
                '<div class="mem-entry"><span class="mem-tag mem-tag-med">MED</span>'
                '<strong>2022-11</strong> — Score 55 · Approve · PEP cooling-off assessed</div>'
                '<div class="mem-entry"><span class="mem-tag mem-tag-low">LOW</span>'
                '<strong>2019-06</strong> — Score 28 · Approve · Standard CDD, onboarding</div>'
                '<div style="font-size:11px; color:#8f959e; margin-top:8px; padding-top:8px; border-top:1px dashed #e8e9eb;">'
                'Trajectory: LOW → MEDIUM → HIGH · TM alerts (12m): 2 · SAR: No</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        with st.expander("📊 Behavioral Profile (Bank Internal)", expanded=False):
            st.markdown(
                '<div class="mem-card"><div class="dgrid" style="font-size:12px;">'
                '<div class="dl">Avg Monthly Inflow</div><div class="dv">$185,000</div>'
                '<div class="dl">Avg Monthly Outflow</div><div class="dv">$142,000</div>'
                '<div class="dl">Max Single TX</div><div class="dv">$320,000 (2024-08, wire to SG)</div>'
                '<div class="dl">Cross-border Ratio</div><div class="dv" style="color:#d4760a; font-weight:500;">68%</div>'
                '<div class="dl">Counterparties</div><div class="dv">Singapore, Mainland China, BVI</div>'
                '<div class="dl">Cash Deposits</div><div class="dv">Rare (2x in 12m)</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

        _section_reviewed_checkbox(case_id, 0)


# ───────────────────────────────────────────────────────────────
# §2 Document Verification
# ───────────────────────────────────────────────────────────────
def _render_s2_documents(case_id, case_data, cv):
    intake_status = cv.get("intake_status", "complete")
    has_issues = intake_status == "conditional" or cv.get("critical_missing")
    severity = "critical" if has_issues else "clear"
    badge = ("Issue Found", "alert") if has_issues else ("All Valid", "pass")

    with st.container(border=True):
        _section_header(2, "Document Verification", severity, badge[0], badge[1])

        docs = case_data.get("identification_documents", [])
        if docs:
            rows_html = ""
            for doc in docs:
                doc_type = doc.get("type", "unknown").replace("_", " ").title()
                verified = doc.get("verified", doc.get("provided", False))
                note = doc.get("note", doc.get("document_number", "N/A"))
                cls = "doc-ok" if verified else "doc-expired"
                text = "Valid" if verified else "Issue"
                rows_html += f'<tr><td>{doc_type}</td><td class="{cls}">{text}</td><td>{note}</td></tr>'
            st.markdown(
                f'<table class="doc-table"><thead><tr><th>Document</th><th>Status</th><th>Notes</th></tr></thead>'
                f'<tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True,
            )

        critical = cv.get("critical_missing", [])
        non_critical = cv.get("non_critical_missing", [])
        if critical:
            st.markdown(
                f'<div class="callout callout-red"><strong>⚠ Critical:</strong> Missing: {", ".join(critical)}</div>',
                unsafe_allow_html=True,
            )
        if non_critical:
            st.markdown(
                f'<div class="callout callout-orange"><strong>Conditional Intake:</strong> Missing non-critical: {", ".join(non_critical)}. Risk score +1.</div>',
                unsafe_allow_html=True,
            )

        _section_reviewed_checkbox(case_id, 1)


# ───────────────────────────────────────────────────────────────
# §3 Screening Results
# ───────────────────────────────────────────────────────────────
def _render_s3_screening(case_id, cv):
    sanctions = cv.get("sanctions_result", "N/A")
    pep_res = cv.get("pep_result", "N/A")
    adverse = cv.get("adverse_media_result", "N/A")

    has_match = any(r in ("potential_match", "confirmed_match") for r in [sanctions, pep_res, adverse])
    severity = "warning" if has_match else "clear"
    badge_text = "PEP Match" if pep_res in ("potential_match", "confirmed_match") else "All Clear"
    badge_type = "warn" if has_match else "pass"

    with st.container(border=True):
        _section_header(3, "Screening Results", severity, badge_text, badge_type)

        def _card(label, result):
            is_match = result in ("potential_match", "confirmed_match")
            card_cls = "alert" if is_match else "clear"
            res_cls = "match" if is_match else "ok"
            icon = "⚠" if is_match else "✓"
            display = result.upper().replace("_", " ") if result != "N/A" else "N/A"
            return (
                f'<div class="scr-card {card_cls}">'
                f'<div class="scr-label">{label}</div>'
                f'<div class="scr-result {res_cls}">{icon} {display}</div></div>'
            )

        st.markdown(
            f'<div class="scr-row">{_card("Sanctions", sanctions)}{_card("PEP Status", pep_res)}{_card("Adverse Media", adverse)}</div>',
            unsafe_allow_html=True,
        )

        if pep_res in ("potential_match", "confirmed_match"):
            st.markdown(
                '<div class="callout callout-orange">'
                '<strong>PEP Assessment:</strong> EDD required per PEP Policy. '
                'Mitigating factors should be evaluated in §6 Enhanced Due Diligence.</div>',
                unsafe_allow_html=True,
            )

        _section_reviewed_checkbox(case_id, 2)


# ───────────────────────────────────────────────────────────────
# §4 Risk Assessment
# ───────────────────────────────────────────────────────────────
def _render_s4_risk(case_id, cv):
    risk_rating = cv.get("risk_rating", "N/A")
    risk_total = cv.get("risk_total", 0)
    dd_level = cv.get("due_diligence_level", "standard")
    max_score = 15 + (1 if cv.get("intake_status") == "conditional" else 0)

    severity = {"low": "clear", "medium": "warning", "high": "critical"}.get(risk_rating, "default")
    badge_type = {"low": "pass", "medium": "warn", "high": "alert"}.get(risk_rating, "info")

    with st.container(border=True):
        _section_header(4, "Risk Assessment", severity, f"{risk_rating.upper()} — {risk_total}/{max_score}", badge_type)

        col_score, col_bar = st.columns([1, 3])
        with col_score:
            color = {"low": "#28a745", "medium": "#ffc107", "high": "#dc3545"}.get(risk_rating, "#6c757d")
            st.markdown(
                f'<div style="text-align:center;">'
                f'<div class="risk-score-big" style="color:{color};">{risk_total}</div>'
                f'<div style="font-size:11px; font-weight:600; color:{color};">{risk_rating.upper()} RISK</div>'
                f'<div style="font-size:11px; color:#8f959e;">DD: {dd_level.upper()}</div></div>',
                unsafe_allow_html=True,
            )
        with col_bar:
            st.markdown(
                '<div style="margin-top:8px;">'
                '<div class="risk-bar-bg"></div>'
                '<div style="display:flex; justify-content:space-between; font-size:10px; color:#8f959e; margin-top:4px;">'
                f'<span>0 — Low</span><span>Medium</span><span>High</span><span>{max_score}</span></div></div>',
                unsafe_allow_html=True,
            )

        risk_scores = cv.get("risk_scores", {})
        if risk_scores:
            factor_labels = {
                "customer_type": "Customer Type",
                "geography": "Geography",
                "product_service": "Product/Service",
                "transaction_pattern": "Transaction",
                "source_of_funds": "Source of Funds",
            }
            factor_cols = st.columns(min(len(risk_scores), 5))
            for i, (key, data) in enumerate(risk_scores.items()):
                score = data.get("score", 0) if isinstance(data, dict) else data
                label = factor_labels.get(key, key.replace("_", " ").title())
                sc_color = "#28a745" if score == 1 else ("#ffc107" if score == 2 else "#dc3545")
                with factor_cols[i % len(factor_cols)]:
                    st.markdown(
                        f'<div class="risk-factor">'
                        f'<div class="risk-factor-score" style="color:{sc_color};">{score}/3</div>'
                        f'<div class="risk-factor-label">{label}</div></div>',
                        unsafe_allow_html=True,
                    )

        _section_reviewed_checkbox(case_id, 3)


# ───────────────────────────────────────────────────────────────
# §5 Source of Wealth
# ───────────────────────────────────────────────────────────────
def _render_s5_sow(case_id, case_data, cv):
    with st.container(border=True):
        _section_header(5, "Source of Wealth / Funds", "info", "Under Review", "info")

        sof = case_data.get("source_of_funds", {})
        customer = case_data["customer"]
        rows = []
        if sof.get("primary"):
            rows.append(("Declared Source", sof["primary"].replace("_", " ").title()))
        if sof.get("details"):
            rows.append(("Details", sof["details"]))
        income = customer.get("annual_income")
        if income:
            rows.append(("Annual Income", f"{customer.get('income_currency', '')} {income:,.0f}"))

        if rows:
            grid = '<div class="dgrid">' + "".join(
                f'<div class="dl">{l}</div><div class="dv">{v}</div>' for l, v in rows
            ) + '</div>'
            st.markdown(grid, unsafe_allow_html=True)

        edd_findings = cv.get("edd_findings", {})
        if edd_findings.get("source_of_wealth"):
            st.markdown(
                f'<div class="callout callout-blue"><strong>Assessment:</strong> {edd_findings["source_of_wealth"]}</div>',
                unsafe_allow_html=True,
            )

        _section_reviewed_checkbox(case_id, 4)


# ───────────────────────────────────────────────────────────────
# §6 Enhanced Due Diligence
# ───────────────────────────────────────────────────────────────
def _render_s6_edd(case_id, cv):
    dd_level = cv.get("due_diligence_level", "standard")
    is_edd = dd_level == "enhanced"
    severity = "warning" if is_edd else "info"
    badge = ("Required", "warn") if is_edd else ("Standard DD", "info")

    with st.container(border=True):
        _section_header(6, "Enhanced Due Diligence", severity, badge[0], badge[1])

        if not is_edd:
            st.info("Standard due diligence — EDD not triggered for this case.")
        else:
            edd = cv.get("edd_findings", {})
            rows = []
            if edd.get("source_of_wealth"):
                rows.append(("Source of Wealth", edd["source_of_wealth"]))
            if edd.get("source_of_funds"):
                rows.append(("Source of Funds", edd["source_of_funds"]))
            if edd.get("risk_mitigants"):
                rows.append(("Risk Mitigants", "; ".join(edd["risk_mitigants"])))
            if edd.get("risk_amplifiers"):
                rows.append(("Risk Amplifiers", '<span style="color:#d83931;">' + "; ".join(edd["risk_amplifiers"]) + '</span>'))

            if rows:
                grid = '<div class="dgrid">' + "".join(
                    f'<div class="dl">{l}</div><div class="dv">{v}</div>' for l, v in rows
                ) + '</div>'
                st.markdown(grid, unsafe_allow_html=True)

        _section_reviewed_checkbox(case_id, 5)


# ───────────────────────────────────────────────────────────────
# §7 AI Analysis & Cited Sources
# ───────────────────────────────────────────────────────────────
def _render_s7_ai(case_id, cv):
    with st.container(border=True):
        _section_header(7, "AI Analysis & Cited Sources", "clear")

        agent_decision = cv.get("decision", "N/A")
        ai_confidence = cv.get("ai_confidence")
        rationale = cv.get("decision_rationale", "")

        pct = int(ai_confidence * 100) if ai_confidence is not None else 0
        conf_html = ""
        if ai_confidence is not None:
            conf_html = (
                f'<span style="font-size:11px; color:#8f959e; margin-left:auto;">'
                f'Confidence: {pct}% '
                f'<span class="conf-sm"><span class="conf-sm-fill" style="width:{pct}%"></span></span></span>'
            )

        st.markdown(
            f'<div class="ai-rec">'
            f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">'
            f'<span style="font-size:12px; font-weight:600; color:#3370ff;">🤖 AI Recommendation</span>'
            f'{conf_html}</div>'
            f'<div class="ai-rec-decision">{agent_decision.upper().replace("_", " ")}</div>'
            f'<div style="font-size:13px; color:#646a73; line-height:1.6;">{rationale}</div></div>',
            unsafe_allow_html=True,
        )

        sources_cited = cv.get("sources_cited", [])
        if sources_cited:
            st.markdown("**Sources Cited**")
            kb = get_knowledge_base()
            ref_counter = 1
            for src_group in sources_cited:
                for src in src_group.get("sources", []):
                    chunks = kb.query(src, n_results=1)
                    title = chunks[0].get("source", src) if chunks else src
                    version = chunks[0].get("version", "") if chunks else ""
                    section = chunks[0].get("section", "") if chunks else ""
                    ver_str = f" v{version}" if version else ""
                    sec_str = f" — {section}" if section else ""
                    st.markdown(
                        f'<span class="src-ref">[{ref_counter}]</span> {title}{ver_str}{sec_str}',
                        unsafe_allow_html=True,
                    )
                    ref_counter += 1

        _section_reviewed_checkbox(case_id, 6)


# ───────────────────────────────────────────────────────────────
# §8 Findings Summary (Short-term Memory)
# ───────────────────────────────────────────────────────────────
def _render_s8_findings(case_id, cv):
    findings = cv.get("findings", [])
    n = len(findings)
    severity = "warning" if n > 2 else ("info" if n > 0 else "clear")

    with st.container(border=True):
        _section_header(8, "Review Findings Summary", severity, f"Session Memory · {n}", "info")

        st.caption("All issues accumulated during this review session, sorted by severity.")

        if findings:
            for f in findings:
                text = str(f)
                if any(w in text.lower() for w in ["expired", "missing", "critical", "blocked"]):
                    cls = "finding-critical"
                elif any(w in text.lower() for w in ["pep", "monitor", "bvi", "warning", "elevated"]):
                    cls = "finding-warning"
                else:
                    cls = "finding-info"
                st.markdown(f'<div class="finding {cls}">{text}</div>', unsafe_allow_html=True)
        else:
            st.info("No findings recorded.")

        _section_reviewed_checkbox(case_id, 7)


# ───────────────────────────────────────────────────────────────
# §9 Human Decision
# ───────────────────────────────────────────────────────────────
def _render_s9_decision(case_id, case_data, cv, review_info, current_step):
    with st.container(border=True):
        st.markdown(
            '<div class="severity-bar" style="background:#3370ff;"></div>'
            '<div style="font-size:15px; font-weight:600; margin-bottom:12px;">§9 Human Decision</div>',
            unsafe_allow_html=True,
        )

        all_reviewed = all(
            st.session_state.get(f"sec_{case_id}_{i}", False) for i in range(8)
        )

        if current_step == "awaiting_info":
            _render_awaiting_info(case_id, cv, review_info)
            return

        if current_step == "complete":
            _render_completed_decision(cv, review_info, case_id)
            return

        # Lock state
        if not all_reviewed:
            st.markdown("### 🔒 Review all sections to unlock")
            st.caption("Confirm each section above by checking **Mark as reviewed**.")
            for i, sec_name in enumerate(SECTION_NAMES):
                checked = st.session_state.get(f"sec_{case_id}_{i}", False)
                icon = "✅" if checked else "⬜"
                st.markdown(f"{icon} {sec_name}")
            return

        # Unlocked: Decision form
        agent_decision = cv.get("decision", "N/A")
        ai_confidence = cv.get("ai_confidence")
        risk_rating = cv.get("risk_rating", "low")

        conf_text = f" ({int(ai_confidence * 100)}%)" if ai_confidence else ""
        st.markdown(
            f"All sections reviewed. AI recommends: **{agent_decision.upper().replace('_', ' ')}**{conf_text}."
        )

        # Conditions editor
        st.markdown("**Review Conditions**")
        recs = cv.get("recommendations", [])
        for i, rec in enumerate(recs):
            st.checkbox(f"{rec} *(inherited)*", value=True, disabled=True, key=f"cond_i_{case_id}_{i}")
        st.text_input("+ Add condition...", key=f"new_cond_{case_id}", placeholder="Type a new condition and press Enter")

        # Four-eyes notice
        if current_user.role == Role.ANALYST and risk_rating == "high":
            st.markdown(
                '<div class="four-eyes">'
                '<strong>⚠ Four-Eyes Required:</strong> As Analyst L1, your approval of this HIGH-risk case '
                'requires Senior Analyst co-sign. The case will be routed for co-sign after your decision.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("**Your Decision:**")
        decision_options = ["approve", "approve_with_conditions", "reject", "request_more_info", "escalate"]
        default_idx = decision_options.index(agent_decision) if agent_decision in decision_options else 0
        human_decision = st.selectbox(
            "Decision:", decision_options, index=default_idx, key=f"dec_{case_id}",
            format_func=lambda x: x.upper().replace("_", " "),
        )
        human_notes = st.text_area(
            "Reviewer notes (required):", height=100,
            placeholder="Document your reasoning...", key=f"notes_{case_id}",
        )

        if st.button("Submit Decision", type="primary", use_container_width=True, key=f"submit_{case_id}"):
            if not human_notes.strip():
                st.error("Review notes are required.")
            elif (human_decision in ("approve", "approve_with_conditions")
                  and not current_user.can_approve_risk_level(cv.get("risk_rating", "low"))):
                st.error(
                    f"Permission denied: {current_user.role.value} cannot approve "
                    f"{cv.get('risk_rating', 'unknown')}-risk cases. Please escalate."
                )
                get_audit_logger().log_case_action(
                    action=AuditAction.PERMISSION_DENIED,
                    case_id=case_id,
                    details={
                        "attempted_decision": human_decision,
                        "role": current_user.role.value,
                        "risk_level": cv.get("risk_rating"),
                    },
                    user=current_user,
                    risk_level=cv.get("risk_rating"),
                )
            else:
                try:
                    audit_logger = get_audit_logger()
                    is_override = human_decision != agent_decision
                    audit_logger.log_case_action(
                        action=AuditAction.CASE_OVERRIDE_AI if is_override else AuditAction.CASE_SUBMIT_DECISION,
                        case_id=case_id,
                        details={
                            "human_decision": human_decision,
                            "ai_decision": agent_decision,
                            "notes": human_notes,
                            "is_override": is_override,
                        },
                        risk_level=cv.get("risk_rating"),
                        ai_decision=agent_decision,
                        human_decision=human_decision,
                    )
                    if review_info.get("from_cache"):
                        state_snap = review_info["review_state"]
                        state_snap.values["human_decision"] = human_decision
                        state_snap.values["human_notes"] = human_notes
                        state_snap.values["review_status"] = "completed"
                        review_info["current_step"] = "complete"
                        st.session_state["case_reviews"][case_id] = review_info
                    else:
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
                        review_info["review_state"] = app.get_state(thread_config)
                        review_info["current_step"] = _step_from_pause(app, thread_config)
                        st.session_state["case_reviews"][case_id] = review_info
                except Exception as e:
                    st.error(f"Error finalizing review: {e}")
                    return
                st.rerun()

        _render_audit_preview(cv)


def _render_awaiting_info(case_id, cv, review_info):
    stage = cv.get("info_request_stage", "")
    round_no = cv.get("info_request_round", 1)
    st.warning(f"Information requested by **{stage}** (round {round_no})")
    for item in cv.get("info_requests", []):
        st.markdown(f"- {item}")

    st.caption("Paste supplemental information as a JSON patch.")
    patch_text = st.text_area(
        "Supplemental information (JSON):", height=160,
        placeholder='{"source_of_wealth": {"supporting_documents": ["audited_financials_2023"]}}',
        key=f"patch_{case_id}",
    )
    if st.button("Submit Information", type="primary", use_container_width=True, key=f"supply_{case_id}"):
        try:
            patch = json.loads(patch_text)
            if not isinstance(patch, dict) or not patch:
                raise ValueError("Must be a non-empty JSON object.")
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Invalid JSON: {e}")
            return
        try:
            if review_info.get("from_cache"):
                state_snap = review_info["review_state"]
                state_snap.values.update(patch)
                review_info["current_step"] = "human_review"
                st.session_state["case_reviews"][case_id] = review_info
            else:
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
            st.error(f"Error resuming: {e}")
            return
        st.rerun()


def _render_completed_decision(cv, review_info, case_id):
    decision_colors = {
        "approve": "#28a745", "reject": "#dc3545",
        "request_more_info": "#ffc107", "escalate": "#17a2b8",
        "approve_with_conditions": "#20c997",
    }
    final_snap = review_info.get("review_state")
    fv = final_snap.values if final_snap else {}
    human_dec = fv.get("human_decision", "N/A")
    human_notes = fv.get("human_notes", "")
    agreement = fv.get("ai_human_agreement")
    dec_color = decision_colors.get(human_dec, "#6c757d")

    st.markdown(
        f'<div style="background:linear-gradient(135deg,{dec_color}22,{dec_color}11); '
        f'border-left:4px solid {dec_color}; padding:12px; border-radius:6px;">'
        f'<div style="font-size:18px; font-weight:bold; color:{dec_color};">'
        f'{human_dec.upper().replace("_", " ")}</div></div>',
        unsafe_allow_html=True,
    )

    if agreement is not None:
        if agreement:
            st.success("AI and Human decisions **AGREE**")
        else:
            st.warning("AI and Human decisions **DIFFER** — override logged")

    if human_notes:
        st.markdown(f"**Reviewer Notes:** {human_notes}")

    st.divider()
    if st.button("Start New Review", key=f"new_{case_id}"):
        review_info["run"] = review_info.get("run", 1) + 1
        review_info["current_step"] = "ready"
        review_info["review_state"] = None
        review_info["step_results"] = []
        for i in range(8):
            st.session_state[f"sec_{case_id}_{i}"] = False
        st.session_state["case_reviews"][case_id] = review_info
        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# Audit Helpers
# ═══════════════════════════════════════════════════════════════════
def _render_audit_preview(cv):
    audit_trail = cv.get("audit_trail", [])
    if not audit_trail:
        return
    st.markdown("---")
    st.caption("AUDIT TRAIL PREVIEW")
    for entry in audit_trail[-6:]:
        ts = entry.get("timestamp", "")[:19].replace("T", " ") if entry.get("timestamp") else "—"
        step = entry.get("step", "")
        action = entry.get("action", "")
        st.markdown(
            f'<div class="audit-row">'
            f'<span class="audit-time">{ts}</span>'
            f'<span style="flex:1; font-size:11px;">{step}: {action}</span>'
            f'<span class="audit-actor">{step}_node</span></div>',
            unsafe_allow_html=True,
        )


def _render_audit_timeline(cv, review_info):
    audit_trail = cv.get("audit_trail", [])
    if not audit_trail:
        st.info("No audit entries yet.")
        return

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
            step_type, dot_color = "HUMAN", "#28a745"
        elif sources_used:
            step_type, dot_color = "AI + RAG", "#17a2b8"
        elif step in ai_steps:
            step_type, dot_color = "AI", "#007bff"
        else:
            step_type, dot_color = "SYSTEM", "#6c757d"

        details_display = (str(details)[:250] + "...") if len(str(details)) > 250 else details
        st.markdown(
            f'<div style="padding-left:24px; border-left:2px solid #dee0e6; margin-left:8px; padding-bottom:16px; position:relative;">'
            f'<div style="position:absolute; left:-7px; top:4px; width:12px; height:12px; border-radius:50%; background:{dot_color}; border:2px solid #fff;"></div>'
            f'<div style="font-size:11px; color:#999;">{ts_display} | {step_type} | Model: {model_version}</div>'
            f'<div style="font-weight:600; font-size:14px;">{step.replace("_", " ").title()}: {action.replace("_", " ").title()}</div>'
            f'<div style="font-size:13px; color:#555; margin-top:2px;">{details_display}</div></div>',
            unsafe_allow_html=True,
        )

    step_results = review_info.get("step_results", [])
    if step_results:
        st.markdown("### Detailed Step Outputs")
        for i, sr in enumerate(step_results):
            with st.expander(f"Step {i+1}: {sr['node'].replace('_', ' ').title()}"):
                output = sr["output"]
                if isinstance(output, dict):
                    for k, v in output.items():
                        label = k.replace("_", " ").title()
                        if isinstance(v, list):
                            st.markdown(f"**{label}:**")
                            for item in v:
                                st.markdown(f"- {item if not isinstance(item, dict) else item.get('details', str(item))}")
                        elif isinstance(v, dict):
                            st.markdown(f"**{label}:**")
                            for sk, sv in v.items():
                                st.markdown(f"  - {sk.replace('_', ' ').title()}: {sv}")
                        else:
                            st.markdown(f"**{label}:** {v}")
                else:
                    st.write(output)


def _render_enterprise_audit(case_id):
    audit_logger = get_audit_logger()
    all_entries = audit_logger.query_by_case(case_id, limit=200)
    overrides = audit_logger.query_overrides()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Actions", len(all_entries))
    with col2:
        denied = sum(1 for e in all_entries if e.get("action") == "permission_denied")
        st.metric("Permission Denied", denied)
    with col3:
        st.metric("AI Overrides (all)", len(overrides))

    if not all_entries:
        st.info("No audit entries yet.")
        return

    import pandas as pd
    rows = []
    for entry in all_entries[:20]:
        details = json.loads(entry["details"]) if entry.get("details") else {}
        rows.append({
            "Timestamp": entry.get("timestamp", "")[:19].replace("T", " "),
            "User": entry.get("username", ""),
            "Role": entry.get("role", ""),
            "Action": entry.get("action", "").replace("_", " ").title(),
            "Risk Level": (entry.get("risk_level") or "").upper(),
            "AI Decision": (entry.get("ai_decision") or "—").replace("_", " "),
            "Human Decision": (entry.get("human_decision") or "—").replace("_", " "),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# Case Preview (shown before workflow runs)
# ═══════════════════════════════════════════════════════════════════
def _render_case_preview(case_data):
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Customer Information")
        customer = case_data.get("customer", {})
        ctype = customer.get("type", "unknown")
        if ctype == "individual":
            fields = [
                ("Full Name", pii(customer.get("full_name", "N/A"))),
                ("Date of Birth", pii(customer.get("date_of_birth", "N/A"))),
                ("Nationality", customer.get("nationality", "N/A")),
                ("Occupation", customer.get("occupation", "N/A")),
            ]
        else:
            fields = [
                ("Company", pii(customer.get("company_name", "N/A"))),
                ("Registration", customer.get("registration_number", "N/A")),
                ("Jurisdiction", customer.get("country_of_incorporation", "N/A")),
            ]
        for label, value in fields:
            if value:
                st.markdown(f"**{label}:** {value}")

    with col_b:
        st.subheader("Documents Submitted")
        for doc in case_data.get("identification_documents", []):
            icon = "✅" if doc.get("verified") or doc.get("provided") else "❌"
            doc_type = doc.get("type", "unknown").replace("_", " ").title()
            st.markdown(f"{icon} {doc_type}")


# ═══════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════
if st.session_state["current_page"] == "queue":
    render_queue_page()
elif st.session_state["current_page"] == "detail":
    render_detail_page()
