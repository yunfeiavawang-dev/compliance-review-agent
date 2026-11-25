"""Debug a single case to inspect raw LLM output from ReAct loop."""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src.config import load_config
from src.graph.workflow import create_app
from src.graph.resume import pause_point
from src.graph.nodes import _parse_json_response


config = load_config()
app = create_app(config)

case_file = Path("data/customers/clean_case.json")
with open(case_file) as f:
    case_data = json.load(f)

case_id = case_data["case_id"]
thread_config = {"configurable": {"thread_id": f"debug-{case_id}"}}

initial_state = {
    "case_id": case_id,
    "review_id": f"REV-{case_id}",
    "customer_id": f"CUST-{case_id}",
    "submission": case_data,
    "review_status": "pending",
    "info_request_round": 0,
    "audit_trail": [],
}

print("Running workflow until human_review pause...")
for event in app.stream(initial_state, thread_config, stream_mode="values"):
    step = event.get("current_step", "?")

paused_at = pause_point(app, thread_config)
print(f"Paused at: {paused_at}")

snapshot = app.get_state(thread_config)
vals = snapshot.values

print(f"\n=== RISK ASSESSMENT ===")
print(f"risk_total: {vals.get('risk_total')}")
print(f"risk_rating: {vals.get('risk_rating')}")
print(f"risk_scores: {json.dumps(vals.get('risk_scores', {}), indent=2)}")

print(f"\n=== DECISION FROM STANDARD REVIEW ===")
print(f"decision: {vals.get('decision')}")
print(f"ai_confidence: {vals.get('ai_confidence')}")
print(f"decision_rationale: {vals.get('decision_rationale', '')[:300]}")
print(f"recommendations: {vals.get('recommendations')}")

print(f"\n=== AUDIT TRAIL (review steps) ===")
for entry in vals.get("audit_trail", []):
    if entry.get("step") in ("standard_review", "risk_assessment"):
        print(f"  [{entry['step']}] {entry['action']}: {entry.get('details', '')[:200]}")

print(f"\n=== FINDINGS ===")
for f in vals.get("findings", []):
    print(f"  - {str(f)[:200]}")
