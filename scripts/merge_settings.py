#!/usr/bin/env python3
"""Idempotently merge awesome-harness wiring into ~/.claude/settings.json.

Backs up the existing file first, only ADDS our hook commands / env vars when
absent (never clobbers the user's own config or duplicates on re-run), and
validates the result is still valid JSON before writing. ANTHROPIC_BASE_URL is
intentionally NOT added here — the proxy is opt-in (see install.sh --proxy).
"""
import json
import shutil
import sys
import time
from pathlib import Path

HOOK = "$HOME/.claude/hooks"

# env defaults we add only if the key is missing
ENV_DEFAULTS = {
    "ENABLE_TOOL_SEARCH": "true",
    "PONYTAIL_DEFAULT_MODE": "full",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60",
}

# event -> list of (matcher, command). matcher "" means all.
HOOKS = {
    "SessionStart":     [("", f'sh "{HOOK}/caveman-discipline.sh"'),
                         # reset the re-read guard's read-set (compact-safety valve)
                         ("", f'python3 "{HOOK}/reread-guard.py"')],
    "UserPromptSubmit": [("", f'python3 "{HOOK}/recall-inject.py"'),
                         ("", f'python3 "{HOOK}/northstar-inject.py"'),
                         # anti-decay: rotating re-assertion of ponytail/graphify/
                         # mulch/caveman so they don't get skimmed away by turn ~20
                         ("", f'python3 "{HOOK}/harness-enforce.py"')],
    "PreToolUse":       [("Task", f'sh "{HOOK}/coding-routing-guard.sh"'),
                         # anti-drift: the north star is read-only to the agent
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/northstar-protect.py"'),
                         ("Bash", f'python3 "{HOOK}/northstar-protect.py"'),
                         # anti-drift: hard stop on irreversible ops (rm -rf / force-push / destructive SQL)
                         ("Bash", f'python3 "{HOOK}/irreversible-pause.py"'),
                         # code-map: advise before editing a file with unread callers (no-op without graphify)
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/graphify-blindspot.py"'),
                         # code-map ENFORCED: DENY cold source Read/Grep until graphify has run once this session
                         ("Read", f'python3 "{HOOK}/graphify-gate.py"'),
                         ("Grep", f'python3 "{HOOK}/graphify-gate.py"'),
                         # token-save: block a full re-read of an unchanged large file already read this stretch
                         ("Read", f'python3 "{HOOK}/reread-guard.py"'),
                         # keep .now.md tiny (injector truncates at 800 chars) — advisory only
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/now-gate.py"')],
    "PostToolUse":      [("Read", f'python3 "{HOOK}/graphify-blindspot.py"'),
                         # token-save: record full reads so the PreToolUse guard can dedup them
                         ("Read", f'python3 "{HOOK}/reread-guard.py"'),
                         # code-map ENFORCED: mark the session "graphified" once a graphify command runs
                         ("Bash", f'python3 "{HOOK}/graphify-gate.py"'),
                         # soft re-scope nudge when a session looks abnormal (deep / errors / looping)
                         ("", f'python3 "{HOOK}/session-checkpoint.py"'),
                         # token discipline: warn on the 3rd full re-read of the same file
                         ("Read", f'python3 "{HOOK}/token-discipline.py"')],
    "Stop":             [# compact-prep ENFORCED: block turn-end until .now.md/STATE refreshed (rate-limited)
                         ("", f'python3 "{HOOK}/compact-prep-gate.py"')],
    "PreCompact":       [("", f'bash "{HOOK}/pre_compact_global.sh"'),
                         # context-preservation: cheap model writes a 7-field handoff before compaction
                         ("", f'python3 "{HOOK}/precompact-handoff.py"')],
}


def _commands(entries):
    out = []
    for e in entries or []:
        for h in e.get("hooks", []):
            if h.get("command"):
                out.append(h["command"])
    return out


def ensure_hook(settings, event, matcher, command):
    arr = settings.setdefault("hooks", {}).setdefault(event, [])
    # dedupe PER MATCHER — the same command may legitimately live on two
    # different matchers (e.g. northstar-protect on Write|Edit|MultiEdit AND on
    # Bash). Idempotent: re-running never duplicates within a matcher.
    for e in arr:
        if e.get("matcher", "") == matcher:
            if command in _commands([e]):
                return False  # already present under this matcher
            e.setdefault("hooks", []).append({"type": "command", "command": command})
            return True
    arr.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})
    return True


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude" / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    settings = {}
    if path.exists() and path.stat().st_size:
        try:
            settings = json.loads(path.read_text())
        except Exception as e:
            print(f"  refusing to merge — existing settings.json is not valid JSON: {e}")
            sys.exit(1)
        bak = path.with_suffix(f".json.bak.{int(time.time())}")
        shutil.copy2(path, bak)
        print(f"  backed up existing settings → {bak.name}")

    added = 0
    env = settings.setdefault("env", {})
    for k, v in ENV_DEFAULTS.items():
        if k not in env:
            env[k] = v
            added += 1
    for event, items in HOOKS.items():
        for matcher, cmd in items:
            if ensure_hook(settings, event, matcher, cmd):
                added += 1

    # validate by round-tripping before writing
    text = json.dumps(settings, indent=2)
    json.loads(text)
    path.write_text(text + "\n")
    print(f"  merged {added} new entries (idempotent; re-running adds nothing).")


if __name__ == "__main__":
    main()
