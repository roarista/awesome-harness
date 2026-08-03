#!/usr/bin/env python3
"""PreToolUse(Task|Agent) — check whether the spawn is needed at all, and whether
the requested agent matches what the router would pick. `tools/route-model.sh`
already answers both questions (NECESSITY + AGENT) and NOTHING calls it — this
wires it in at the only point with leverage: before the spawn happens.

Design: SILENT unless there's something to say. A hook that fires prose on
every one of 186 spawns/session is pure cost (measured 2026-08-02: the fleet is
51.9% of all tokens). Only three things ever print:
  1. router says DO-NOT-LAUNCH -> one short advisory block (never blocks).
  2. router's AGENT differs from the requested subagent_type -> one line.
  3. this is spawn #8+ this session (once) -> one nudge line.

Kill-switch: SPAWN_NECESSITY=off. Fail-open on ANY error: exit 0, print nothing,
never block a spawn.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hookout

SPAWN_COUNTER_DIR = Path.home() / ".claude" / "hooks" / "state" / "spawn-count"


def session_id(data: dict) -> str:
    """Mirrors hooks/harness-usage-telemetry.py's session_id() derivation."""
    tp = str(data.get("session_id") or data.get("transcript_path") or "")
    if not tp:
        return "unknown"
    stem = Path(tp).stem
    return stem or hashlib.sha1(tp.encode()).hexdigest()[:12]


def repo_root() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=5,
    )
    if out.returncode != 0:
        return ""
    return out.stdout.strip()


def run_router(root: str, prompt: str) -> str:
    script = os.path.join(root, "tools", "route-model.sh")
    if not os.path.isfile(script):
        return ""
    out = subprocess.run(
        ["bash", script, prompt[:400]],
        capture_output=True, text=True, timeout=10, cwd=root,
    )
    return out.stdout


def parse_router(output: str):
    """-> (necessity, reason, agent, why)"""
    necessity = None
    reason = ""
    agent = ""
    why = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("NECESSITY: DO-NOT-LAUNCH"):
            necessity = "DO-NOT-LAUNCH"
            reason = line.split(":", 2)[-1].strip() if line.count(":") >= 2 else ""
        elif line.startswith("NECESSITY: LAUNCH"):
            necessity = "LAUNCH"
        elif line.startswith("AGENT:"):
            agent = line.split(":", 1)[1].strip()
        elif line.startswith("WHY:"):
            why = line.split(":", 1)[1].strip()
    return necessity, reason, agent, why


def bump_spawn_count(sid: str) -> int:
    SPAWN_COUNTER_DIR.mkdir(parents=True, exist_ok=True)
    path = SPAWN_COUNTER_DIR / sid
    n = 0
    if path.exists():
        try:
            n = int(path.read_text().strip() or "0")
        except Exception:
            n = 0
    n += 1
    path.write_text(str(n))
    return n


def main():
    if os.environ.get("SPAWN_NECESSITY", "").strip().lower() == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    ti = data.get("tool_input", {}) or {}
    prompt = str(ti.get("prompt", "") or "")
    requested_agent = str(ti.get("subagent_type", "") or "")

    root = repo_root()
    if not root:
        return

    router_out = run_router(root, prompt)
    if not router_out:
        return

    necessity, reason, routed_agent, why = parse_router(router_out)

    lines = []
    if necessity == "DO-NOT-LAUNCH":
        lines.append(
            f"SPAWN ADVISORY: router says DO-NOT-LAUNCH ({reason or 'no reason given'}) — "
            "main can likely do this directly instead of spawning."
        )
    elif routed_agent and requested_agent and routed_agent != requested_agent:
        lines.append(
            f"ROUTER: this reads as {routed_agent}; you spawned {requested_agent}. {why}".strip()
        )

    sid = session_id(data)
    try:
        count = bump_spawn_count(sid)
    except Exception:
        count = 0
    if count == 8 and _hookout.once("spawn-necessity-8", sid):
        lines.append(
            "SPAWN #8 this session. The fleet is 51.9% of all tokens and ~75% of "
            "returns are discarded — is this one necessary, or can main answer "
            "from the codemap?"
        )

    if lines:
        _hookout.inject("PreToolUse", "\n".join(lines))


def _selftest():
    import tempfile

    ok = True

    # Case 1: DO-NOT-LAUNCH prompt should print something.
    env = dict(os.environ)
    payload = json.dumps({
        "session_id": "selftest-session-1",
        "tool_input": {"subagent_type": "codex", "prompt": "read one file and summarize it"},
    })
    r = subprocess.run(
        [sys.executable, __file__], input=payload, capture_output=True, text=True, env=env,
    )
    passed = len(r.stdout.strip()) > 0
    print(("PASS" if passed else "FAIL") + ": DO-NOT-LAUNCH prints something")
    ok = ok and passed

    # Case 2: correctly-routed LAUNCH prompt should print NOTHING.
    payload = json.dumps({
        "session_id": "selftest-session-2",
        "tool_input": {"subagent_type": "codex-audit", "prompt": "audit this diff for correctness"},
    })
    r = subprocess.run(
        [sys.executable, __file__], input=payload, capture_output=True, text=True, env=env,
    )
    passed = len(r.stdout.strip()) == 0
    print(("PASS" if passed else "FAIL") + ": correctly-routed LAUNCH prints nothing")
    ok = ok and passed

    # Case 3: mismatched agent prints one line.
    payload = json.dumps({
        "session_id": "selftest-session-3",
        "tool_input": {"subagent_type": "opus", "prompt": "audit this diff for correctness"},
    })
    r = subprocess.run(
        [sys.executable, __file__], input=payload, capture_output=True, text=True, env=env,
    )
    passed = len(r.stdout.strip()) > 0
    print(("PASS" if passed else "FAIL") + ": mismatched agent prints one line")
    ok = ok and passed

    # Case 4: missing router (run from a dir with no tools/route-model.sh) exits silent.
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["git", "init", "-q"], cwd=td)
        payload = json.dumps({
            "session_id": "selftest-session-4",
            "tool_input": {"subagent_type": "codex", "prompt": "read one file and summarize it"},
        })
        r = subprocess.run(
            [sys.executable, __file__], input=payload, capture_output=True, text=True,
            env=env, cwd=td,
        )
        passed = len(r.stdout.strip()) == 0 and r.returncode == 0
        print(("PASS" if passed else "FAIL") + ": missing router exits silent")
        ok = ok and passed

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
