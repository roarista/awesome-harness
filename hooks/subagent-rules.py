#!/usr/bin/env python3
"""SubagentStart hook: inject core harness rules into harness subagents only.
Subagents don't inherit CLAUDE.md. Builders/auditors get a <=900-byte block; other
agent_types, SDK/print parents and the main session get nothing. Fail-open. `--selftest`.
"""
import json
import os
import subprocess
import sys

R = {
    1: "Ponytail: smallest diff, stdlib first, no unrequested files or abstractions.",
    2: "No source file over 200 lines; a file already over must not grow (the git ratchet blocks it).",
    3: "Never edit .northstar.md, .now.md, .planning/ or settings; the orchestrator owns them.",
    4: "VERIFY = run the commands and paste real output; a claim without output counts as not done.",
    5: "TypeScript: pre-commit runs `trellis audit --baseline`; run it yourself before handing back.",
    6: "Full report to .artifacts/agent-reports/ (auditors: <task>-audit.md; read-only sandbox: in your reply); follow your agent's return contract.",
    7: "Auditors: shared rubric, VERDICT PASS | PASS WITH FIXES | REJECT; REJECT on any HIGH or CRITICAL; reproduce, don't trust claims.",
    8: "Navigate first: graphify query|explain, `python3 ~/.claude/tools/l1.py`, skeleton.py, semgrep, rg; then whole files.",
}
BUILD, AUDIT = (1, 2, 3, 4, 5, 6, 8), (2, 3, 4, 6, 7, 8)
PICK = {"codex": BUILD, "claude": BUILD, "codex-audit": AUDIT, "opus": AUDIT, "opus48-audit": AUDIT}


def block(agent_type):
    keys = PICK.get(agent_type)
    return "Harness rules:\n" + "\n".join("- " + R[k] for k in keys) if keys else ""


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _hookout
    _hookout.exit_if_product()
    e = os.environ  # any SDK/print parent (`claude -p`) is not harness work, whatever its cwd
    if e.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk") and e.get("HARNESS_HOOKS") != "on":
        return
    payload = json.loads(sys.stdin.read() or "{}")
    if isinstance(payload, dict) and payload.get("hook_event_name") == "SubagentStart":
        _hookout.inject("SubagentStart", block(str(payload.get("agent_type") or "")))


def selftest():
    def run(stdin, ep="cli"):
        env = {k: v for k, v in os.environ.items() if k != "HARNESS_HOOKS"}
        p = subprocess.run([sys.executable, __file__], input=stdin, capture_output=True, text=True,
                           env=dict(env, CLAUDE_CODE_ENTRYPOINT=ep), timeout=10)
        return p.returncode, p.stdout
    fails = []
    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name) or cond or fails.append(name)
    for t, want, skip in (("codex", R[5], R[7]), ("opus48-audit", R[7], R[5])):
        rc, out = run(json.dumps({"hook_event_name": "SubagentStart", "agent_type": t, "agent_id": "x"}))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        check(t + " right lines", rc == 0 and want in ctx and skip not in ctx)
        check(t + " block <=900 bytes, <=12 lines (%d B)" % len(ctx.encode()), len(ctx.encode()) <= 900 and ctx.count("\n") < 12)
    check("Explore gets nothing", run('{"hook_event_name":"SubagentStart","agent_type":"Explore"}') == (0, ""))
    check("Stop payload, agent_type=codex: 0 bytes", run('{"hook_event_name":"Stop","agent_type":"codex"}') == (0, ""))
    check("sdk-cli parent, repo cwd: nothing", run('{"hook_event_name":"SubagentStart","agent_type":"claude"}', "sdk-cli") == (0, ""))
    check("garbage JSON exit 0, silent", run("{not json") == (0, ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
