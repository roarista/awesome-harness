#!/bin/bash
# open-findings.sh — after a propose-only auditor finishes, open a NEW macOS
# Terminal window running an interactive Claude Code session with the fresh
# report already loaded, so Ro can implement the findings he picks.
#
# usage: tools/open-findings.sh <report-path> [repo-dir]
# env:   OPEN_FINDINGS=0          kill-switch (scheduled jobs can silence it)
#        OPEN_FINDINGS_DRYRUN=1   print the osascript command instead of running it
#
# ALWAYS exits 0 — it must never take down the auditor job that calls it.
# --dangerously-skip-permissions is deliberate (Ro's own machine): the spawned
# session can run any tool / edit / command without asking.

set -u

REPORT="${1:-}"
REPO="${2:-$HOME/Downloads/awesome-harness}"

[ "${OPEN_FINDINGS:-1}" = "0" ] && { echo "open-findings: disabled (OPEN_FINDINGS=0)"; exit 0; }
[ -n "$REPORT" ] && [ -f "$REPORT" ] || { echo "open-findings: no report at '${REPORT}' — skipping"; exit 0; }
command -v osascript >/dev/null 2>&1 || { echo "open-findings: no osascript — skipping"; exit 0; }

# shell-quote: wrap in single quotes, escaping embedded single quotes
q() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

# `claude` is only a zsh FUNCTION in ~/.zshrc — a `do script` shell that is not an
# interactive login zsh would never find it. Resolve a real binary path instead, and
# fall back to the bare name only if nothing is found.
CLAUDE_BIN=""
for c in "$HOME/.npm-global/bin/claude" "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
  [ -x "$c" ] && { CLAUDE_BIN="$c"; break; }
done
[ -n "$CLAUDE_BIN" ] || CLAUDE_BIN="$(command -v claude 2>/dev/null || echo claude)"

PROMPT="Read the propose-only auditor report at $REPORT. Summarize its findings as a numbered list, shortest-first. Change NOTHING until I pick which ones to implement; then implement only those."
# Trailing `exec $SHELL -l` guarantees the window STAYS OPEN even if claude exits
# immediately — otherwise Terminal can close the tab and it looks like nothing happened.
CMD="cd $(q "$REPO") && $(q "$CLAUDE_BIN") --dangerously-skip-permissions $(q "$PROMPT"); exec \$SHELL -l"

# AppleScript string literal: escape backslashes first, then double quotes.
AS_CMD=$(printf '%s' "$CMD" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
SCRIPT="tell application \"Terminal\"
	activate
	do script \"$AS_CMD\"
end tell"

if [ "${OPEN_FINDINGS_DRYRUN:-0}" = "1" ]; then
  printf 'osascript -e %s\n' "$(q "$SCRIPT")"
  exit 0
fi

# GUI session check: launchctl managername is "Aqua" only in a real login session.
[ "$(launchctl managername 2>/dev/null)" = "Aqua" ] || { echo "open-findings: not a GUI session — skipping"; exit 0; }

# NEVER swallow osascript's stderr: a TCC "Automation" denial (-1743) or a syntax
# error must land in the caller's log. Still always exit 0 — this must never take
# down the auditor job.
ERR=$(osascript -e "$SCRIPT" 2>&1) ; RC=$?
if [ "$RC" -ne 0 ]; then
  echo "open-findings: osascript FAILED (rc=$RC) — non-fatal, continuing"
  echo "open-findings: osascript said: ${ERR}"
  case "$ERR" in
    *-1743*|*"Not authorized to send Apple events"*)
      echo "open-findings: FIX = System Settings > Privacy & Security > Automation > (bash / Terminal) > enable 'Terminal'" ;;
  esac
else
  echo "open-findings: opened Terminal (${ERR:-no window id reported}) with $REPORT"
fi
exit 0
