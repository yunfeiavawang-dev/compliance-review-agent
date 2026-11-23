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
    route_after_review,
    route_after_human_review,
)


def build_review_graph(config: AppConfig) -> StateGraph:
    """Build the KYC compliance review LangGraph workflow.

    Graph structure:
        intake → [screening | request_info]
        screening → [risk_assessment | request_info]
        risk_assessment → [standard_review | enhanced_due_diligence]
        standard_review → [human_review | request_info]
        enhanced_due_diligence → [human_review | request_info]
        human_review → [decision | request_info]
        decision → END
        request_info → END
    """
    runner = NodeRunner(config)

    graph = StateGraph(ReviewState)

    graph.add_node("intake", runner.intake_node)
    graph.add_node("identity_screening", runner.screening_node)
    graph.add_node("risk_assessment", runner.risk_assessment_node)
    graph.add_node("standard_review", runner.standard_review_node)
    graph.add_node("enhanced_due_diligence", runner.edd_node)
    graph.add_node("human_review", runner.human_review_node)
    graph.add_node("decision", runner.decision_node)
    graph.add_node("request_info", runner.request_info_node)

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
        "enhanced_due_diligence": "enhanced_due_diligence",
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
    graph.add_edge("request_info", END)

    return graph


def create_app(config: AppConfig):
    """Create a compiled LangGraph app with checkpointing."""
    graph = build_review_graph(config)
    checkpointer = MemorySaver()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],
    )
