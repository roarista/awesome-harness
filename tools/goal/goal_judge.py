#!/usr/bin/env python3
"""goal_judge.py — independent "is it DONE?" helper for the /goal loop.

Moves the done-decision OFF the maker: the loop orchestrator spawns a SEPARATE
judge sub-agent (a different model than the worker) that fills in an explicit
checklist; this script provides the MECHANICAL scaffolding around that judgment:

  1. clean-verify  — run detectors/tests from a CLEAN checkout of committed HEAD
                     (a throwaway `git worktree`), so a doctored conftest.py /
                     test file in the working tree can't fake green. Fail-OPEN:
                     if git state makes this unsafe, it warns and runs in place.
  2. gate          — pure no-advance-on-red + bounded-retry decision.
  3. grade         — pure checklist grader (PASS only if every item verified,
                     zero red).

Everything here is ADVISORY and flag-gated by the caller (GOAL_INDEPENDENT_JUDGE,
default off = current /goal behavior). Nothing here blocks or mutates the repo
beyond a temporary worktree it always cleans up.

stdlib only. `python3 goal_judge.py --selftest` exercises the pure functions.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Pure functions (unit-tested by --selftest)
# ---------------------------------------------------------------------------

# gate() verdicts
ADVANCE = "ADVANCE"                      # verify passed -> mark unit done
RETRY = "RETRY"                          # red, but retries remain -> root-cause fix
STOP_MAX_RETRIES_RED = "STOP_MAX_RETRIES_RED"  # red, out of retries -> NEVER mark done


def gate(passed: bool, retry: int, max_retries: int = 3) -> str:
    """No-advance-on-red decision.

    passed=True                          -> ADVANCE
    passed=False and retry < max_retries -> RETRY   (caller re-injects a 5-Whys
                                                      root-cause-fix directive and
                                                      re-verifies with retry+1)
    passed=False and retry >= max_retries-> STOP_MAX_RETRIES_RED (report red, do
                                                      NOT check the item off)
    Never returns ADVANCE on a red verify. That is the whole point.
    """
    if passed:
        return ADVANCE
    if retry < max_retries:
        return RETRY
    return STOP_MAX_RETRIES_RED


def parse_checklist(text: str):
    """Parse a judge checklist. Items are lines like:

        [x] unit 3 — parser rejects empty input      (verified green)
        [ ] unit 4 — CLI prints usage on --help      (not yet verified)
        [!] unit 5 — retry counter caps at 3         (verified RED / failing)

    Returns list of (state, label) where state in {'x','',' ','!'} normalised to
    'done' / 'todo' / 'red'. Non-item lines are ignored.
    """
    items = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) >= 3 and line[0] == "[" and line[2] == "]":
            mark = line[1].lower()
            label = line[3:].strip()
            if mark == "x":
                state = "done"
            elif mark == "!":
                state = "red"
            else:  # space or anything else -> not done
                state = "todo"
            items.append((state, label))
    return items


def grade(items) -> dict:
    """PASS only if every item is 'done' and NONE are 'red'."""
    total = len(items)
    done = sum(1 for s, _ in items if s == "done")
    red = sum(1 for s, _ in items if s == "red")
    todo = sum(1 for s, _ in items if s == "todo")
    verdict = "PASS" if (total > 0 and done == total and red == 0) else "INCOMPLETE"
    return {"total": total, "done": done, "red": red, "todo": todo, "verdict": verdict}


# ---------------------------------------------------------------------------
# clean-verify: run a command against a clean checkout of committed HEAD
# ---------------------------------------------------------------------------

def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True,
    )


def clean_verify(cmd: str, repo: str) -> int:
    """Run `cmd` from a throwaway worktree of committed HEAD. Fail-OPEN.

    Returns the command's exit code. On any git-unsafety, prints a WARN and runs
    `cmd` in the working tree instead (current behavior) rather than blocking.
    """
    repo = os.path.abspath(repo)
    inside = _git(repo, "rev-parse", "--show-toplevel")
    if inside.returncode != 0:
        print("WARN clean-verify: not a git repo — running in place (fail-open).", file=sys.stderr)
        return _run_in(repo, cmd)
    root = inside.stdout.strip()

    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        print("WARN clean-verify: no HEAD commit — running in place (fail-open).", file=sys.stderr)
        return _run_in(root, cmd)
    sha = head.stdout.strip()

    # Warn (do NOT block) if the working tree is dirty: the clean-HEAD run will
    # legitimately NOT see those uncommitted changes. That is the intended
    # guarantee (tests come from committed state), but the caller should know.
    status = _git(root, "status", "--porcelain")
    if status.stdout.strip():
        print("WARN clean-verify: working tree is dirty — clean-HEAD run reflects the "
              "last COMMIT, not uncommitted edits. Commit first if you meant to verify them.",
              file=sys.stderr)

    if shutil.which("git") is None:
        print("WARN clean-verify: git not on PATH — running in place (fail-open).", file=sys.stderr)
        return _run_in(root, cmd)

    tmp = tempfile.mkdtemp(prefix="goal_clean_head_")
    wt = os.path.join(tmp, "wt")
    added = _git(root, "worktree", "add", "--detach", wt, sha)
    if added.returncode != 0:
        print(f"WARN clean-verify: `git worktree add` failed ({added.stderr.strip()}) — "
              "running in place (fail-open).", file=sys.stderr)
        shutil.rmtree(tmp, ignore_errors=True)
        return _run_in(root, cmd)

    print(f"clean-verify: running detectors from clean HEAD {sha[:12]} at {wt}", file=sys.stderr)
    try:
        rc = _run_in(wt, cmd)
    finally:
        _git(root, "worktree", "remove", "--force", wt)
        shutil.rmtree(tmp, ignore_errors=True)
    return rc


def _run_in(cwd: str, cmd: str) -> int:
    proc = subprocess.run(cmd, shell=True, cwd=cwd)
    return proc.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_gate(a) -> int:
    passed = str(a.passed).lower() in ("1", "true", "yes", "pass", "green", "ok")
    verdict = gate(passed, a.retry, a.max)
    print(verdict)
    # exit 0 always: this is advisory bookkeeping, never a blocking gate.
    return 0


def _cmd_grade(a) -> int:
    text = sys.stdin.read() if a.checklist == "-" else open(a.checklist).read()
    items = parse_checklist(text)
    r = grade(items)
    print(f"checklist: {r['done']}/{r['total']} done, {r['red']} red, {r['todo']} todo -> {r['verdict']}")
    return 0 if r["verdict"] == "PASS" else 1


def _cmd_clean_verify(a) -> int:
    return clean_verify(a.cmd, a.repo)


def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and cond

    print("gate() — no-advance-on-red + bounded retry:")
    check("green -> ADVANCE", gate(True, 0, 3) == ADVANCE)
    check("green ignores retry count", gate(True, 9, 3) == ADVANCE)
    check("red retry 0/3 -> RETRY", gate(False, 0, 3) == RETRY)
    check("red retry 2/3 -> RETRY", gate(False, 2, 3) == RETRY)
    check("red retry 3/3 -> STOP (never done on red)", gate(False, 3, 3) == STOP_MAX_RETRIES_RED)
    check("red beyond max -> STOP", gate(False, 5, 3) == STOP_MAX_RETRIES_RED)
    check("red never returns ADVANCE", all(
        gate(False, i, 3) != ADVANCE for i in range(0, 10)))

    print("grade() — checklist grading:")
    all_done = parse_checklist("[x] a\n[x] b\n[x] c")
    check("all done -> PASS", grade(all_done)["verdict"] == "PASS")
    one_open = parse_checklist("[x] a\n[ ] b\n[x] c")
    check("one open -> INCOMPLETE", grade(one_open)["verdict"] == "INCOMPLETE")
    one_red = parse_checklist("[x] a\n[!] b\n[x] c")
    g = grade(one_red)
    check("one red -> INCOMPLETE", g["verdict"] == "INCOMPLETE")
    check("red counted", g["red"] == 1)
    check("empty checklist -> INCOMPLETE (not vacuous PASS)",
          grade(parse_checklist(""))["verdict"] == "INCOMPLETE")
    check("non-item lines ignored",
          len(parse_checklist("UNIT 1: title\n[x] real item\nblah")) == 1)

    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true", help="run pure-function unit tests and exit")
    sub = p.add_subparsers(dest="sub")

    g = sub.add_parser("gate", help="no-advance-on-red decision")
    g.add_argument("--passed", required=True, help="true/false: did independent verify pass?")
    g.add_argument("--retry", type=int, default=0, help="current retry count (0-based)")
    g.add_argument("--max", type=int, default=3, help="max retries (default 3)")
    g.set_defaults(func=_cmd_gate)

    gr = sub.add_parser("grade", help="grade a judge checklist (stdin with -)")
    gr.add_argument("--checklist", default="-", help="checklist file, or - for stdin")
    gr.set_defaults(func=_cmd_grade)

    cv = sub.add_parser("clean-verify", help="run a verify cmd from clean committed HEAD (fail-open)")
    cv.add_argument("--cmd", required=True, help="the verify/detector command to run")
    cv.add_argument("--repo", default=".", help="repo dir (default: cwd)")
    cv.set_defaults(func=_cmd_clean_verify)

    a = p.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not getattr(a, "func", None):
        p.print_help()
        return 0
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
