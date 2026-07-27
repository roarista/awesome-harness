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
  warn        -> unset/DEFAULT — inject a model-only nudge, ALLOW. (NOTE: unlike
                 main-edit-guard, which defaults off, this defaults to warn.)
  enforce     -> deny the spawn (exit 2) with the run-codebase-first message
Kill-switch: write `off` to state/understand-gate.mode (overrides env, live, no
restart), or UNDERSTAND_GATE=off. Fail-open on any error.
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

LOG = Path.home() / ".claude" / "hooks" / "state" / "understand-gate.log"

READONLY_RE = re.compile(
    r"^\W*(explain|why|how|review|audit|research|document|find|summarize|summarise|"
    r"read|check|investigate|diagnose|compare|list|trace)\b", re.I)
BUILD_RE = re.compile(
    r"\b(write the code|wire up|fix the bug|"
    r"(refactor|implement|change|update|rename|remove|delete|add|replace|extend|port|make)"
    r" (the|this|a|an) \w|"
    r"(add|extend) [\w ]+ (to|with) \w|"
    r"add (a|the) (feature|module|endpoint|function|hook|script)|"
    r"create (a|the) file)", re.I)
DISCOVERY_RE = re.compile(r"\.scratch/discovery/[\w.-]+\.md")
VERDICT_RE = re.compile(r"(REUSE|ADAPT|REJECT):")

MSG = (
    "UNDERSTAND GATE: this spawn writes code but carries no codebase-first evidence.\n"
    "1. Run the `codebase-first` skill -> produces .scratch/discovery/<slug>.md\n"
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
    if any(READONLY_RE.match(t.strip()) for t in (prompt, desc) if t.strip()):
        return False
    if "codex" in str(ti.get("subagent_type", "") or "").lower():
        return True
    return bool(BUILD_RE.search(f"{prompt}\n{desc}"))


def has_evidence(ti: dict) -> bool:
    prompt = str(ti.get("prompt", "") or "")
    return bool(DISCOVERY_RE.search(prompt) or VERDICT_RE.search(prompt))


def _mode() -> str:
    # Control file overrides env so the mode can flip LIVE, mid-session, across
    # every running session without a restart (hooks spawn per tool call → fresh read).
    f = Path.home() / ".claude" / "hooks" / "state" / "understand-gate.mode"
    try:
        v = f.read_text().strip().lower()
        if v in ("off", "log", "warn", "enforce"):
            return v
    except Exception:
        pass
    return os.environ.get("UNDERSTAND_GATE", "warn").lower() or "warn"


def main() -> None:
    mode = _mode()
    if mode == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
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
    _hookout.inject("PreToolUse", MSG)  # warn (default)


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
    assert is_build_intent({"subagent_type": "codex", "prompt": "look around"})
    assert not is_build_intent({"subagent_type": "codex:codex-rescue",
                                "prompt": "investigate why tests are slow, "
                                          "do not change anything"})
    assert not has_evidence({"prompt": "implement the retry logic"})
    assert has_evidence({"prompt": "implement retry per .scratch/discovery/retry.md"})
    assert has_evidence({"prompt": "REJECT: no existing helper"})
    print("PASS")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
