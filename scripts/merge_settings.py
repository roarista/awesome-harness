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
HOOKS = {  # == registered set after 2026-10-03 hook-circumvention + U10 hook-impact
    "SessionStart":     [# full north star once per session (also fires after /compact)
                         ("", f'python3 "{HOOK}/northstar-inject.py"'),
                         # /clear handoff: inject .planning/CONTINUE.md written by compact-prep
                         ("clear", f'python3 "{HOOK}/clear-resume.py"')],
    "UserPromptSubmit": [# per prompt: the NOW line only (<=300 B)
                         ("", f'python3 "{HOOK}/northstar-inject.py"')],
    "PreToolUse":       [("Skill", f'python3 "{HOOK}/skill-reinject-guard.py"'),
                         # anti-drift: the north star is read-only to the agent
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/northstar-protect.py"'),
                         ("Bash", f'python3 "{HOOK}/northstar-protect.py"'),
                         # hard stop on irreversible ops; scratch/build deletes pass
                         ("Bash", f'python3 "{HOOK}/irreversible-pause.py"'),
                         # code-map: advise before editing a file with unread callers (no-op without graphify)
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/graphify-blindspot.py"'),
                         # token-save: advise against slurping a very large file whole
                         ("Read", f'python3 "{HOOK}/filesize-cap.py"'),
                         # keep .now.md tiny — advisory only
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/now-gate.py"'),
                         # route-only: main session only, opt-in per repo (.route-only marker)
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/route-only-gate.py"')],
    "PostToolUse":      [("", f'python3 "{HOOK}/harness-usage-telemetry.py"'),
                         # soft re-scope nudge when a session looks abnormal (deep / errors / looping)
                         ("", f'python3 "{HOOK}/session-checkpoint.py"'),
                         ("Read", f'python3 "{HOOK}/graphify-blindspot.py"'),
                         # one-line nudge when an edited source file is over 200 lines (never blocks)
                         ("Write|Edit|MultiEdit", f'python3 "{HOOK}/size-nudge.py"'),
                         # token discipline: warn on the 3rd full re-read of the same file
                         ("Read", f'python3 "{HOOK}/token-discipline.py"')],
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


# unregistered 2026-10-03 (hooks/retired/README.md); stripped from existing installs
RETIRED = ("bash-write-fence", "compact-prep-gate", "graphify-gate", "claude-spawn-gate",
           "coding-routing-guard", "harness-enforce", "caveman-discipline", "post-agent-guard",
           "abs-path-nudge",
           # U10 (.artifacts/agent-reports/hook-impact-2026-10-03.md DELETE verdicts)
           "recall-inject", "manifest-guard", "codemap-inject", "reread-guard")


def drop_retired(settings):
    n = 0
    for event, arr in settings.get("hooks", {}).items():
        for e in arr:
            keep = [h for h in e.get("hooks", [])
                    if not any(f"/{r}." in h.get("command", "") for r in RETIRED)]
            n += len(e.get("hooks", [])) - len(keep)
            e["hooks"] = keep
        arr[:] = [e for e in arr if e.get("hooks")]
    return n


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
    removed = drop_retired(settings)
    for event, items in HOOKS.items():
        for matcher, cmd in items:
            if ensure_hook(settings, event, matcher, cmd):
                added += 1

    # validate by round-tripping before writing
    text = json.dumps(settings, indent=2)
    json.loads(text)
    path.write_text(text + "\n")
    print(f"  merged {added} new entries, removed {removed} retired (idempotent).")


if __name__ == "__main__":
    main()
