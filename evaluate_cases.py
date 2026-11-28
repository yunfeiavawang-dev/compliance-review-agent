"""Run all 7 KYC cases with rubric evaluation: efficiency, quality, experience.

Outputs:
  - evaluation_report.json  (machine-readable, per-case + aggregate)
  - evaluation_report.md    (human-readable scorecard)
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from src.config import load_config
from src.graph.workflow import create_app
from src.graph.resume import pause_point, merge_submission
from src.models import set_token_callback
from src.evaluation.rubric import (
    CaseRubricResult,
    EfficiencyScore,
    score_quality,
    score_experience,
)

# ---------------------------------------------------------------------------
# Token tracking
# ---------------------------------------------------------------------------

_current_input_tokens = 0
_current_output_tokens = 0


def _token_tracker(input_t: int, output_t: int):
    global _current_input_tokens, _current_output_tokens
    _current_input_tokens += input_t
    _current_output_tokens += output_t


# ---------------------------------------------------------------------------
# Supplements (same as run_all_cases.py)
# ---------------------------------------------------------------------------

SUPPLEMENTS = {
    "KYC-2024-002": {
        "identification_documents": [
            {
                "type": "board_resolution",
                "provided": True,
                "verified": True,
                "note": "Board resolution dated 2024-08-18 authorizing account opening, signed by Li Jian Ming",
            },
            {
                "type": "business_license",
                "provided": True,
                "verified": True,
                "note": "ACRA BizFile+ foreign company registration (branch office)",
            },
        ],
        "beneficial_ownership": {
            "declared_owners": [
                {
                    "name": "Li Jian Ming",
                    "ownership_percentage": 60,
                    "nationality": "Malaysian",
                    "identification_provided": True,
                },
                {
                    "name": "Pacific Ventures Holdings Ltd",
                    "ownership_percentage": 40,
                    "country_of_incorporation": "Cayman Islands",
                    "identification_provided": False,
                    "note": "Nominee structure — ultimate beneficial owner not disclosed",
                },
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Case runner with instrumentation
# ---------------------------------------------------------------------------

def run_case_instrumented(app, case_data: dict, case_file: str) -> dict:
    """Run one case and return final state + timing."""
    global _current_input_tokens, _current_output_tokens
    _current_input_tokens = 0
    _current_output_tokens = 0

    case_id = case_data["case_id"]
    thread_config = {"configurable": {"thread_id": case_id}}
    customer = case_data.get("customer", {})
    name = customer.get("full_name", customer.get("company_name", "?"))

    initial_state = {
        "case_id": case_id,
        "review_id": f"REV-{case_id}",
        "customer_id": f"CUST-{case_id}",
        "submission": case_data,
        "review_status": "pending",
        "info_request_round": 0,
        "audit_trail": [],
    }

    print(f"\n{'='*70}")
    print(f"CASE: {case_id} — {name} ({case_file})")
    print(f"{'='*70}")

    node_times = {}
    t_start = time.time()
    last_step = None
    step_start = time.time()

    # Stream through the graph
    for event in app.stream(initial_state, thread_config, stream_mode="values"):
        step = event.get("current_step", "?")
        if step != last_step and last_step:
            node_times[last_step] = time.time() - step_start
            step_start = time.time()
        last_step = step
        print(f"  [{step}] done")

    if last_step:
        node_times[last_step] = time.time() - step_start

    # Handle pauses (human_review / await_info)
    paused_at = pause_point(app, thread_config)
    supplement_used = False
    max_resumes = 8
    resume_count = 0
    while paused_at and resume_count < max_resumes:
        resume_count += 1
        if paused_at == "human_review":
            snapshot = app.get_state(thread_config)
            vals = snapshot.values
            ai_decision = vals.get("decision", "approve")
            print(f"  Human review: accepting AI recommendation ({ai_decision})")
            app.update_state(
                thread_config,
                {
                    "human_decision": ai_decision,
                    "human_notes": "Auto-eval: accepted AI recommendation",
                    "human_review_required": False,
                },
                as_node="human_review",
            )
            step_start = time.time()
            for event in app.stream(None, thread_config, stream_mode="values"):
                step = event.get("current_step", "?")
                if step != last_step and last_step and last_step not in node_times:
                    node_times[last_step] = time.time() - step_start
                    step_start = time.time()
                last_step = step
                print(f"  [{step}] done")
            if last_step and last_step not in node_times:
                node_times[last_step] = time.time() - step_start
            paused_at = pause_point(app, thread_config)

        elif paused_at == "await_info":
            snapshot = app.get_state(thread_config)
            vals = snapshot.values
            round_num = vals.get("info_request_round", 0)
            print(f"  Awaiting info (round {round_num})")
            patch = SUPPLEMENTS.get(case_id) if not supplement_used else None
            if patch:
                supplement_used = True
                merged = merge_submission(vals.get("submission", {}), patch)
                app.update_state(
                    thread_config,
                    {"submission": merged},
                    as_node="request_info",
                )
            else:
                app.update_state(
                    thread_config,
                    {"submission": vals.get("submission", {})},
                    as_node="request_info",
                )
            step_start = time.time()
            for event in app.stream(None, thread_config, stream_mode="values"):
                step = event.get("current_step", "?")
                if step != last_step and last_step and last_step not in node_times:
                    node_times[last_step] = time.time() - step_start
                    step_start = time.time()
                last_step = step
                print(f"  [{step}] done")
            if last_step and last_step not in node_times:
                node_times[last_step] = time.time() - step_start
            paused_at = pause_point(app, thread_config)
        else:
            break

    elapsed = time.time() - t_start

    # Final state
    final = app.get_state(thread_config).values

    return {
        "case_id": case_id,
        "customer_name": name,
        "case_file": case_file,
        "final_state": final,
        "expected": case_data.get("expected_outcome", {}),
        "elapsed_seconds": elapsed,
        "node_latencies": node_times,
        "input_tokens": _current_input_tokens,
        "output_tokens": _current_output_tokens,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_markdown_report(results: list[CaseRubricResult], agg: dict) -> str:
    lines = []
    lines.append("# KYC Agent — Rubric Evaluation Report\n")
    lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**LLM**: {agg.get('llm', 'N/A')}")
    lines.append(f"**Cases**: {len(results)}\n")

    # Aggregate
    lines.append("## Aggregate Scores\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Accuracy (decision acceptable) | {agg['accuracy_pct']:.0f}% ({agg['correct']}/{agg['total']}) |")
    lines.append(f"| Risk Rating Match | {agg['risk_match']}/{agg['total']} |")
    lines.append(f"| DD Level Match | {agg['dd_match']}/{agg['total']} |")
    lines.append(f"| Total Tokens | {agg['total_tokens']:,} |")
    lines.append(f"| Total Cost (USD) | ${agg['total_cost']:.4f} |")
    lines.append(f"| Avg Latency per Case | {agg['avg_latency']:.1f}s |")
    lines.append(f"| Avg Experience Score | {agg['avg_experience']:.1f}/{results[0].experience.max_score if results else 7} |")
    lines.append("")

    # Per-case table
    lines.append("## Per-Case Results\n")
    lines.append("| Case | Customer | Decision | Expected | Risk | DD | Exp Score | Tokens | Latency |")
    lines.append("|------|----------|----------|----------|------|----|-----------|--------|---------|")
    for r in results:
        q = r.quality
        risk_ok = "Y" if q.risk_rating_match else "N"
        dd_ok = "Y" if q.dd_level_match else "N"
        dec_ok = "Y" if q.decision_acceptable else "**N**"
        lines.append(
            f"| {r.case_id} | {r.customer_name[:18]} | "
            f"{q.decision_actual} {dec_ok} | {q.decision_expected} | "
            f"{risk_ok} | {dd_ok} | "
            f"{r.experience.total:.1f} | {r.efficiency.total_tokens:,} | "
            f"{r.efficiency.elapsed_seconds:.0f}s |"
        )
    lines.append("")

    # Experience details
    lines.append("## Experience Detail\n")
    for r in results:
        e = r.experience
        lines.append(f"### {r.case_id} — {r.customer_name}")
        lines.append(f"- Clarity: {e.clarity}/5")
        lines.append(f"- Jargon: {e.no_jargon}/5 (found: {', '.join(e.jargon_found) if e.jargon_found else 'none'})")
        lines.append(f"- References: {'Yes' if e.has_references else 'No'}")
        lines.append(f"- Next Steps: {'Yes' if e.has_next_steps else 'No'}")
        lines.append(f"- **Total: {e.total:.1f}/{e.max_score}**\n")

    # Node latency breakdown
    lines.append("## Node Latency Breakdown\n")
    all_nodes = set()
    for r in results:
        all_nodes.update(r.efficiency.node_latencies.keys())
    nodes_sorted = sorted(all_nodes)
    header = "| Case | " + " | ".join(nodes_sorted) + " | Total |"
    sep = "|------| " + " | ".join(["---"] * len(nodes_sorted)) + " | --- |"
    lines.append(header)
    lines.append(sep)
    for r in results:
        vals = " | ".join(
            f"{r.efficiency.node_latencies.get(n, 0):.0f}s"
            for n in nodes_sorted
        )
        lines.append(f"| {r.case_id} | {vals} | {r.efficiency.elapsed_seconds:.0f}s |")
    lines.append("")

    return "\n".join(lines)


def main():
    set_token_callback(_token_tracker)

    print("Initializing...")
    config = load_config()
    app = create_app(config)
    llm_label = f"{config.llm.provider}/{config.llm.model}"
    print(f"LLM: {llm_label}")
    print(f"Embedding: {config.embedding.provider}/{config.embedding.model_name}")

    data_dir = Path("data/customers")
    order = [
        "clean_case.json",
        "corporate_clean.json",
        "expired_documents.json",
        "medium_risk_individual.json",
        "pep_declared.json",
        "edge_incomplete.json",
        "edge_high_risk.json",
    ]

    rubric_results: list[CaseRubricResult] = []

    for case_file in order:
        path = data_dir / case_file
        if not path.exists():
            print(f"  SKIP: {case_file} not found")
            continue
        with open(path) as fh:
            case_data = json.load(fh)
        try:
            run = run_case_instrumented(app, case_data, case_file)
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Score
        eff = EfficiencyScore(
            total_input_tokens=run["input_tokens"],
            total_output_tokens=run["output_tokens"],
            total_tokens=run["input_tokens"] + run["output_tokens"],
            elapsed_seconds=run["elapsed_seconds"],
            node_latencies=run["node_latencies"],
        )
        qual = score_quality(run["final_state"], run["expected"])
        exp = score_experience(run["final_state"])

        cr = CaseRubricResult(
            case_id=run["case_id"],
            customer_name=run["customer_name"],
            efficiency=eff,
            quality=qual,
            experience=exp,
        )
        rubric_results.append(cr)

        # Print inline
        print(f"\n  Rubric ➜ accuracy={qual.accuracy_pct:.0f}%  experience={exp.total:.1f}/{exp.max_score}  tokens={eff.total_tokens:,}  latency={eff.elapsed_seconds:.0f}s")

    # Aggregate
    total = len(rubric_results)
    correct = sum(1 for r in rubric_results if r.quality.decision_acceptable)
    risk_match = sum(1 for r in rubric_results if r.quality.risk_rating_match)
    dd_match = sum(1 for r in rubric_results if r.quality.dd_level_match)
    total_tokens = sum(r.efficiency.total_tokens for r in rubric_results)
    total_cost = sum(r.efficiency.cost_usd for r in rubric_results)
    avg_latency = sum(r.efficiency.elapsed_seconds for r in rubric_results) / max(total, 1)
    avg_exp = sum(r.experience.total for r in rubric_results) / max(total, 1)

    agg = {
        "llm": llm_label,
        "total": total,
        "correct": correct,
        "accuracy_pct": correct / total * 100 if total else 0,
        "risk_match": risk_match,
        "dd_match": dd_match,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "avg_latency": avg_latency,
        "avg_experience": avg_exp,
    }

    # JSON report
    json_report = {
        "summary": agg,
        "cases": [r.summary() for r in rubric_results],
    }
    json_path = Path("evaluation_report.json")
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report → {json_path}")

    # Markdown report
    md_report = generate_markdown_report(rubric_results, agg)
    md_path = Path("evaluation_report.md")
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"Markdown report → {md_path}")

    # Print summary
    print(f"\n{'='*70}")
    print("EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Accuracy: {correct}/{total} ({agg['accuracy_pct']:.0f}%)")
    print(f"Risk Match: {risk_match}/{total}")
    print(f"DD Match: {dd_match}/{total}")
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Avg Latency: {avg_latency:.1f}s")
    print(f"Avg Experience: {avg_exp:.1f}/7.0")


if __name__ == "__main__":
    main()
