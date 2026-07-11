#!/usr/bin/env python3
"""PostToolUse(all tools) — per-session harness-usage telemetry. READ-ONLY.

Stops Ro from being the manual drift-detector. Observes every tool call and
appends ONE jsonl line per *relevant* event so the weekly `harness-coach` can
audit whether the harness features are actually being USED per session:
  - subagent spawns (Task/Agent)             -> are we delegating?
  - Read of .now.md / northstar / STATE      -> are we orienting?
  - Bash command containing `graphify`       -> are we using the code map?
Every line also carries the session id (derived from transcript_path) and the
running tool-call ordinal, so the coach can bucket by session.

NEVER blocks, NEVER writes to chat, fail-open on ANY error (exit 0 always).

Kill-switch: HARNESS_TELEMETRY=off disables it. Default on-but-harmless
(read-only append). Also silently no-ops if the state dir isn't writable.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

LOG = Path.home() / ".claude" / "hooks" / "state" / "harness-usage.jsonl"

# filename fragments that count as an "orientation" Read
ORIENT_RE = re.compile(r"(\.now\.md|\.northstar\.md|northstar|STATE\.md|/STATE)", re.IGNORECASE)


def session_id(data: dict) -> str:
    tp = str(data.get("session_id") or data.get("transcript_path") or "")
    if not tp:
        return "unknown"
    # prefer the transcript filename stem; else hash whatever we have
    stem = Path(tp).stem
    return stem or hashlib.sha1(tp.encode()).hexdigest()[:12]


def classify(data: dict):
    """Return (event, detail) if relevant, else (None, None)."""
    tool = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    if tool in ("Task", "Agent"):
        sub = ti.get("subagent_type") or ti.get("description") or ""
        return "subagent_spawn", str(sub)
    if tool == "Read":
        fp = str(ti.get("file_path") or "")
        if ORIENT_RE.search(fp):
            return "orient_read", os.path.basename(fp)
    if tool == "Bash":
        cmd = str(ti.get("command") or "")
        if "graphify" in cmd:
            return "graphify_run", cmd[:120]
    return None, None


def main() -> None:
    if os.environ.get("HARNESS_TELEMETRY", "on").lower() == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    event, detail = classify(data)
    if event is None:
        return  # not a harness-relevant event; stay lightweight
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        line = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "session": session_id(data),
            "event": event,
            "tool": data.get("tool_name", ""),
            "detail": detail,
        }
        with LOG.open("a") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        pass  # never error on a read-only telemetry append


def _selftest() -> None:
    cases = [
        ({"tool_name": "Task", "tool_input": {"subagent_type": "codex"}}, "subagent_spawn"),
        ({"tool_name": "Agent", "tool_input": {"description": "x"}}, "subagent_spawn"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/x/.now.md"}}, "orient_read"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/x/STATE.md"}}, "orient_read"),
        ({"tool_name": "Read", "tool_input": {"file_path": "/x/foo.py"}}, None),
        ({"tool_name": "Bash", "tool_input": {"command": "graphify query foo"}}, "graphify_run"),
        ({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}, None),
        ({}, None),
    ]
    ok = True
    for d, want in cases:
        got, _ = classify(d)
        ok &= got == want
        print(f"  classify(tool={d.get('tool_name','-')}) = {got} (want {want})")
    sid = session_id({"transcript_path": "/private/tmp/x/tasks/a1b2.jsonl"})
    ok &= sid == "a1b2"
    print(f"  session_id(tasks path) = {sid} (want a1b2)")
    # kill-switch -> no-op
    os.environ["HARNESS_TELEMETRY"] = "off"
    assert main() is None
    os.environ.pop("HARNESS_TELEMETRY", None)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
