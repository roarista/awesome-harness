#!/usr/bin/env python3
"""Codex PreToolUse guard for external builder commands.

This is deliberately narrow: it only denies an actual builder invocation whose
embedded task lacks the unit-contract headings.  It does not try to identify
the main agent, so direct apply_patch is advisory rather than blocked.

The emitted deny response uses Codex's nested PreToolUse wire schema. Runtime
hook dispatch remains a disposable-session proof for Unit 4.

Run ``python3 pre_tool_use.py --selftest`` for representative payload checks.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTRACT_HEADINGS = ("CONTEXT", "CHANGE", "GOAL", "VERIFY", "REUSE")
SHELL_CONTROL = {";", "&&", "||", "|", "(", ")"}
WRITE_INTENT = re.compile(
    r"\b(?:edit|write|modify|implement|fix|patch|create|delete|add|remove|rename|"
    r"refactor|update)\b|\bchange\b(?!\s*:)",
    re.IGNORECASE,
)
EDIT_VERB = r"(?:edit|write|modify|implement|fix|patch|create|delete|add|remove|rename|refactor|update|change)"
NORTHSTAR_EDIT = re.compile(
    rf"\b{EDIT_VERB}\b[^;\n]{{0,80}}\.northstar\.md\b|"
    rf"\.northstar\.md\b[^;\n]{{0,80}}\b{EDIT_VERB}\b",
    re.IGNORECASE,
)
READ_ONLY = re.compile(
    r"(?:--read-only\b|\b(?:inspect|review|audit)\s+only\b|\bno\s+"
    r"(?:edits?|changes?|modifications?)\b|\bdo\s+not\s+"
    r"(?:edit|write|modify|change|patch)\b|\bdon't\s+"
    r"(?:edit|write|modify|change|patch)\b)",
    re.IGNORECASE,
)


def command_from(payload: Any) -> str | None:
    """Extract a Bash command from Codex's hook payload without trusting shape."""
    if not isinstance(payload, dict):
        return None
    if payload.get("tool_name") not in (None, "Bash"):
        return None
    for key in ("tool_input", "toolInput", "input"):
        value = payload.get(key)
        if isinstance(value, dict) and isinstance(value.get("command"), str):
            return value["command"]
    if isinstance(payload.get("command"), str):
        return payload["command"]
    return None


def shell_segments(command: str) -> list[list[str]]:
    """Return executable shell segments; malformed shell text is ignored."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SHELL_CONTROL:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def is_builder_segment(segment: list[str]) -> bool:
    """Recognize only executable builder forms, never quoted/search text."""
    while segment and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", segment[0]):
        segment = segment[1:]
    if not segment:
        return False
    executable = os.path.basename(segment[0])
    if executable == "codex" and len(segment) > 1:
        return segment[1] == "exec" or segment[1].startswith("--edit")
    if executable == "glm":
        return any(token.startswith("--edit") for token in segment[1:])
    if executable != "node":
        return False
    return any("codex-companion" in os.path.basename(token) for token in segment[1:]) and (
        "task" in segment[1:]
    )


def is_builder(command: str) -> bool:
    return any(is_builder_segment(segment) for segment in shell_segments(command))


def has_write_intent(command: str) -> bool:
    """Only contract external builder tasks that request a source mutation."""
    return bool(WRITE_INTENT.search(command)) and not bool(READ_ONLY.search(command))


def edits_northstar(command: str) -> bool:
    """Require an edit action tied to the path, not a mere path mention."""
    return bool(NORTHSTAR_EDIT.search(command))


def missing_headings(command: str) -> list[str]:
    upper = command.upper()
    return [heading for heading in CONTRACT_HEADINGS if heading not in upper]


def deny(reason: str) -> dict[str, dict[str, str]]:
    """Build the exact PreToolUse response shape Codex consumes."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def decision(payload: Any) -> dict[str, Any] | None:
    """Return Codex's documented deny response, or None to allow/fail open."""
    command = command_from(payload)
    if command is None or not is_builder(command) or not has_write_intent(command):
        return None
    if edits_northstar(command):
        return deny(
            "External builders may not edit .northstar.md; return the proposed "
            "change to the orchestrator for an explicit decision."
        )
    missing = missing_headings(command)
    if not missing:
        return None
    return deny(
        "External builder task is missing unit-contract headings: "
        + ", ".join(missing)
        + ". Include CONTEXT, CHANGE, GOAL, VERIFY, and a REUSE codebase-first pointer."
    )


def advisory_log_path() -> Path | None:
    """Use Git metadata so advisory telemetry never dirties the working tree."""
    override = os.environ.get("AWESOME_HARNESS_ADVISORY_LOG")
    if override:
        return Path(override)
    try:
        git_dir = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(git_dir) / "awesome-harness" / "codex-advisory.jsonl"


