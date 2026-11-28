"""Pre-computed workflow cache for instant demo loading."""

import json
import os
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def save_case_cache(case_id: str, step_results: list, state_values: dict, current_step: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "case_id": case_id,
        "current_step": current_step,
        "step_results": step_results,
        "state_values": state_values,
    }
    path = CACHE_DIR / f"{case_id}.json"
    path.write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False))


def load_case_cache(case_id: str):
    path = CACHE_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return data["step_results"], data["state_values"], data.get("current_step", "human_review")
    except (json.JSONDecodeError, KeyError):
        return None
