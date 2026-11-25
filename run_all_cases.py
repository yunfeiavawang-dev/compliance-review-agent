"""Run all 7 test cases through the LangGraph workflow and compare with expected outcomes."""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.config import load_config
from src.graph.workflow import create_app
from src.graph.resume import pause_point, supply_information, merge_submission


# Supplemental documents to supply when a case is waiting at await_info.
# Key: case_id, Value: patch dict to merge into the submission.
# Only the first await_info round for a case uses this; subsequent rounds
# supply nothing (simulating the customer not responding further).
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


def run_case(app, case_data: dict, case_file: str) -> dict:
    case_id = case_data["case_id"]
    thread_config = {"configurable": {"thread_id": case_id}}

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
    print(f"CASE: {case_id} ({case_file})")
    customer = case_data.get("customer", {})
    name = customer.get("full_name", customer.get("company_name", "?"))
    print(f"Customer: {name} ({customer.get('type', '?')})")
    print(f"{'='*70}")

    # Run until first interrupt
    print("  Running workflow...")
    last_state = None
    for event in app.stream(initial_state, thread_config, stream_mode="values"):
        step = event.get("current_step", "?")
        last_state = event

    # Check where we paused
    paused_at = pause_point(app, thread_config)
    print(f"  Paused at: {paused_at}")

    supplement_used = False
    max_resumes = 8
    resume_count = 0
    while paused_at and resume_count < max_resumes:
        resume_count += 1
        if paused_at == "human_review":
            snapshot = app.get_state(thread_config)
            vals = snapshot.values
            ai_decision = vals.get("decision", "approve")
            print(f"  AI recommends: {ai_decision} (confidence: {vals.get('ai_confidence', 'N/A')})")
            print(f"  Simulating human accepts AI recommendation...")

            app.update_state(
                thread_config,
                {
                    "human_decision": ai_decision,
                    "human_notes": "Auto-test: accepted AI recommendation",
                    "human_review_required": False,
                },
                as_node="human_review",
            )

            for event in app.stream(None, thread_config, stream_mode="values"):
                last_state = event

            paused_at = pause_point(app, thread_config)
            if paused_at:
                print(f"  Paused again at: {paused_at}")

        elif paused_at == "await_info":
            snapshot = app.get_state(thread_config)
            vals = snapshot.values
            round_num = vals.get("info_request_round", 0)
            print(f"  Awaiting info (round {round_num})")

            patch = SUPPLEMENTS.get(case_id) if not supplement_used else None
            if patch:
                supplement_used = True
                print(f"  Supplying supplemental documents: {list(patch.keys())}")
                merged = merge_submission(vals.get("submission", {}), patch)
                app.update_state(
                    thread_config,
                    {"submission": merged},
                    as_node="request_info",
                )
            else:
                print(f"  No supplement — advancing empty")
                app.update_state(
                    thread_config,
                    {"submission": vals.get("submission", {})},
                    as_node="request_info",
                )

            for event in app.stream(None, thread_config, stream_mode="values"):
                last_state = event
            paused_at = pause_point(app, thread_config)
            if paused_at:
                print(f"  Paused again at: {paused_at}")
        else:
            print(f"  Unknown pause point: {paused_at}, breaking")
            break

    # Get final state
    final_snapshot = app.get_state(thread_config)
    final = final_snapshot.values

    result = {
        "case_id": case_id,
        "customer_name": name,
        "actual_risk_rating": final.get("risk_rating", "N/A"),
        "actual_decision": final.get("decision", "N/A"),
        "actual_human_decision": final.get("human_decision", "N/A"),
        "actual_confidence": final.get("ai_confidence", "N/A"),
        "actual_dd_level": final.get("due_diligence_level", "N/A"),
        "intake_status": final.get("intake_status", "N/A"),
        "risk_total": final.get("risk_total", "N/A"),
        "review_status": final.get("review_status", "N/A"),
        "info_request_round": final.get("info_request_round", 0),
        "error": final.get("error"),
    }

    expected = case_data.get("expected_outcome", {})
    result["expected_risk_rating"] = expected.get("risk_rating", "N/A")
    result["expected_decision"] = expected.get("decision", "N/A")
    result["expected_dd_level"] = expected.get("due_diligence_level", "N/A")

    # Compare
    risk_match = result["actual_risk_rating"] == result["expected_risk_rating"]
    dd_match = result["actual_dd_level"] == result["expected_dd_level"]

    print(f"\n  --- Results ---")
    print(f"  Risk Rating:  actual={result['actual_risk_rating']}  expected={result['expected_risk_rating']}  {'MATCH' if risk_match else 'MISMATCH'}")
    print(f"  DD Level:     actual={result['actual_dd_level']}  expected={result['expected_dd_level']}  {'MATCH' if dd_match else 'MISMATCH'}")
    print(f"  AI Decision:  {result['actual_decision']}")
    print(f"  Human Decision: {result['actual_human_decision']}")
    print(f"  Confidence:   {result['actual_confidence']}")
    print(f"  Intake Status: {result['intake_status']}")
    print(f"  Risk Total:   {result['risk_total']}")
    if result["error"]:
        print(f"  ERROR: {result['error']}")

    return result


def main():
    print("Initializing...")
    config = load_config()
    app = create_app(config)

    data_dir = Path("data/customers")
    case_files = sorted(data_dir.glob("*.json"))

    # Run order: easy → hard
    order = [
        "clean_case.json",
        "corporate_clean.json",
        "expired_documents.json",
        "medium_risk_individual.json",
        "pep_declared.json",
        "edge_incomplete.json",
        "edge_high_risk.json",
    ]

    ordered_files = []
    for name in order:
        p = data_dir / name
        if p.exists():
            ordered_files.append(p)
    for f in case_files:
        if f not in ordered_files:
            ordered_files.append(f)

    results = []
    for case_file in ordered_files:
        with open(case_file) as fh:
            case_data = json.load(fh)
        try:
            result = run_case(app, case_data, case_file.name)
            results.append(result)
        except Exception as e:
            print(f"\n  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "case_id": case_data.get("case_id", "?"),
                "error": str(e),
            })

    # Summary
    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"{'Case ID':<16} {'Risk Match':<12} {'DD Match':<12} {'Decision':<24} {'Expected':<24} {'Error'}")
    print(f"{'-'*16} {'-'*12} {'-'*12} {'-'*24} {'-'*24} {'-'*20}")
    for r in results:
        if "actual_risk_rating" not in r:
            print(f"{r.get('case_id','?'):<16} {'ERROR':<12} {'ERROR':<12} {'N/A':<24} {'N/A':<24} {r.get('error','')[:40]}")
            continue
        risk_ok = "YES" if r["actual_risk_rating"] == r["expected_risk_rating"] else "NO"
        dd_ok = "YES" if r["actual_dd_level"] == r["expected_dd_level"] else "NO"
        print(f"{r['case_id']:<16} {risk_ok:<12} {dd_ok:<12} {r['actual_decision']:<24} {r['expected_decision']:<24} {r.get('error') or ''}")

    # Save results
    output_path = Path("test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to {output_path}")


if __name__ == "__main__":
    main()