def record_apply_patch_advisory(payload: Any) -> None:
    """Record the event, never its patch content, and never block the edit."""
    if not isinstance(payload, dict) or payload.get("tool_name") != "apply_patch":
        return
    try:
        path = advisory_log_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "direct_apply_patch_advisory",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except OSError:
        # Telemetry cannot make a normal edit fail.
        return


def run_hook() -> int:
    try:
        payload = json.load(sys.stdin)
        result = decision(payload)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        # A malformed hook payload must not stop normal work.
        return 0
    record_apply_patch_advisory(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


def selftest() -> int:
    """Check local logic and the exact deny wire shape; Unit 4 proves dispatch."""
    cases = [
        (
            "ordinary shell command passes",
            {"tool_name": "Bash", "tool_input": {"command": "git status --short"}},
            None,
        ),
        (
            "builder with contract passes",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "codex exec 'CONTEXT: x CHANGE: update parser GOAL: z "
                        "VERIFY: q REUSE: .scratch/discovery/parser.md'"
                    )
                },
            },
            None,
        ),
        (
            "builder without contract is denied",
            {"tool_name": "Bash", "tool_input": {"command": "glm --edit 'fix it'"}},
            "deny",
        ),
        (
            "read-only builder without contract passes",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "codex exec 'inspect only the parser'"},
            },
            None,
        ),
        (
            "non-builder codex inspection passes",
            {"tool_name": "Bash", "tool_input": {"command": "codex --version"}},
            None,
        ),
        (
            "builder north-star attempt is denied",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "codex exec 'CONTEXT: x CHANGE: edit .northstar.md "
                        "GOAL: z VERIFY: q'"
                    )
                },
            },
            "deny",
        ),
        (
            "harmless north-star mention passes",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "codex exec 'CONTEXT: x CHANGE: update parser; mention "
                        ".northstar.md only in the report GOAL: z VERIFY: q "
                        "REUSE: .scratch/discovery/parser.md'"
                    )
                },
            },
            None,
        ),
        (
            "echoed builder text is not a builder",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo 'codex exec fix the parser'"},
            },
            None,
        ),
        (
            "searched builder text is not a builder",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "rg 'glm --edit fix it' docs"},
            },
            None,
        ),
        (
            "apply_patch payload is advisory",
            {"tool_name": "apply_patch", "tool_input": {"patch": "*** Begin Patch"}},
            None,
        ),
        (
            "builder with contract but no REUSE is denied",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "codex exec 'CONTEXT: x CHANGE: update parser "
                        "GOAL: z VERIFY: q'"
                    )
                },
            },
            "deny",
        ),
        (
            "builder with contract and REUSE passes",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "codex exec 'CONTEXT: x CHANGE: update parser GOAL: z "
                        "VERIFY: q REUSE: .scratch/discovery/parser.md'"
                    )
                },
            },
            None,
        ),
        ("malformed payload passes", {"tool_name": "Bash", "tool_input": []}, None),
    ]
    failures = []
    for label, payload, expected in cases:
        actual = decision(payload)
        actual_kind = (
            actual["hookSpecificOutput"]["permissionDecision"] if actual else None
        )
        if actual_kind != expected:
            failures.append(f"{label}: expected {expected!r}, got {actual_kind!r}")
        if expected == "deny" and actual is not None:
            wire = json.loads(json.dumps(actual))
            output = wire.get("hookSpecificOutput")
            expected_keys = {
                "hookEventName",
                "permissionDecision",
                "permissionDecisionReason",
            }
            if not isinstance(output, dict) or set(output) != expected_keys:
                failures.append(f"{label}: deny wire shape is not exact")
            elif output["hookEventName"] != "PreToolUse":
                failures.append(f"{label}: deny wire event is not PreToolUse")
    if failures:
        print("selftest failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    old_log = os.environ.get("AWESOME_HARNESS_ADVISORY_LOG")
    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / "advisory.jsonl"
        os.environ["AWESOME_HARNESS_ADVISORY_LOG"] = str(log)
        record_apply_patch_advisory(
            {"tool_name": "apply_patch", "tool_input": {"patch": "private source"}}
        )
        records = log.read_text(encoding="utf-8") if log.exists() else ""
    if old_log is None:
        os.environ.pop("AWESOME_HARNESS_ADVISORY_LOG", None)
    else:
        os.environ["AWESOME_HARNESS_ADVISORY_LOG"] = old_log
    if "direct_apply_patch_advisory" not in records or "private source" in records:
        print("selftest failed: apply_patch advisory record", file=sys.stderr)
        return 1
    print(f"selftest passed: {len(cases)} representative payloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv[1:] else run_hook())
