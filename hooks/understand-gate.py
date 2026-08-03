#!/usr/bin/env python3
"""PreToolUse(Task) — make the UNDERSTAND step (THE PROCEDURE steps 2-3) actually
RUN before a code-writing subagent is spawned. coding-routing-guard.sh only ADVISES
on every Task spawn; this is the enforcing counterpart: it fires only on build-intent
spawns and asks for a codebase-first evidence pointer (a `.scratch/discovery/<slug>.md`
path, or an inline REUSE:/ADAPT:/REJECT: verdict) IN THE SPAWN ITSELF.

Build intent = the prompt/description does NOT open with a read-only verb
(explain/why/review/audit/...) AND matches a verb-OBJECT mutation phrase
("refactor the X", "change the X", "add a feature", ...). Bare verbs alone
("build", "patch", "migrate") never trip it — research prompts talk about builds too.

Modes via env UNDERSTAND_GATE:
  off         -> no-op
  log         -> append the spawn to state/understand-gate.log, ALLOW (observe)
  warn        -> GLOBAL DEFAULT — inject a model-only nudge, ALLOW.
  enforce     -> deny the spawn (exit 2) with the run-codebase-first message.

Precedence (highest first): control file > env > repo marker > default warn.
Enforcement is OPT-IN PER REPO, exactly like hooks/check-all-commit-gate.sh's
`.check-all.json`: if a `.understand-gate` marker file exists at/above the target
repo, the effective mode becomes `enforce` there. Global enforce-by-default was tried
and reverted — it exit-2'd read-only investigation spawns (`Task(subagent_type=
"codex", prompt="Look at X and tell me why semgrep flags it")`), wedging the session.
Kill-switch: write `off` to state/understand-gate.mode (overrides env AND marker,
live, no restart), or UNDERSTAND_GATE=off. Fail-open on any error.
Honest limits: this checks for an evidence POINTER only — it cannot judge whether the
discovery is relevant, honest, or correct (that stays behavioral and audit-backed).
The pointer must be per-spawn: a fresh discovery file lying around the repo is NOT
evidence (that would be a repo-wide bypass proving only that a tool was once run).
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

# Overridable so --selftest can never touch the LIVE mode file (a crash mid-test
# used to leave every concurrent session with the gate disabled).
STATE_DIR = Path(os.environ.get("HOOK_STATE_DIR",
                                str(Path.home() / ".claude" / "hooks" / "state")))
LOG = STATE_DIR / "understand-gate.log"
MARKER = ".understand-gate"          # repo opt-in, mirrors .check-all.json

# Read-only intent. Matched anywhere in the FIRST LINE, not just at position 0: real
# investigation prompts open with "Look at X and tell me why semgrep flags it".
READONLY_RE = re.compile(
    r"\b(explain|why|how|review|audit|research|document|find|summarize|summarise|"
    r"read|check|investigate|diagnose|compare|list|trace|look|inspect|analyz|analys|"
    r"verify|confirm|assess|evaluate|map|identify|search|grep|you are)\b", re.I)
BUILD_RE = re.compile(
    r"\b(write the code|wire up|fix the bug|"
    r"(refactor|implement|change|update|rename|remove|delete|add|replace|extend|port|make)"
    r" (the|this|a|an) \w|"
    r"(add|extend) [\w ]+ (to|with) \w|"
    r"add (a|the) (feature|module|endpoint|function|hook|script)|"
    r"create (a|the) file)", re.I)
DISCOVERY_RE = re.compile(r"\.scratch/discovery/[\w.-]+\.md")
VERDICT_RE = re.compile(r"(REUSE|ADAPT|REJECT):")
# orient skill (merged recall+codebase-first) exit artifact: an ORIENT block
# headed by a GATE: STOP|PLAN|BUILD line counts as evidence too.
ORIENT_RE = re.compile(r"^ORIENT\b|GATE:\s*(STOP|PLAN|BUILD)", re.I | re.M)

MSG = (
    "UNDERSTAND GATE: this spawn writes code but carries no codebase-first evidence.\n"
    "1. Run the `orient` skill -> produces .scratch/discovery/<slug>.md\n"
    "2. Pass that path in the subagent prompt, OR an inline REUSE:/ADAPT:/REJECT: verdict.\n"
    "STOP (no new code) is a valid outcome.\n"
    "Kill: UNDERSTAND_GATE=off, or write `off` to "
    "~/.claude/hooks/state/understand-gate.mode\n"
)


def is_build_intent(ti: dict) -> bool:
    prompt = str(ti.get("prompt", "") or "")
    desc = str(ti.get("description", "") or "")
    # Read-only opener wins outright: research prompts discuss builds, patches, refactors
    # (and codex:codex-rescue is an investigation agent as much as a coding one).
    # Scoped to the FIRST line only: a build prompt routinely says "verify" or "check"
    # further down ("add the flag, then verify tests pass") and must not be exempted.
    if any(READONLY_RE.search(t.strip().splitlines()[0][:200])
           for t in (prompt, desc) if t.strip()):
        return False
    if "codex" in str(ti.get("subagent_type", "") or "").lower():
        return True
    return bool(BUILD_RE.search(f"{prompt}\n{desc}"))


def has_evidence(ti: dict) -> bool:
    prompt = str(ti.get("prompt", "") or "")
    return bool(DISCOVERY_RE.search(prompt) or VERDICT_RE.search(prompt) or ORIENT_RE.search(prompt))


def _marked(start: Path) -> bool:
    """True if a `.understand-gate` marker exists at or above `start` (repo opt-in)."""
    try:
        start = start.resolve()
    except Exception:
        return False
    return any((d / MARKER).exists() for d in [start, *start.parents])


def _mode(cwd: str = ".") -> str:
    # Control file overrides env so the mode can flip LIVE, mid-session, across
    # every running session without a restart (hooks spawn per tool call → fresh read).
    f = STATE_DIR / "understand-gate.mode"
    try:
        v = f.read_text().strip().lower()
        if v in ("off", "log", "warn", "enforce"):
            return v
    except Exception:
        pass
    env = os.environ.get("UNDERSTAND_GATE", "").strip().lower()
    if env in ("off", "log", "warn", "enforce"):
        return env
    return "enforce" if _marked(Path(cwd or ".")) else "warn"


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    mode = _mode(str(data.get("cwd", "") or os.getcwd()))
    if mode == "off":
        return
    ti = data.get("tool_input", {}) or {}
    if not is_build_intent(ti) or has_evidence(ti):
        return  # silent pass

    if mode == "log":
        try:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a") as f:
                f.write(f"{datetime.now().isoformat()}\t{ti.get('subagent_type','')}\t"
                        f"{str(ti.get('description','') or '')[:80]}\n")
        except Exception:
            pass
        return
    if mode == "enforce":
        sys.stderr.write(MSG)
        sys.exit(2)
    _hookout.inject("PreToolUse", MSG)  # warn


def _selftest() -> None:
    for p in ("explain the build system",
              "why did the build fail",
              "review the patch in PR 12",
              "document how we migrate schemas",
              "audit the refactor codex just did",
              "read the edit history",
              "find where we build the config dict",
              "research build tools",
              "check if we implement caching anywhere"):
        assert not is_build_intent({"prompt": p}), p
        assert not is_build_intent({"description": p}), p
    for p in ("change the timeout to 30s",
              "make the function return X",
              "remove the retry loop",
              "rename the module",
              "update the parser",
              "add error handling to run()",
              "port this to python 3.12",
              "extend the CLI with a --json flag",
              "implement the retry logic"):
        assert is_build_intent({"prompt": p}), p
    # a codex spawn is build-intent by default, but a read-only opener still wins
    assert is_build_intent({"subagent_type": "codex", "prompt": "make the retry loop async"})
    assert not is_build_intent({"subagent_type": "codex", "prompt": "look around"})
    # a "verify" LATER in a build prompt must not exempt it
    assert is_build_intent({"prompt": "add the retry helper\nthen verify tests pass"})
    assert not is_build_intent({"subagent_type": "codex:codex-rescue",
                                "prompt": "investigate why tests are slow, "
                                          "do not change anything"})
    assert not has_evidence({"prompt": "implement the retry logic"})
    assert has_evidence({"prompt": "implement retry per .scratch/discovery/retry.md"})
    assert has_evidence({"prompt": "REJECT: no existing helper"})

    # read-only openers the old ^-anchored regex missed
    for p in ("Look at tools/goal/goal_judge.py and tell me why semgrep flags it",
              "Inspect the retry loop and report",
              "You are auditing the parser; change nothing",
              "Verify the timeout is 30s",
              "Map the module graph"):
        assert not is_build_intent({"subagent_type": "codex", "prompt": p}), p

    # mode resolution: default warn, marker -> enforce, env + control file override.
    # NB: runs entirely inside a tempdir — the LIVE understand-gate.mode is never
    # touched, so a crash here cannot disable the gate for other sessions.
    import tempfile
    global STATE_DIR
    live = STATE_DIR
    with tempfile.TemporaryDirectory() as td:
        STATE_DIR = Path(td) / "state"
        STATE_DIR.mkdir()
        mf = STATE_DIR / "understand-gate.mode"
        unmarked = Path(td) / "plain"
        marked = Path(td) / "marked"
        unmarked.mkdir()
        marked.mkdir()
        (marked / MARKER).write_text("")
        try:
            os.environ.pop("UNDERSTAND_GATE", None)
            assert _mode(str(unmarked)) == "warn", _mode(str(unmarked))
            assert _mode(str(marked)) == "enforce", _mode(str(marked))
            os.environ["UNDERSTAND_GATE"] = "log"       # env beats marker
            assert _mode(str(marked)) == "log", _mode(str(marked))
            os.environ["UNDERSTAND_GATE"] = ""          # empty env -> ignored
            assert _mode(str(marked)) == "enforce", _mode(str(marked))
            del os.environ["UNDERSTAND_GATE"]
            mf.write_text("off\n")                      # control file beats everything
            assert _mode(str(marked)) == "off", _mode(str(marked))
            os.environ["UNDERSTAND_GATE"] = "enforce"
            assert _mode(str(marked)) == "off", _mode(str(marked))
        finally:
            os.environ.pop("UNDERSTAND_GATE", None)
            STATE_DIR = live
    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
