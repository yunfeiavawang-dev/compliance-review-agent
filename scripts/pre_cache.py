#!/usr/bin/env python3
"""Pre-run all case workflows and cache results for instant demo loading.

Usage:
    cd compliance-review-agent
    python3 scripts/pre_cache.py          # run all cases
    python3 scripts/pre_cache.py KYC-2024-001  # run one case
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.graph.workflow import create_app
from src.graph.state import ReviewState
from src.graph.resume import pause_point
from src.cache import save_case_cache

CASES_DIR = Path(__file__).resolve().parent.parent / "data" / "customers"
TENANT_ID = "pacific_rim_fg"


def _step_from_pause(app, thread_config) -> str:
    paused = pause_point(app, thread_config)
    if paused == "await_info":
        return "awaiting_info"
    if paused == "human_review":
        return "human_review"
    return "complete"


def run_case(app, case_path: Path, index: int, total: int) -> bool:
    with open(case_path) as f:
        case_data = json.load(f)
    case_id = case_data["case_id"]
    print(f"[{index}/{total}] Running {case_id} ({case_path.name})...", flush=True)

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
        tenant_id=TENANT_ID,
        data_classification="confidential",
    )

    thread_id = f"cache-{case_id}-{int(time.time())}"
    thread_config = {"configurable": {"thread_id": thread_id}}

    start = time.time()
    step_results = []
    try:
        for event in app.stream(initial_state, thread_config):
            for node_name, node_output in event.items():
                elapsed = time.time() - start
                print(f"  [{elapsed:5.1f}s] {node_name}", flush=True)
                step_results.append({"node": node_name, "output": node_output})
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    state_snap = app.get_state(thread_config)
    current_step = _step_from_pause(app, thread_config)

    save_case_cache(case_id, step_results, dict(state_snap.values), current_step)

    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s — cached as {current_step}")
    return True


def main():
    config = load_config()
    app = create_app(config)

    case_files = sorted(CASES_DIR.glob("*.json"))
    if not case_files:
        print("No case files found in", CASES_DIR)
        return

    target_id = sys.argv[1] if len(sys.argv) > 1 else None
    if target_id:
        case_files = [f for f in case_files if target_id in f.stem or target_id in json.loads(f.read_text()).get("case_id", "")]
        if not case_files:
            print(f"No case matching '{target_id}'")
            return

    total = len(case_files)
    print(f"Pre-caching {total} case(s)...\n")

    ok = 0
    for i, path in enumerate(case_files, 1):
        if run_case(app, path, i, total):
            ok += 1
        print()

    print(f"Results: {ok}/{total} cached successfully")


if __name__ == "__main__":
    main()
