"""Three-dimension rubric evaluation for KYC agent output quality.

Dimensions:
1. Efficiency — token consumption, latency, cost
2. Quality — decision accuracy, consistency across runs
3. Experience — clarity, no jargon, source citations, actionable next steps
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Scoring definitions
# ---------------------------------------------------------------------------

@dataclass
class EfficiencyScore:
    """Tokens and timing per case."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    node_latencies: dict[str, float] = field(default_factory=dict)

    @property
    def cost_usd(self) -> float:
        """Doubao-seed-evolving pricing (per 1K tokens): input ¥0.004, output ¥0.004."""
        rmb = (self.total_input_tokens * 0.004 + self.total_output_tokens * 0.004) / 1000
        return rmb / 7.2  # approximate CNY→USD

    def summary(self) -> dict:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "elapsed_s": round(self.elapsed_seconds, 1),
            "cost_usd": round(self.cost_usd, 4),
            "node_latencies": {k: round(v, 1) for k, v in self.node_latencies.items()},
        }


@dataclass
class QualityScore:
    """Decision correctness and consistency."""
    risk_rating_match: bool = False
    dd_level_match: bool = False
    decision_acceptable: bool = False
    decision_actual: str = ""
    decision_expected: str = ""
    consistency_runs: int = 0
    consistency_agree: int = 0

    @property
    def accuracy_pct(self) -> float:
        checks = [self.risk_rating_match, self.dd_level_match, self.decision_acceptable]
        return sum(checks) / len(checks) * 100

    @property
    def consistency_pct(self) -> Optional[float]:
        if self.consistency_runs < 2:
            return None
        return self.consistency_agree / self.consistency_runs * 100

    def summary(self) -> dict:
        d = {
            "risk_rating_match": self.risk_rating_match,
            "dd_level_match": self.dd_level_match,
            "decision_acceptable": self.decision_acceptable,
            "decision_actual": self.decision_actual,
            "decision_expected": self.decision_expected,
            "accuracy_pct": self.accuracy_pct,
            "risk_actual": getattr(self, "risk_actual", ""),
            "risk_expected": getattr(self, "risk_expected", ""),
            "risk_total": getattr(self, "risk_total", "N/A"),
        }
        if self.consistency_pct is not None:
            d["consistency_pct"] = self.consistency_pct
        return d


JARGON_PATTERNS = [
    r"\bCDD\b", r"\bEDD\b", r"\bAML\b", r"\bCFT\b", r"\bFATF\b",
    r"\bPEP\b", r"\bSAR\b", r"\bSTR\b", r"\bUBO\b", r"\bSoF\b",
    r"\bSoW\b", r"\bKYC\b", r"\bTM\b", r"\bRBA\b",
]


@dataclass
class ExperienceScore:
    """Output readability and usefulness for a compliance analyst."""
    clarity: int = 0          # 1-5: structure, logical flow
    no_jargon: int = 0        # 1-5: unexplained acronyms penalized
    has_references: bool = False
    has_next_steps: bool = False
    jargon_found: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        ref_pts = 1.0 if self.has_references else 0.0
        step_pts = 1.0 if self.has_next_steps else 0.0
        return (self.clarity + self.no_jargon) / 2 + ref_pts + step_pts

    @property
    def max_score(self) -> float:
        return 7.0  # 5 (avg clarity+jargon) + 1 (ref) + 1 (steps)

    def summary(self) -> dict:
        return {
            "clarity": self.clarity,
            "no_jargon": self.no_jargon,
            "has_references": self.has_references,
            "has_next_steps": self.has_next_steps,
            "jargon_found": self.jargon_found,
            "total": round(self.total, 1),
            "max": self.max_score,
        }


@dataclass
class CaseRubricResult:
    case_id: str
    customer_name: str
    efficiency: EfficiencyScore = field(default_factory=EfficiencyScore)
    quality: QualityScore = field(default_factory=QualityScore)
    experience: ExperienceScore = field(default_factory=ExperienceScore)

    def summary(self) -> dict:
        return {
            "case_id": self.case_id,
            "customer_name": self.customer_name,
            "efficiency": self.efficiency.summary(),
            "quality": self.quality.summary(),
            "experience": self.experience.summary(),
        }


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

DECISION_EQUIVALENCE = {
    "approve": {"approve"},
    "approve_with_conditions": {"approve_with_conditions", "approve"},
    "reject": {"reject"},
    "request_more_info": {"request_more_info", "request_more_information"},
    "escalate": {"escalate", "escalate_to_compliance_committee"},
    "escalate_to_compliance_committee": {"escalate", "escalate_to_compliance_committee"},
}


def _decision_acceptable(actual: str, expected: str) -> bool:
    """Check if the actual decision is acceptable given the expected one."""
    actual = actual.lower().strip()
    expected = expected.lower().strip()
    if actual == expected:
        return True
    acceptable = DECISION_EQUIVALENCE.get(expected, {expected})
    return actual in acceptable


def score_quality(final_state: dict, expected: dict) -> QualityScore:
    actual_risk = final_state.get("risk_rating", "")
    actual_dd = final_state.get("due_diligence_level", "")
    actual_decision = final_state.get("decision", "")
    expected_risk = expected.get("risk_rating", "")
    expected_dd = expected.get("due_diligence_level", "")
    expected_decision = expected.get("decision", "")

    qs = QualityScore(
        risk_rating_match=(actual_risk == expected_risk),
        dd_level_match=(actual_dd == expected_dd),
        decision_acceptable=_decision_acceptable(actual_decision, expected_decision),
        decision_actual=actual_decision,
        decision_expected=expected_decision,
    )
    qs.risk_actual = actual_risk
    qs.risk_expected = expected_risk
    qs.dd_actual = actual_dd
    qs.dd_expected = expected_dd
    qs.risk_total = final_state.get("risk_total", "N/A")
    return qs


def _count_jargon(text: str) -> list[str]:
    found = set()
    for pattern in JARGON_PATTERNS:
        if re.search(pattern, text):
            found.add(pattern.strip(r"\b"))
    return sorted(found)


def score_experience(final_state: dict) -> ExperienceScore:
    """Score the agent's output for analyst-friendliness."""
    findings = final_state.get("findings", [])
    rationale = final_state.get("decision_rationale", "") or ""
    all_text = "\n".join(str(f) for f in findings) + "\n" + rationale

    # Jargon check
    jargon = _count_jargon(all_text)
    if len(jargon) == 0:
        jargon_score = 5
    elif len(jargon) <= 2:
        jargon_score = 4
    elif len(jargon) <= 5:
        jargon_score = 3
    elif len(jargon) <= 8:
        jargon_score = 2
    else:
        jargon_score = 1

    # Clarity: simple heuristic — structured findings, reasonable length
    n_findings = len([f for f in findings if isinstance(f, str) and len(f) > 10])
    if n_findings >= 3 and len(rationale) > 100:
        clarity = 4
    elif n_findings >= 2:
        clarity = 3
    else:
        clarity = 2

    # Bump clarity if rationale is well-structured (has sections/bullets)
    if rationale and ("\n-" in rationale or "\n•" in rationale or "\n1." in rationale):
        clarity = min(5, clarity + 1)

    # References
    sources = final_state.get("sources_cited", [])
    has_refs = len(sources) >= 2

    # Next steps / recommendations
    recs = final_state.get("recommendations", [])
    has_steps = len(recs) >= 1 or "condition" in rationale.lower() or "monitor" in rationale.lower()

    return ExperienceScore(
        clarity=clarity,
        no_jargon=jargon_score,
        has_references=has_refs,
        has_next_steps=has_steps,
        jargon_found=jargon,
    )
