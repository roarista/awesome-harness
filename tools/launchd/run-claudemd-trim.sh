#!/bin/bash
# run-claudemd-trim.sh — launchd shim for the weekly CLAUDE.md trimmer.
#
# WHY THIS EXISTS (macOS TCC):
#   ~/.claude/tools/claudemd-trim.py reads CLAUDE.md out of repos under ~/Downloads.
#   ~/Downloads is a TCC-protected folder. A launchd agent inherits NO TCC grant, so
#   running the trimmer directly from launchd dies with:
#       PermissionError: [Errno 1] Operation not permitted: '/Users/.../Downloads/...'
#   The documented fix — Full Disk Access for /usr/bin/python3 — is unusable in
#   practice: /usr/bin is hidden in the Finder picker, so the grant cannot be added.
#
#   WORKAROUND: Terminal.app ALREADY holds the needed grant. So launchd never touches a
#   protected path itself; it just asks Terminal (via osascript) to run the trimmer.
#   The real work executes inside Terminal, under Terminal's existing TCC grant — and
#   as a bonus Ro gets to watch the weekly run happen in a visible window.

set -uo pipefail

TRIM="$HOME/.claude/tools/claudemd-trim.py"
REPORT_DIR="$HOME/engineering-harness/reports/claudemd-trim"

# Only meaningful in a GUI (Aqua) session — there is no Terminal.app to drive otherwise.
if [ "$(launchctl managername 2>/dev/null)" != "Aqua" ]; then
    echo "run-claudemd-trim: not an Aqua session; skipping (no GUI Terminal to borrow)." >&2
    exit 0
fi

if [ ! -r "$TRIM" ]; then
    echo "run-claudemd-trim: trimmer not readable at $TRIM" >&2
    exit 1
fi

if ! command -v osascript >/dev/null 2>&1; then
    echo "run-claudemd-trim: osascript not found; cannot dispatch to Terminal." >&2
    exit 1
fi

# Record the newest existing report's mtime before dispatch, so we can detect a
# genuinely NEW report after — same-day re-runs reuse the same filename, so
# comparing names alone would miss a real rewrite. 0 if the dir is empty/absent.
BEFORE_MTIME="$(stat -f %m "$REPORT_DIR"/* 2>/dev/null | sort -rn | head -n1)"
BEFORE_MTIME="${BEFORE_MTIME:-0}"

# The path is passed as an ARGUMENT (argv), never interpolated into AppleScript source.
osascript - "$TRIM" <<'APPLESCRIPT'
on run argv
    tell application "Terminal"
        activate
        do script ("/usr/bin/python3 " & quoted form of (item 1 of argv))
    end tell
end run
APPLESCRIPT

if [ $? -ne 0 ]; then
    echo "run-claudemd-trim: osascript dispatch to Terminal failed." >&2
    exit 1
fi

DISPATCH_TS="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "run-claudemd-trim: dispatched $TRIM to Terminal.app at $DISPATCH_TS"

# Verify the dispatch actually produced a report; launchd must not see exit 0 on a no-op.
elapsed=0
while [ "$elapsed" -lt 900 ]; do
    NOW_MTIME="$(stat -f %m "$REPORT_DIR"/* 2>/dev/null | sort -rn | head -n1)"
    NOW_MTIME="${NOW_MTIME:-0}"
    if [ "$NOW_MTIME" -gt "$BEFORE_MTIME" ]; then
        NOW_NEWEST="$(ls -t "$REPORT_DIR" 2>/dev/null | head -n1)"
        echo "run-claudemd-trim: new report: $NOW_NEWEST"
        exit 0
    fi
    sleep 30
    elapsed=$((elapsed + 30))
done

echo "run-claudemd-trim: no new report in $REPORT_DIR within 15m of dispatch at $DISPATCH_TS" >&2
exit 1
