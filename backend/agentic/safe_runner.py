from __future__ import annotations

import time
from typing import Any, Callable


def run_stage_with_retries(
    stage_name: str,
    stage_func: Callable[[], dict[str, Any]],
    validator_func: Callable[[dict[str, Any]], dict[str, Any]],
    fallback_func: Callable[[], dict[str, Any]],
    max_retries: int = 2,
) -> dict[str, Any]:
    issues: list[str] = []
    attempts_allowed = max(0, int(max_retries)) + 1

    for attempt in range(1, attempts_allowed + 1):
        try:
            raw = stage_func()
            validated = validator_func(raw)

            return {
                "data": validated,
                "stage": stage_name,
                "attempts": attempt,
                "used_fallback": False,
                "issues": issues,
            }
        except Exception as exc:
            issues.append(f"Attempt {attempt} failed: {type(exc).__name__}: {exc}")
            if attempt < attempts_allowed:
                time.sleep(1)

    fallback = fallback_func()
    issues.append("Fallback output used after retry budget was exhausted.")

    return {
        "data": fallback,
        "stage": stage_name,
        "attempts": attempts_allowed,
        "used_fallback": True,
        "issues": issues,
    }


__all__ = ["run_stage_with_retries"]
