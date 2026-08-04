#!/usr/bin/env python3
"""Adversarial bench for advertised-command-guard.py.

Feeds it realistic hook payloads across many settings and reports, for each,
whether it FIRED (reported an unverified advertised command) and what it said.
Each case declares what SHOULD happen, so this is a pass/fail table, not a dump.
"""
import json
import os
import subprocess
import sys
import tempfile
import uuid

HOOK = os.path.expanduser("~/.claude/hooks/advertised-command-guard.py")


def run(payload, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run(
        [sys.executable, HOOK], input=json.dumps(payload), text=True,
        capture_output=True, env=e,
    )
    return p.returncode, p.stderr.strip()


def session():
    return "fuzz-" + uuid.uuid4().hex[:12]


def scenario(name, writes, runs, should_fire, env=None):
    """writes: [(tool, file_path, content_or_new_string)], runs: [cmd]"""
    sid = session()
    for tool, path, text in writes:
        ti = {"file_path": path}
        if tool == "Write":
            ti["content"] = text
        elif tool == "MultiEdit":
            ti["edits"] = [{"new_string": text}]
        else:
            ti["new_string"] = text
        run({"hook_event_name": "PostToolUse", "tool_name": tool,
             "tool_input": ti, "session_id": sid}, env)
    for c in runs:
        run({"hook_event_name": "PreToolUse", "tool_name": "Bash",
             "tool_input": {"command": c}, "session_id": sid}, env)
    rc, err = run({"hook_event_name": "Stop", "session_id": sid}, env)
    fired = "UNVERIFIED ADVERTISED" in err
    ok = fired == should_fire
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"      expected fire={should_fire} got={fired}")
        if err:
            print("      " + err.splitlines()[0][:150])
    return ok, err


