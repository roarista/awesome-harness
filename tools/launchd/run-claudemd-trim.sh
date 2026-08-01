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

echo "run-claudemd-trim: dispatched $TRIM to Terminal.app at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
