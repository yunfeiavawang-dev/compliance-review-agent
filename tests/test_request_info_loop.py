"""Offline tests for the request-info loop (no LLM, no vector store).

NodeRunner's LLM-facing methods are replaced with canned answers; every other
piece — the rule-based intake check, the EDD document gate, request_info /
await_info, the conditional edges, the checkpointer and the interrupts — is the
real code.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import src.graph.workflow as workflow
from src.graph.nodes import NodeRunner
from src.graph.resume import merge_submission, pause_point, supply_information
from src.graph.state import ReviewState

DATA = Path(__file__).resolve().parent.parent / "data" / "customers"


def load_case(name: str) -> dict:
    return json.loads((DATA / name).read_text())


class StubKB:
    def get_policy_for_step(self, step, *a, **k):
        return []

    def format_sources_for_prompt(self, results, *a, **k):
        return ""

    def query(self, *a, **k):
        return []


class FakeRunner(NodeRunner):
    """Real nodes and edges; canned LLM answers; per-node call counters."""

    sanctions = "clear"
    pep = "clear"
    rating = "high"
    react_results: list = []
    calls: dict = {}

    def __init__(self, config=None):
        self.kb = StubKB()
        self.client = None
        self.model = "fake"

    def _call_llm(self, system, user):
        return {
            "sanctions_result": self.sanctions,
            "pep_result": self.pep,
            "screening_details": [],
            "scores": {},
            "total_score": 14 if self.rating == "high" else 8,
            "final_rating": self.rating,
            "due_diligence_level": "enhanced" if self.rating == "high" else "standard",
            "summary": "canned",
            "rationale": "canned",
        }

    def _react_loop(self, system_prompt, initial_user_msg, state, max_rounds=5, step_name="review"):
        FakeRunner.calls[step_name] = FakeRunner.calls.get(step_name, 0) + 1
        result = dict(FakeRunner.react_results.pop(0))
        return result, [{"round": 1, "action": "final_answer"}]


def _counted(name):
    original = getattr(NodeRunner, name)

    def wrapper(self, state):
        FakeRunner.calls[name] = FakeRunner.calls.get(name, 0) + 1
        return original(self, state)

    return wrapper


for _n in ("intake_node", "screening_node", "risk_assessment_node", "edd_document_check_node"):
    setattr(FakeRunner, _n, _counted(_n))


@pytest.fixture(autouse=True)
def reset_fake(monkeypatch):
    FakeRunner.sanctions = "clear"
    FakeRunner.pep = "clear"
    FakeRunner.rating = "high"
    FakeRunner.react_results = []
    FakeRunner.calls = {}
    monkeypatch.setattr(workflow, "NodeRunner", FakeRunner)


def start(case: dict, thread_id: str = "t1"):
    app = workflow.create_app(config=None)
    cfg = {"configurable": {"thread_id": thread_id}}
    initial = ReviewState(
        case_id=case["case_id"], submission=case,
        findings=[], recommendations=[], sources_cited=[], audit_trail=[], info_requests=[],
        current_step="intake", intake_status="complete", critical_missing=[],
        non_critical_missing=[], review_status="in_review",
    )
    visited = [n for ev in app.stream(initial, cfg) for n in ev if not n.startswith("__")]
    return app, cfg, visited


def resume(app, cfg):
    return [n for ev in app.stream(None, cfg) for n in ev if not n.startswith("__")]


def values(app, cfg):
    return app.get_state(cfg).values


SOW_EVIDENCE = {"source_of_wealth": {"supporting_documents": ["audited_financials_2023", "business_registry_extract"]}}


# --------------------------------------------------------------------------
def test_edd_gate_pauses_then_resumes_at_gate_not_intake():
    app, cfg, visited = start(load_case("edge_high_risk.json"))

    assert visited[-1] == "request_info"
    assert "enhanced_due_diligence" not in visited          # EDD effort not spent yet
    assert pause_point(app, cfg) == "await_info"
    v = values(app, cfg)
    assert v["info_request_stage"] == "edd_document_check"
    assert any("source of wealth" in r for r in v["info_requests"])

    FakeRunner.react_results = [{"recommendation": "escalate", "rationale": "r", "confidence": 0.7}]
    supply_information(app, cfg, SOW_EVIDENCE)
    visited2 = resume(app, cfg)

    assert visited2[:2] == ["await_info", "edd_document_check"]
    assert "intake" not in visited2 and "identity_screening" not in visited2 and "risk_assessment" not in visited2
    assert FakeRunner.calls["intake_node"] == 1
    assert FakeRunner.calls["screening_node"] == 1
    assert FakeRunner.calls["risk_assessment_node"] == 1
    assert FakeRunner.calls["edd_document_check_node"] == 2
    assert pause_point(app, cfg) == "human_review"

    app.update_state(cfg, {"human_decision": "escalate", "human_notes": "n"}, as_node="human_review")
    resume(app, cfg)
    final = values(app, cfg)
    assert final["review_status"] == "completed"

    actions = [a["action"] for a in final["audit_trail"]]
    assert "information_requested" in actions and "information_received" in actions
    assert actions.count("document_completeness_check") == 1        # history kept, not duplicated


def test_red_flag_is_never_blocked_by_the_document_gate():
    FakeRunner.sanctions = "potential_match"
    FakeRunner.react_results = [{"recommendation": "escalate", "rationale": "r", "confidence": 0.6,
                                 "additional_info_needed": ["x"]}]
    app, cfg, visited = start(load_case("edge_high_risk.json"))

    assert "request_info" not in visited
    assert visited[-1] == "enhanced_due_diligence"
    assert pause_point(app, cfg) == "human_review"
    v = values(app, cfg)
    assert v["edd_docs_bypassed"] is True
    assert v["edd_missing_docs"]                                     # gaps carried into EDD


def test_edd_asking_for_more_info_resumes_at_edd_only():
    FakeRunner.sanctions = "potential_match"                         # skip the gate, reach EDD
    FakeRunner.react_results = [
        {"recommendation": "request_more_info", "rationale": "need proof",
         "additional_info_needed": ["tax residency certificate"], "confidence": 0.5},
        {"recommendation": "escalate", "rationale": "r", "confidence": 0.7},
    ]
    app, cfg, _ = start(load_case("edge_high_risk.json"))

    assert pause_point(app, cfg) == "await_info"
    v = values(app, cfg)
    assert v["info_request_stage"] == "enhanced_due_diligence"
    assert "tax residency certificate" in v["info_requests"]

    supply_information(app, cfg, {"declarations": {"tax_residency_certificate": True}})
    visited = resume(app, cfg)

    assert visited[:2] == ["await_info", "enhanced_due_diligence"]
    assert FakeRunner.calls["edd"] == 2
    assert FakeRunner.calls["risk_assessment_node"] == 1
    assert pause_point(app, cfg) == "human_review"


def test_blocked_intake_resumes_at_intake():
    case = load_case("edge_incomplete.json")
    app, cfg, visited = start(case)

    assert visited == ["intake", "request_info"]
    assert values(app, cfg)["info_request_stage"] == "intake"
    assert pause_point(app, cfg) == "await_info"

    # Supply everything intake reported as critical so the re-check passes.
    critical = values(app, cfg)["critical_missing"]
    patch: dict = {"identification_documents": [], "declarations": {"declaration_signed": True}}
    for item in critical:
        if "board resolution" in item:
            patch["identification_documents"].append({"type": "board_resolution", "provided": True, "verified": True})
        if "certificate" in item:
            patch["identification_documents"].append({"type": "certificate_of_incorporation", "provided": True, "verified": True})
        if "beneficial" in item:
            patch["beneficial_ownership"] = {"declared_owners": [
                {"name": "A", "ownership_percentage": 60, "identification_provided": True}]}
    supply_information(app, cfg, patch)
    visited2 = resume(app, cfg)

    assert visited2[:2] == ["await_info", "intake"]
    assert FakeRunner.calls["intake_node"] == 2
    assert "identity_screening" in visited2                          # moved on once intake passed


def test_human_request_for_more_info_returns_to_the_review_node():
    FakeRunner.sanctions = "potential_match"
    FakeRunner.react_results = [
        {"recommendation": "escalate", "rationale": "r1", "confidence": 0.7},
        {"recommendation": "escalate", "rationale": "r2", "confidence": 0.7},
    ]
    app, cfg, _ = start(load_case("edge_high_risk.json"))
    assert pause_point(app, cfg) == "human_review"

    app.update_state(cfg, {"human_decision": "request_more_info", "human_notes": "need SoF bank letter"},
                     as_node="human_review")
    resume(app, cfg)
    v = values(app, cfg)
    assert pause_point(app, cfg) == "await_info"
    assert v["info_request_stage"] == "human_review"
    assert v["info_requests"] == ["need SoF bank letter"]

    supply_information(app, cfg, {"source_of_funds": {"bank_letter": "provided"}})
    visited = resume(app, cfg)
    assert visited[:2] == ["await_info", "enhanced_due_diligence"]  # analysed again with new info
    assert pause_point(app, cfg) == "human_review"
    assert values(app, cfg)["human_decision"] is None                # old decision cleared


def test_round_limit_hands_the_case_to_a_human():
    FakeRunner.rating = "medium"
    # standard review keeps asking for more info
    FakeRunner.react_results = [
        {"recommendation": "request_more_info", "rationale": f"ask {i}", "confidence": 0.5} for i in range(6)
    ]
    app, cfg, _ = start(load_case("clean_case.json"))

    rounds = 0
    while pause_point(app, cfg) == "await_info":
        rounds += 1
        assert rounds <= 3, "loop must stop after MAX_INFO_REQUEST_ROUNDS"
        supply_information(app, cfg, {"declarations": {"note": f"round {rounds}"}})
        resume(app, cfg)

    assert rounds == 3
    assert pause_point(app, cfg) == "human_review"
    v = values(app, cfg)
    assert v["info_round_exceeded"] is True
    assert v["decision"] == "escalate"


def test_audit_trail_is_append_only_across_a_resubmission():
    app, cfg, _ = start(load_case("edge_high_risk.json"))
    before = [a["timestamp"] for a in values(app, cfg)["audit_trail"]]
    FakeRunner.react_results = [{"recommendation": "escalate", "rationale": "r", "confidence": 0.7}]
    supply_information(app, cfg, SOW_EVIDENCE)
    resume(app, cfg)
    after = [a["timestamp"] for a in values(app, cfg)["audit_trail"]]
    assert after[: len(before)] == before                            # earlier entries untouched
    assert len(after) > len(before)


def test_merge_submission_semantics():
    base = {"a": {"x": 1}, "docs": [{"type": "passport", "provided": False}], "n": 1}
    patch = {"a": {"y": 2}, "docs": [{"type": "passport", "provided": True}, {"type": "utility_bill"}], "n": 2}
    original = copy.deepcopy(base)
    merged = merge_submission(base, patch)
    assert base == original                                          # input not mutated
    assert merged["a"] == {"x": 1, "y": 2}
    assert merged["docs"] == [{"type": "passport", "provided": True}, {"type": "utility_bill"}]
    assert merged["n"] == 2
