#!/usr/bin/env python3
"""Compact Codex guard for builder contracts and irreversible writes.

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
NORTHSTAR_PATCH = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File: .*\.northstar\.md$", re.MULTILINE
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


def executable_segment(raw: list[str]) -> tuple[str, list[str]]:
    """Strip common execution wrappers and return executable plus arguments."""
    segment = raw[:]
    while segment and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", segment[0]):
        segment = segment[1:]
    while segment and os.path.basename(segment[0]) in {"command", "env", "sudo"}:
        wrapper = os.path.basename(segment.pop(0))
        while segment and segment[0].startswith("-"):
            option = segment.pop(0)
            if wrapper == "sudo" and option in {"-C", "-D", "-g", "-h", "-p", "-R", "-r", "-t", "-T", "-u"} and segment:
                segment.pop(0)
            elif wrapper == "env" and option in {"-C", "--chdir", "-S", "--split-string", "-u", "--unset"} and segment:
                segment.pop(0)
        while wrapper == "env" and segment and re.match(
            r"^[A-Za-z_][A-Za-z0-9_]*=", segment[0]
        ):
            segment.pop(0)
    if not segment:
        return "", []
    return os.path.basename(segment[0]), segment[1:]


def git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    """Skip common Git global options, including options that consume a value."""
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"-C", "-c", "--exec-path", "--git-dir", "--namespace", "--work-tree"}:
            index += 2
        elif token.startswith(("--exec-path=", "--git-dir=", "--namespace=", "--work-tree=")):
            index += 1
        elif token in {"--bare", "--no-pager", "--paginate", "--literal-pathspecs", "--no-optional-locks"}:
            index += 1
        else:
            return token, args[index + 1 :]
    return "", []


def irreversible_reason(command: str) -> str | None:
    """Recognize a deliberately small set of destructive executable forms."""
    for segment in shell_segments(command):
        executable, args = executable_segment(segment)
        if not executable:
            continue
        if executable == "rm":
            force = any(arg == "--force" or (arg.startswith("-") and "f" in arg) for arg in args)
            recursive = any(
                arg == "--recursive" or (arg.startswith("-") and "r" in arg) for arg in args
            )
            if force and recursive:
                return "recursive forced removal"
        subcommand, subargs = git_subcommand(args) if executable == "git" else ("", [])
        if subcommand == "reset" and "--hard" in subargs:
            return "git reset --hard"
        if subcommand == "clean" and any(
            arg.startswith("-") and "f" in arg and "d" in arg for arg in subargs
        ):
            return "git clean with force and directory removal"
        if subcommand == "push" and any(
            arg in {"-f", "--force", "--force-with-lease"} for arg in subargs
        ):
            return "forced git push"
    return None


def shell_writes_northstar(command: str) -> bool:
    """Recognize direct shell writers targeting the protected file."""
    for segment in shell_segments(command):
        if not any(Path(token).name == ".northstar.md" for token in segment):
            joined = " ".join(segment)
            executable, _ = executable_segment(segment)
            if not (executable.startswith("python") and ".northstar.md" in joined):
                continue
        executable, args = executable_segment(segment)
        if executable in {"rm", "tee", "touch", "truncate"}:
            return True
        if executable == "sed" and any(arg == "--in-place" or arg.startswith("-i") for arg in args):
            return True
        if executable == "mv":
            operands = [arg for arg in args if not arg.startswith("-")]
            if any(Path(arg).name == ".northstar.md" for arg in operands):
                return True
        if executable in {"cp", "install"}:
            operands = [arg for arg in args if not arg.startswith("-")]
            if operands and Path(operands[-1]).name == ".northstar.md":
                return True
        if executable.startswith("python"):
            joined = " ".join(args)
            if re.search(
                r"(?:write_text|write_bytes|unlink|remove|replace|rename)\s*\(|"
                r"open\s*\([^)]*\.northstar\.md[^)]*['\"](?:w|a|x|\+)|"
                r"Path\s*\([^)]*\.northstar\.md[^)]*\)\.open\s*\([^)]*"
                r"(?:mode\s*=\s*)?['\"](?:w|a|x|\+)",
                joined,
            ):
                return True
        if any(token.startswith(">") for token in segment):
            return True
    return False


def patch_edits_northstar(payload: Any) -> bool:
    if not isinstance(payload, dict) or payload.get("tool_name") != "apply_patch":
        return False
    for key in ("tool_input", "toolInput", "input"):
        value = payload.get(key)
        if isinstance(value, dict):
            for field in ("patch", "input", "command"):
                patch = value.get(field)
                if isinstance(patch, str) and NORTHSTAR_PATCH.search(patch):
                    return True
    return False


def is_git_commit(command: str) -> bool:
    for segment in shell_segments(command):
        executable, args = executable_segment(segment)
        if executable == "git" and git_subcommand(args)[0] == "commit":
            return True
    return False


def check_all_failure(command: str) -> str | None:
    """Run the installed fast gate only for an armed repository commit."""
    if not is_git_commit(command) or not Path(".check-all.json").is_file():
        return None
    runner = Path(__file__).resolve().parents[2] / "tools" / "check-all" / "check_all.sh"
    if not runner.is_file():
        return "check-all is armed, but its installed runner is missing"
    result = subprocess.run(
        ["bash", str(runner), str(Path.cwd()), "--fast"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode:
        tail = (result.stdout + result.stderr).strip().splitlines()[-1:]
        return "check-all fast gate failed" + (f": {tail[0]}" if tail else "")
    return None


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
    if patch_edits_northstar(payload):
        return deny("Do not edit .northstar.md without Ro's explicit approval.")
    command = command_from(payload)
    if command is None:
        return None
    destructive = irreversible_reason(command)
    if destructive:
        return deny(f"Blocked irreversible command ({destructive}); get explicit approval.")
    if edits_northstar(command) or shell_writes_northstar(command):
        return deny("Do not edit .northstar.md without Ro's explicit approval.")
    gate_failure = check_all_failure(command)
    if gate_failure:
        return deny(gate_failure)
    if not is_builder(command) or not has_write_intent(command):
        return None
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
    except (json.JSONDecodeError, OSError, subprocess.SubprocessError, TypeError, ValueError):
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
            "north-star patch is denied",
            {
                "tool_name": "apply_patch",
                "tool_input": {"patch": "*** Update File: .northstar.md\n@@"},
            },
            "deny",
        ),
        (
            "recursive forced removal is denied",
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}},
            "deny",
        ),
        (
            "hard reset is denied",
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}},
            "deny",
        ),
        (
            "split recursive forced removal is denied",
            {"tool_name": "Bash", "tool_input": {"command": "rm -r -f build"}},
            "deny",
        ),
        (
            "command wrapper removal is denied",
            {"tool_name": "Bash", "tool_input": {"command": "command rm -rf build"}},
            "deny",
        ),
        (
            "sudo wrapper removal is denied",
            {"tool_name": "Bash", "tool_input": {"command": "sudo rm -rf build"}},
            "deny",
        ),
        (
            "env unset wrapper removal is denied",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "env -u NAME rm -rf build"},
            },
            "deny",
        ),
        (
            "git global option hard reset is denied",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git -C /tmp/repo reset --hard HEAD"},
            },
            "deny",
        ),
        (
            "shell north-star write is denied",
            {"tool_name": "Bash", "tool_input": {"command": "touch .northstar.md"}},
            "deny",
        ),
        (
            "read-only sed north-star passes",
            {"tool_name": "Bash", "tool_input": {"command": "sed -n 1,20p .northstar.md"}},
            None,
        ),
        (
            "copy from north-star passes",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "cp .northstar.md /tmp/northstar-copy"},
            },
            None,
        ),
        (
            "copy to north-star is denied",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "cp /tmp/new-northstar .northstar.md"},
            },
            "deny",
        ),
        (
            "move from north-star is denied",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "mv .northstar.md /tmp/saved"},
            },
            "deny",
        ),
        (
            "python north-star write is denied",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -c \"from pathlib import Path; Path('.northstar.md').write_text('x')\""
                },
            },
            "deny",
        ),
        (
            "python Path open north-star write is denied",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 -c \"from pathlib import Path; Path('.northstar.md').open(mode='w').close()\""
                },
            },
            "deny",
        ),
        (
            "apply_patch command field north-star edit is denied",
            {
                "tool_name": "apply_patch",
                "tool_input": {"command": "*** Update File: .northstar.md\n@@"},
            },
            "deny",
        ),
        (
            "quoted destructive text passes",
            {"tool_name": "Bash", "tool_input": {"command": "echo 'rm -rf build'"}},
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
    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".check-all.json").write_text(
            '{"base_command":"false"}\n', encoding="utf-8"
        )
        os.chdir(repo)
        try:
            gated = decision(
                {"tool_name": "Bash", "tool_input": {"command": "git commit -m test"}}
            )
        finally:
            os.chdir(original_cwd)
    if (
        not gated
        or "check-all fast gate failed"
        not in gated["hookSpecificOutput"]["permissionDecisionReason"]
    ):
        print("selftest failed: armed commit gate", file=sys.stderr)
        return 1
    print(f"selftest passed: {len(cases)} representative payloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest() if "--selftest" in sys.argv[1:] else run_hook())
