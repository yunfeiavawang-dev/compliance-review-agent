"""Generate final metrics report from evaluation_report.json.

Step 5: Token consumption, cost, latency, accuracy, and scaled projections.
Run AFTER evaluate_cases.py completes.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.evaluation.cost_projection import project_costs, format_projection_table, VOLCENGINE_INFRA


def main():
    report_path = Path("evaluation_report.json")
    if not report_path.exists():
        print("ERROR: evaluation_report.json not found. Run evaluate_cases.py first.")
        sys.exit(1)

    with open(report_path) as f:
        report = json.load(f)

    summary = report["summary"]
    cases = report["cases"]
    n = len(cases)

    # Compute averages
    avg_input = sum(c["efficiency"]["input_tokens"] for c in cases) // max(n, 1)
    avg_output = sum(c["efficiency"]["output_tokens"] for c in cases) // max(n, 1)
    avg_total = avg_input + avg_output
    avg_latency = sum(c["efficiency"]["elapsed_s"] for c in cases) / max(n, 1)

    # Cost projections
    projections = project_costs(avg_input, avg_output, [7, 500, 1000, 5000])

    # Build Markdown report
    lines = []
    lines.append("# KYC Agent — Metrics Report\n")
    lines.append(f"**LLM**: {summary['llm']}")
    lines.append(f"**Evaluation Date**: {report.get('date', 'N/A')}")
    lines.append(f"**Cases Evaluated**: {n}\n")

    # 1. Token consumption
    lines.append("## 1. Token Consumption\n")
    lines.append("| Case | Customer | Input Tokens | Output Tokens | Total |")
    lines.append("|------|----------|-------------|--------------|-------|")
    for c in cases:
        e = c["efficiency"]
        lines.append(
            f"| {c['case_id']} | {c['customer_name'][:18]} | "
            f"{e['input_tokens']:,} | {e['output_tokens']:,} | {e['total_tokens']:,} |"
        )
    lines.append(f"| **Average** | | **{avg_input:,}** | **{avg_output:,}** | **{avg_total:,}** |")
    lines.append(f"| **Total (7 cases)** | | **{sum(c['efficiency']['input_tokens'] for c in cases):,}** | "
                 f"**{sum(c['efficiency']['output_tokens'] for c in cases):,}** | "
                 f"**{summary['total_tokens']:,}** |")
    lines.append("")

    # 2. Latency
    lines.append("## 2. Latency\n")
    lines.append("### End-to-End per Case\n")
    lines.append("| Case | Customer | Elapsed (s) |")
    lines.append("|------|----------|-------------|")
    for c in cases:
        lines.append(f"| {c['case_id']} | {c['customer_name'][:18]} | {c['efficiency']['elapsed_s']:.1f}s |")
    lines.append(f"| **Average** | | **{avg_latency:.1f}s** |")
    lines.append("")

    lines.append("### Per-Node Latency (seconds)\n")
    all_nodes = set()
    for c in cases:
        all_nodes.update(c["efficiency"]["node_latencies"].keys())
    nodes_sorted = sorted(all_nodes)
    if nodes_sorted:
        header = "| Case | " + " | ".join(nodes_sorted) + " |"
        sep = "|------| " + " | ".join(["---"] * len(nodes_sorted)) + " |"
        lines.append(header)
        lines.append(sep)
        for c in cases:
            vals = " | ".join(
                f"{c['efficiency']['node_latencies'].get(n, 0):.0f}"
                for n in nodes_sorted
            )
            lines.append(f"| {c['case_id']} | {vals} |")
        # Averages
        avg_node = {}
        for node in nodes_sorted:
            vals = [c["efficiency"]["node_latencies"].get(node, 0) for c in cases if node in c["efficiency"]["node_latencies"]]
            avg_node[node] = sum(vals) / max(len(vals), 1)
        avg_vals = " | ".join(f"{avg_node[n]:.0f}" for n in nodes_sorted)
        lines.append(f"| **Avg** | {avg_vals} |")
    lines.append("")

    # 3. Cost
    lines.append("## 3. Cost Analysis\n")
    lines.append("### Demo Run (7 cases, actual consumption)\n")
    demo = projections[0]  # volume=7
    lines.append(f"- Input tokens: {sum(c['efficiency']['input_tokens'] for c in cases):,}")
    lines.append(f"- Output tokens: {sum(c['efficiency']['output_tokens'] for c in cases):,}")
    lines.append(f"- LLM cost: ¥{demo.llm_cost_cny:.4f} (${demo.llm_cost_usd:.4f})")
    lines.append(f"- **Total demo cost: ${demo.llm_cost_usd:.4f}** (LLM only, no infra)\n")

    lines.append(format_projection_table(projections[1:]))
    lines.append("")

    # 4. Accuracy
    lines.append("## 4. Accuracy\n")
    lines.append("| Case | Customer | Decision (Actual) | Decision (Expected) | Match | Risk Match | DD Match |")
    lines.append("|------|----------|-------------------|---------------------|-------|------------|----------|")
    for c in cases:
        q = c["quality"]
        dec_ok = "Y" if q["decision_acceptable"] else "**N**"
        risk_ok = "Y" if q["risk_rating_match"] else "**N**"
        dd_ok = "Y" if q["dd_level_match"] else "**N**"
        lines.append(
            f"| {c['case_id']} | {c['customer_name'][:18]} | "
            f"{q['decision_actual']} | {q['decision_expected']} | "
            f"{dec_ok} | {risk_ok} | {dd_ok} |"
        )
    lines.append("")
    lines.append(f"**Decision Accuracy**: {summary['correct']}/{summary['total']} ({summary['accuracy_pct']:.0f}%)")
    lines.append(f"**Risk Rating Match**: {summary['risk_match']}/{summary['total']}")
    lines.append(f"**DD Level Match**: {summary['dd_match']}/{summary['total']}")
    lines.append("")

    # 5. Experience scores
    lines.append("## 5. Experience Scores\n")
    lines.append("| Case | Clarity | Jargon | References | Next Steps | Total |")
    lines.append("|------|---------|--------|------------|------------|-------|")
    for c in cases:
        e = c["experience"]
        lines.append(
            f"| {c['case_id']} | {e['clarity']}/5 | {e['no_jargon']}/5 | "
            f"{'Y' if e['has_references'] else 'N'} | "
            f"{'Y' if e['has_next_steps'] else 'N'} | "
            f"{e['total']}/{e['max']} |"
        )
    lines.append(f"| **Average** | | | | | **{summary['avg_experience']:.1f}/{cases[0]['experience']['max'] if cases else 7}** |")
    lines.append("")

    md = "\n".join(lines)
    out_path = Path("metrics_report.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"Metrics report → {out_path}")

    # Also save enhanced JSON
    enhanced = {
        **report,
        "cost_projections": [p.summary() for p in projections],
        "per_case_averages": {
            "avg_input_tokens": avg_input,
            "avg_output_tokens": avg_output,
            "avg_total_tokens": avg_total,
            "avg_latency_s": round(avg_latency, 1),
        },
    }
    json_path = Path("metrics_report.json")
    with open(json_path, "w") as f:
        json.dump(enhanced, f, indent=2, ensure_ascii=False)
    print(f"Enhanced JSON → {json_path}")


if __name__ == "__main__":
    main()
