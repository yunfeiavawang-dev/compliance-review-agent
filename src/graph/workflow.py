"""LangGraph workflow assembly for the KYC compliance review."""

from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.config import AppConfig
from src.graph.state import ReviewState
from src.graph.nodes import NodeRunner
from src.graph.edges import (
    route_after_intake,
    route_after_screening,
    route_after_risk_assessment,
    route_after_edd_document_check,
    route_after_review,
    route_after_human_review,
    route_after_request_info,
    route_after_await_info,
)


def build_review_graph(config: AppConfig) -> StateGraph:
    """Build the KYC compliance review LangGraph workflow.

    Graph structure:
        intake → [screening | request_info]
        screening → [risk_assessment | request_info]
        risk_assessment → [standard_review | edd_document_check]
        edd_document_check → [enhanced_due_diligence | request_info]
        standard_review → [human_review | request_info]
        enhanced_due_diligence → [human_review | request_info]
        human_review → [decision | request_info]
        decision → END
        request_info → [await_info | human_review (round limit hit)]
        await_info → the node that requested the information (pause before it)

    The request_info loop is the only cycle. The graph pauses before
    ``await_info``; once the supplement is written into state it resumes at the
    node that asked, so earlier results are reused instead of recomputed.
    """
    runner = NodeRunner(config)

    graph = StateGraph(ReviewState)

    graph.add_node("intake", runner.intake_node)
    graph.add_node("identity_screening", runner.screening_node)
    graph.add_node("risk_assessment", runner.risk_assessment_node)
    graph.add_node("standard_review", runner.standard_review_node)
    graph.add_node("edd_document_check", runner.edd_document_check_node)
    graph.add_node("enhanced_due_diligence", runner.edd_node)
    graph.add_node("human_review", runner.human_review_node)
    graph.add_node("decision", runner.decision_node)
    graph.add_node("request_info", runner.request_info_node)
    graph.add_node("await_info", runner.await_info_node)

    graph.set_entry_point("intake")

    graph.add_conditional_edges("intake", route_after_intake, {
        "identity_screening": "identity_screening",
        "request_info": "request_info",
    })

    graph.add_conditional_edges("identity_screening", route_after_screening, {
        "risk_assessment": "risk_assessment",
        "request_info": "request_info",
    })

    graph.add_conditional_edges("risk_assessment", route_after_risk_assessment, {
        "standard_review": "standard_review",
        "edd_document_check": "edd_document_check",
    })

    graph.add_conditional_edges("edd_document_check", route_after_edd_document_check, {
        "enhanced_due_diligence": "enhanced_due_diligence",
        "request_info": "request_info",
    })

    graph.add_conditional_edges("standard_review", route_after_review, {
        "human_review": "human_review",
        "request_info": "request_info",
    })

    graph.add_conditional_edges("enhanced_due_diligence", route_after_review, {
        "human_review": "human_review",
        "request_info": "request_info",
    })

    graph.add_conditional_edges("human_review", route_after_human_review, {
        "decision": "decision",
        "request_info": "request_info",
    })

    graph.add_edge("decision", END)

    graph.add_conditional_edges("request_info", route_after_request_info, {
        "await_info": "await_info",
        "human_review": "human_review",
    })

    graph.add_conditional_edges("await_info", route_after_await_info, {
        "intake": "intake",
        "identity_screening": "identity_screening",
        "edd_document_check": "edd_document_check",
        "enhanced_due_diligence": "enhanced_due_diligence",
        "standard_review": "standard_review",
    })

    return graph


def create_app(config: AppConfig):
    """Create a compiled LangGraph app with checkpointing."""
    graph = build_review_graph(config)
    checkpointer = MemorySaver()
    return graph.compile(
        checkpointer=checkpointer,
        # human_review: waits for the compliance officer's decision.
        # await_info: waits for the customer's supplemental information.
        interrupt_before=["human_review", "await_info"],
    )
