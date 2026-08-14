#!/usr/bin/env python3
"""Compact SubagentStart context and one-retry SubagentStop receipt check."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


CONTRACT = (
    "One bounded unit only. Preserve unrelated work. Write the complete report to "
    ".artifacts/agent-reports/<task>.md; return <=8 lines with verdict, evidence, "
    "verification, risk, next action, and report path."
)
REPORT_PATH = re.compile(r"\.artifacts/agent-reports/([A-Za-z0-9][A-Za-z0-9._-]*\.md)\b")


def event_name(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("hook_event_name") or payload.get("hookEventName")
    return value if isinstance(value, str) else None


def receipt(payload: dict[str, Any]) -> str:
    for key in ("last_assistant_message", "lastAssistantMessage", "response", "result"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def durable_report(message: str) -> bool:
    match = REPORT_PATH.search(message)
    if not match:
        return False
    base = (Path.cwd() / ".artifacts" / "agent-reports").resolve()
    candidate = base / match.group(1)
    report = candidate.resolve()
    try:
        report.relative_to(base)
    except ValueError:
        return False
    return not candidate.is_symlink() and report.is_file()


def decision(payload: Any) -> dict[str, Any] | None:
    event = event_name(payload)
    if event == "SubagentStart":
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": CONTRACT,
            }
        }
    if event != "SubagentStop" or not isinstance(payload, dict):
        return None
    if payload.get("stop_hook_active") is True:
        return None
    message = receipt(payload)
    lines = [line for line in message.splitlines() if line.strip()]
    if message and len(lines) <= 8 and durable_report(message):
        return None
    return {
        "decision": "block",
        "reason": (
            "Return a decision-complete receipt of at most 8 nonblank lines and include "
            "the .artifacts/agent-reports/<task>.md report path."
        ),
    }


def run_hook() -> int:
    try:
        payload = json.load(sys.stdin)
        result = decision(payload)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return 0
    if result is not None:
        print(json.dumps(result))
    return 0


def selftest() -> int:
    good = "PASS\nEvidence: x\nReport: .artifacts/agent-reports/unit.md"
    too_long = "\n".join(str(index) for index in range(9)) + "\n.artifacts/agent-reports/u.md"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        reports = root / ".artifacts" / "agent-reports"
        reports.mkdir(parents=True)
        (reports / "unit.md").write_text("complete\n", encoding="utf-8")
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            cases = [
                ("start injects", {"hook_event_name": "SubagentStart"}, "SubagentStart"),
                ("existing report passes", {"hook_event_name": "SubagentStop", "last_assistant_message": good}, None),
                ("missing path blocks", {"hook_event_name": "SubagentStop", "last_assistant_message": "PASS"}, "block"),
                ("missing file blocks", {"hook_event_name": "SubagentStop", "last_assistant_message": "PASS\n.artifacts/agent-reports/missing.md"}, "block"),
                ("traversal blocks", {"hook_event_name": "SubagentStop", "last_assistant_message": "PASS\n.artifacts/agent-reports/../../escape.md"}, "block"),
                ("long receipt blocks", {"hook_event_name": "SubagentStop", "last_assistant_message": too_long}, "block"),
                ("retry cannot loop", {"hook_event_name": "SubagentStop", "stop_hook_active": True}, None),
                ("malformed passes", [], None),
            ]
            failures = []
            for label, payload, expected in cases:
                actual = decision(payload)
                kind = None
                if actual:
                    kind = actual.get("decision") or actual.get("hookSpecificOutput", {}).get("hookEventName")
                if kind != expected:
                    failures.append(f"{label}: expected {expected!r}, got {kind!r}")
        finally:
            os.chdir(old_cwd)
    if failures:
        print("selftest failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    print(f"selftest passed: {len(cases)} representative payloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv[1:] else run_hook())
