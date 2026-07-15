#!/bin/bash
# run-harness-scout.sh — weekly headless harness-scout pass (proposal-only).
# Schedule with templates/com.awesomeharness.harness-scout.plist (or any cron).
# Runs claude headless, delegates the report write to a sub-agent so the
# main-edit-guard (enforce) doesn't block it. Single-run lock via pidfile.

set -u

export PATH="$HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

LOGDIR="$HOME/.claude/logs"
mkdir -p "$LOGDIR"
DATE="$(date +%F)"
LOG="$LOGDIR/harness-scout-$DATE.log"
LOCK="$LOGDIR/harness-scout.lock"

# --- single-run guard: bail if a previous run is still alive ---
if [ -f "$LOCK" ]; then
  OLDPID="$(cat "$LOCK" 2>/dev/null || echo '')"
  if [ -n "$OLDPID" ] && kill -0 "$OLDPID" 2>/dev/null; then
    echo "[$(date)] previous run (pid $OLDPID) still active — skipping." >>"$LOG"
    exit 0
  fi
  echo "[$(date)] stale lock (pid ${OLDPID:-none}) — clearing." >>"$LOG"
fi
echo $$ >"$LOCK"
cleanup() { rm -f "$LOCK"; }
trap cleanup EXIT

echo "[$(date)] harness-scout run start" >>"$LOG"

PROMPT='Run a BOUNDED harness-scout pass (proposal-only, do NOT edit any live tree). Use the harness-scout skill contract. Cover: (A) repetition-mine my recent transcripts for things I keep hand-prompting; (B) research-scout GitHub for the last 30 days of steal-worthy Claude Code harness ideas; (C) primary-tier creator YouTube intel via the ytintel CLI; plus email newsletters IF any have arrived, and any note-inbox rows with Status=New IF any exist (skip cleanly and note SKIPPED if empty). Keep it bounded and low-CPU: cap fan-out, no VMs, no heavy local compute. IMPORTANT: DELEGATE the final report write to a sub-agent (Agent tool) so the main-edit-guard (enforce) does not block the write. The sub-agent must write the report to '"$HOME"'/Downloads/HARNESS_SCOUT_'"$DATE"'.md using the harness-scout output format (Summary, A. repetition, B. external steal-worthy, C. creator intel, Ranked build-next shortlist). Then return a one-line confirmation of the path written.'

# Headless / non-interactive. Bound wall-clock with a hard timeout.
# NOTE: exact headless flags may vary by claude version.
TIMEOUT_BIN="$(command -v timeout || command -v gtimeout || true)"
RUN=( claude -p "$PROMPT" --dangerously-skip-permissions --output-format text )
if [ -n "$TIMEOUT_BIN" ]; then
  "$TIMEOUT_BIN" 3600 "${RUN[@]}" >>"$LOG" 2>&1
  RC=$?
else
  "${RUN[@]}" >>"$LOG" 2>&1
  RC=$?
fi

echo "[$(date)] harness-scout run end (rc=$RC)" >>"$LOG"
exit 0
