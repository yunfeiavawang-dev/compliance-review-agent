"""Helpers for the request-info loop: supplying information and detecting where
the graph is paused. Kept out of the UI so they can be tested without Streamlit."""

from __future__ import annotations

import copy
from typing import Any


def merge_submission(base: dict, patch: dict) -> dict:
    """Merge a supplemental-information patch into a submission (returns a copy).

    - dicts are merged recursively
    - lists are appended to; a dict item that has a ``type`` replaces the
      existing item of the same ``type`` (so a re-uploaded document supersedes
      the earlier one instead of duplicating it)
    - everything else is overwritten
    """
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            merged[key] = merge_submission(current, value)
        elif isinstance(value, list) and isinstance(current, list):
            merged[key] = _merge_lists(current, value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _merge_lists(current: list, additions: list) -> list:
    result = list(current)
    for item in additions:
        if isinstance(item, dict) and item.get("type") is not None:
            idx = next(
                (i for i, existing in enumerate(result)
                 if isinstance(existing, dict) and existing.get("type") == item["type"]),
                None,
            )
            if idx is not None:
                result[idx] = copy.deepcopy(item)
                continue
        if item not in result:
            result.append(copy.deepcopy(item))
    return result


def pause_point(app: Any, thread_config: dict) -> str | None:
    """Name of the node the graph is currently paused before, or None if the
    run has finished. Callers use this instead of assuming where it stopped."""
    snapshot = app.get_state(thread_config)
    pending = tuple(snapshot.next or ())
    for name in ("await_info", "human_review"):
        if name in pending:
            return name
    return None


def supply_information(app: Any, thread_config: dict, patch: dict) -> None:
    """Write supplemental information into a case that is waiting at
    ``await_info``. The caller then resumes with ``app.stream(None, thread_config)``;
    the graph continues at the node that requested the information."""
    if pause_point(app, thread_config) != "await_info":
        raise ValueError("Case is not waiting for supplemental information.")
    values = app.get_state(thread_config).values
    submission = merge_submission(values["submission"], patch)
    app.update_state(thread_config, {"submission": submission}, as_node="request_info")
