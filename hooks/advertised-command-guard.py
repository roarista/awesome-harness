#!/usr/bin/env python3
"""Advertised-command guard — "a build is not verified until you have run the
exact command string it tells a user to run."

Three bugs in one day (awesome-harness, 2026-08-04) had the same shape: the
tool was correct and the thing POINTING at it was wrong. The worst was
`tools/l0.py` printing `Zoom in: tools/l1.py <area>` — a path that existed in
1 of the 5 repos it served. l1.py worked perfectly the whole time; the
instruction to reach it was dead. Testing "does l1.py work" never touches that.

So this hook keeps a per-session ledger of two sets and compares them at Stop:

  ADVERTISED — script commands appearing in content the session WROTE
               (Write/Edit), i.e. instructions a human or agent will copy-paste
  RAN        — script commands the session actually EXECUTED via Bash

Anything advertised but never run is reported at Stop. Advisory (exit 0): a
blocking Stop hook can wedge a session, and the cost of the miss is a stale
pointer, not data loss. The message names the exact command to paste.

Wire (all three, same script):
  PreToolUse  Bash              -> record RAN
  PostToolUse Write|Edit|MultiEdit -> record ADVERTISED
  Stop                          -> report

Kill switch: ADVERTISED_COMMAND_GUARD=off. Fail-open on any error.
"""
import json
import os
import re
import sys
from pathlib import Path

STATE = Path(os.path.expanduser("~/.claude/hooks/state/advcmd"))

# A script we could be told to run. Basename only — `tools/l1.py` and
# `~/.claude/tools/l1.py` are the same build, and it is the PATH that varies
# (that is the whole bug), so the path must not be part of the identity.
SCRIPT = re.compile(r"([\w.\-/]+\.(?:py|sh))\b")

# A line only ADVERTISES a command if it also looks like an invocation. Without
# this, every `import foo.py` mention and every path in prose becomes a finding
# and the hook cries wolf until it is turned off.
RUN_MARKERS = ("python3", "python ", "bash ", "sh ", "./", "$ ", "run:", "Run:")

# Files whose text is not instructions to anyone: lockfiles, data, the ledger.
SKIP_SUFFIX = (".json", ".lock", ".jsonl", ".csv", ".svg", ".png")


def sid(data: dict) -> str:
    s = str(data.get("session_id") or "nosession")
    return re.sub(r"[^A-Za-z0-9_-]", "", s)[:64] or "nosession"


def _f(s: str) -> Path:
    return STATE / (s + ".json")


def load(s: str) -> dict:
    try:
        return json.loads(_f(s).read_text())
    except Exception:
        return {}


def save(s: str, d: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    _f(s).write_text(json.dumps(d))


def scripts(text: str, require_marker: bool) -> set:
    out = set()
    for line in (text or "").splitlines():
        if require_marker and not any(m in line for m in RUN_MARKERS):
            continue
        for m in SCRIPT.finditer(line):
            out.add(os.path.basename(m.group(1)))
    return out


def advertised_lines(text: str) -> dict:
    """basename -> the first line advertising it, so the report can quote it."""
    out = {}
    for line in (text or "").splitlines():
        if not any(m in line for m in RUN_MARKERS):
            continue
        for m in SCRIPT.finditer(line):
            out.setdefault(os.path.basename(m.group(1)), line.strip()[:160])
    return out


def main() -> None:
    if os.environ.get("ADVERTISED_COMMAND_GUARD", "").lower() == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    event = data.get("hook_event_name", "")
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    s = sid(data)
    led = load(s)
    ran = set(led.get("ran", []))
    adv = dict(led.get("adv", {}))

    if event == "PreToolUse" and tool == "Bash":
        ran |= scripts(str(ti.get("command", "")), require_marker=False)
        save(s, {"ran": sorted(ran), "adv": adv})

    elif event == "PostToolUse" and tool in ("Write", "Edit", "MultiEdit"):
        path = str(ti.get("file_path", ""))
        if path.endswith(SKIP_SUFFIX):
            return
        text = ti.get("content") or ti.get("new_string") or ""
        if tool == "MultiEdit":
            text = "\n".join(
                str(e.get("new_string", "")) for e in (ti.get("edits") or [])
            )
        found = advertised_lines(text)
        # A script never advertises ITSELF into existence — skip self-reference,
        # which is just the file's own shebang or docstring naming its own path.
        me = os.path.basename(path)
        for k, v in found.items():
            if k != me:
                adv.setdefault(k, v)
        save(s, {"ran": sorted(ran), "adv": adv})

    elif event == "Stop":
        missing = {k: v for k, v in adv.items() if k not in ran}
        if not missing:
            return
        lines = [
            "UNVERIFIED ADVERTISED COMMANDS — this session wrote instructions "
            "to run these, and never ran them:"
        ]
        for k, v in sorted(missing.items())[:8]:
            lines.append(f"  {k}   advertised as: {v}")
        lines.append(
            "A build is not verified until the exact command string it tells a "
            "user to run has been executed, copy-pasted verbatim, from the "
            "directory it will actually run in. Run them, or say in the final "
            "message that they are unverified. (kill: ADVERTISED_COMMAND_GUARD=off)"
        )
        sys.stderr.write("\n".join(lines) + "\n")


def selftest() -> None:
    ok = True
    cases = [
        ("advertises a run line", "Zoom in: python3 tools/l1.py <area>", {"l1.py"}),
        ("ignores prose mention", "see tools/l1.py for details", set()),
        ("ignores an import", "from tools.l1 import x", set()),
        ("catches ./ form", "  ./scripts/deploy.sh --now", {"deploy.sh"}),
    ]
    for label, text, want in cases:
        got = set(advertised_lines(text))
        ok &= got == want
        print(("PASS " if got == want else f"FAIL {got!r} != {want!r} ") + label)
    got = scripts("python3 ~/.claude/tools/l1.py services/sketch", False)
    ok &= "l1.py" in got
    print(("PASS " if "l1.py" in got else "FAIL ") + "ran set is path-insensitive")
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    try:
        if "--selftest" in sys.argv:
            selftest()
        main()
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)  # advisory only: never block a turn over this