def main():
    ok = True
    print("=== REAL-WORLD SETTINGS ===")

    # 1. THE ACTUAL BUG: a tool prints a zoom menu it never ran.
    ok &= scenario(
        "tool advertises a sibling script, never runs it",
        [("Write", "/r/tools/l0.py",
          'print("Zoom in:   python3 tools/l1.py <area>")')],
        [], True)[0]

    # 2. Same, but the author actually pasted the command.
    ok &= scenario(
        "advertised AND run (the fix)",
        [("Write", "/r/tools/l0.py",
          'print("Zoom in:   python3 tools/l1.py <area>")')],
        ["python3 ~/.claude/tools/l1.py services/sketch"], False)[0]

    # 3. README install instructions never executed.
    ok &= scenario(
        "README documents ./install.sh, never run",
        [("Write", "/r/README.md", "Install:\n\n    ./install.sh --dry-run\n")],
        [], True)[0]

    # 4. README instructions that were smoke-tested.
    ok &= scenario(
        "README documents ./install.sh, and it was run",
        [("Write", "/r/README.md", "Install:\n\n    ./install.sh --dry-run\n")],
        ["cd /r && ./install.sh --dry-run"], False)[0]

    # 5. Prose that merely names a file must stay silent (cry-wolf guard).
    ok &= scenario(
        "prose mention only",
        [("Write", "/r/docs/x.md", "The logic lives in tools/l1.py and is fine.")],
        [], False)[0]

    # 6. Imports are not invocations.
    ok &= scenario(
        "python import of a module",
        [("Write", "/r/a.py", "from tools.l1 import main\nimport tools.l0")],
        [], False)[0]

    # 7. A file naming its own path (shebang/docstring) is not advertising.
    ok &= scenario(
        "self-reference",
        [("Write", "/r/hooks/now-gate.py",
          "# usage: python3 now-gate.py --selftest")],
        [], False)[0]

    # 8. Edit (fragment) rather than Write (whole file).
    ok &= scenario(
        "Edit new_string carries the advert",
        [("Edit", "/r/tools/l0.py", '    print("run: python3 tools/l1.py")')],
        [], True)[0]

    # 9. MultiEdit.
    ok &= scenario(
        "MultiEdit edits list",
        [("MultiEdit", "/r/tools/l0.py", 'print("run: bash tools/check.sh")')],
        [], True)[0]

    # 10. Data files are not instructions.
    ok &= scenario(
        "JSON payload naming a script",
        [("Write", "/r/settings.json",
          '{"command": "python3 $HOME/.claude/hooks/foo.py"}')],
        [], False)[0]

    print("\n=== PATH / SHELL VARIATION (the identity question) ===")

    # 11. Advertised repo-relative, run via absolute — same build, must count.
    ok &= scenario(
        "advertised relative, run absolute",
        [("Write", "/r/tools/l0.py", 'print("python3 tools/skeleton.py <file>")')],
        ["python3 /Users/x/.claude/tools/skeleton.py a.py"], False)[0]

    # 12. Run inside a compound command.
    ok &= scenario(
        "run inside && chain",
        [("Write", "/r/t.py", 'print("run: python3 tools/l1.py x")')],
        ["cd /r && export PATH=/usr/bin && python3 tools/l1.py x | head"], False)[0]

    # 13. Run inside a heredoc-quoted block.
    ok &= scenario(
        "run inside heredoc",
        [("Write", "/r/t.py", 'print("run: bash tools/git-sync.sh")')],
        ["bash <<'EOF'\ntools/git-sync.sh\nEOF"], False)[0]

    # 14. A DIFFERENT script was run — must still fire.
    ok &= scenario(
        "ran a different script",
        [("Write", "/r/t.py", 'print("run: python3 tools/l1.py x")')],
        ["python3 tools/l0.py"], True)[0]

    print("\n=== NODE / TYPESCRIPT ECOSYSTEM (intrn is 89% TS) ===")

    ok &= scenario("node script advertised, never run",
                   [("Write", "/r/README.md", "Run:\n\n    node scripts/build.js\n")],
                   [], True)[0]
    ok &= scenario("node script advertised AND run",
                   [("Write", "/r/README.md", "Run:\n\n    node scripts/build.js\n")],
                   ["node scripts/build.js"], False)[0]
    ok &= scenario("npm run target, never run",
                   [("Write", "/r/README.md", "Run:\n\n    npm run typecheck\n")],
                   [], True)[0]
    ok &= scenario("npm advertised, pnpm used (same target)",
                   [("Write", "/r/README.md", "Run:\n\n    npm run typecheck\n")],
                   ["pnpm run typecheck"], False)[0]
    ok &= scenario("make target, never run",
                   [("Write", "/r/Makefile.md", "Run:\n\n    make test\n")],
                   [], True)[0]
    ok &= scenario("tsx script, never run",
                   [("Write", "/r/README.md", "Run:\n\n    tsx scripts/seed.ts\n")],
                   [], True)[0]

    print("\n=== TS NOISE THAT MUST STAY SILENT ===")

    for name, text in [
        ("ES import with .js extension",
         "import { db } from './lib/db.js'"),
        ("ES import default",
         "import build from '../scripts/build.js';"),
        ("require call", "const x = require('./tools/l1.js')"),
        ("export from", "export { a } from './a.ts'"),
        ("type-only import", "import type { T } from './types.ts'"),
        ("a bare CLI name", "Run:\n\n    graphify update\n"),
    ]:
        ok &= scenario(name, [("Write", "/r/a.ts", text)], [], False)[0]

    print("\n=== ROBUSTNESS ===")

    # Kill switch.
    ok &= scenario("kill switch honoured",
                   [("Write", "/r/t.py", 'print("run: python3 tools/l1.py")')],
                   [], False, env={"ADVERTISED_COMMAND_GUARD": "off"})[0]

    # No session id at all.
    rc, _ = run({"hook_event_name": "Stop"})
    print(("PASS " if rc == 0 else "FAIL ") + "missing session_id exits 0")
    ok &= rc == 0

    # Garbage / empty stdin.
    p = subprocess.run([sys.executable, HOOK], input="", text=True,
                       capture_output=True)
    print(("PASS " if p.returncode == 0 else "FAIL ") + "empty stdin exits 0")
    ok &= p.returncode == 0
    p = subprocess.run([sys.executable, HOOK], input="{not json", text=True,
                       capture_output=True)
    print(("PASS " if p.returncode == 0 else "FAIL ") + "malformed json exits 0")
    ok &= p.returncode == 0

    # Missing tool_input.
    rc, _ = run({"hook_event_name": "PostToolUse", "tool_name": "Write",
                 "session_id": session()})
    print(("PASS " if rc == 0 else "FAIL ") + "missing tool_input exits 0")
    ok &= rc == 0

    # Unicode + very large content.
    big = ("# ünïcode ✓ π\n" * 200) + "run: python3 tools/l1.py x\n" + ("x" * 200000)
    ok &= scenario("unicode + 200KB content",
                   [("Write", "/r/t.md", big)], [], True)[0]

    # Two sessions must not see each other's ledger.
    a, b = session(), session()
    run({"hook_event_name": "PostToolUse", "tool_name": "Write",
         "tool_input": {"file_path": "/r/t.py",
                        "content": 'print("run: python3 tools/zzz.py")'},
         "session_id": a})
    run({"hook_event_name": "PreToolUse", "tool_name": "Bash",
         "tool_input": {"command": "python3 tools/zzz.py"}, "session_id": b})
    _, ea = run({"hook_event_name": "Stop", "session_id": a})
    _, eb = run({"hook_event_name": "Stop", "session_id": b})
    iso = "UNVERIFIED" in ea and "UNVERIFIED" not in eb
    print(("PASS " if iso else "FAIL ") + "sessions are isolated")
    ok &= iso

    # Report cap: 20 adverts -> at most 8 lines listed.
    sid = session()
    many = "\n".join(f"run: python3 tools/s{i}.py" for i in range(20))
    run({"hook_event_name": "PostToolUse", "tool_name": "Write",
         "tool_input": {"file_path": "/r/t.md", "content": many},
         "session_id": sid})
    _, err = run({"hook_event_name": "Stop", "session_id": sid})
    listed = sum(1 for l in err.splitlines() if "advertised as:" in l)
    print(("PASS " if listed == 8 else f"FAIL listed={listed} ")
          + "report caps at 8 entries")
    ok &= listed == 8

    # Stop fires twice (repeat turn) — must stay stable, not crash.
    rc, _ = run({"hook_event_name": "Stop", "session_id": sid})
    print(("PASS " if rc == 0 else "FAIL ") + "repeat Stop exits 0")
    ok &= rc == 0

    print("\nOVERALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
