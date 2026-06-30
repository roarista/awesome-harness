#!/usr/bin/env bash
# claude-harness global installer.
# Copies hooks/skills/tools into ~/.claude and idempotently merges the hook +
# env wiring into ~/.claude/settings.json (with a timestamped backup first).
# Safe to re-run. Nothing is published anywhere; everything stays on your machine.
#
#   ./install.sh            # install + wire settings.json
#   ./install.sh --proxy    # also install + load the local token-saving proxy (macOS launchd)
#   ./install.sh --dry-run  # show what would change, touch nothing
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude"
DRY=0; PROXY=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --proxy)   PROXY=1 ;;
    *) echo "unknown flag: $a"; exit 1 ;;
  esac
done

say(){ printf '  %s\n' "$*"; }
run(){ if [ "$DRY" = 1 ]; then echo "DRY: $*"; else eval "$*"; fi; }

echo "claude-harness → $DEST"

# ---- 1. dependency check (warn, don't fail) -------------------------------
echo "[1/4] checking dependencies"
need(){ command -v "$1" >/dev/null 2>&1 && say "found $1" || say "MISSING $1 — $2"; }
need python3 "required for memgraph + several hooks"
need git     "required for graphify auto-refresh"
need graphify "code-map RAG — install: uv tool install graphifyy   (https://github.com/…/graphify)"
need ml      "mulch per-repo memory — install: npm i -g @mulch/cli (needs ~/.bun/bin on PATH)"
need node    "needed by the ponytail plugin + some hooks"

# ---- 2. copy harness files ------------------------------------------------
echo "[2/4] copying hooks, skills, tools"
run "mkdir -p '$DEST/hooks' '$DEST/skills' '$DEST/tools' '$DEST/scaffolds'"
run "cp -R '$SRC/hooks/.' '$DEST/hooks/'"
run "cp -R '$SRC/skills/.' '$DEST/skills/'"
run "cp -R '$SRC/tools/.' '$DEST/tools/'"
run "cp '$SRC/ctxproxy.py' '$DEST/tools/ctxproxy.py'"
run "cp '$SRC/BUILDER_STANDARD.md' '$DEST/BUILDER_STANDARD.md'"
run "chmod +x '$DEST'/hooks/*.sh '$DEST'/hooks/*.py '$DEST'/tools/*.sh '$DEST'/tools/*.py '$DEST'/tools/check-all/*.sh 2>/dev/null || true"
[ -f "$DEST/tools/memgraph/sources.txt" ] || run "cp '$SRC/templates/memgraph-sources.txt' '$DEST/tools/memgraph/sources.txt'"

# ---- 3. merge settings.json (backup + idempotent + validate) --------------
echo "[3/4] wiring ~/.claude/settings.json"
if [ "$DRY" = 1 ]; then
  echo "DRY: would merge harness hooks + env into $DEST/settings.json (backup first)"
else
  python3 "$SRC/scripts/merge_settings.py" "$DEST/settings.json"
fi

# ---- 4. optional local proxy (macOS) --------------------------------------
echo "[4/4] local token-saving proxy"
if [ "$PROXY" = 1 ]; then
  if [ "$(uname)" != "Darwin" ]; then
    say "proxy auto-load is macOS/launchd only; on Linux run: python3 $DEST/tools/ctxproxy.py serve  (and set ANTHROPIC_BASE_URL=http://127.0.0.1:8788)"
  else
    PL="$HOME/Library/LaunchAgents/com.claudeharness.ctxproxy.plist"
    run "sed 's#__HOME__#$HOME#g' '$SRC/templates/com.claudeharness.ctxproxy.plist' > '$PL'"
    run "launchctl unload '$PL' 2>/dev/null || true"
    run "launchctl load '$PL'"
    say "proxy loaded. To route through it, add to settings.json env: \"ANTHROPIC_BASE_URL\": \"http://127.0.0.1:8788\" (NEW sessions only)."
    say "It is local + lossless (strips terminal ANSI from non-Read tool results), fail-open. Disable: launchctl unload '$PL'."
  fi
else
  say "skipped (run with --proxy to enable). It only ever talks to api.anthropic.com; data stays on your machine."
fi

echo "done. Restart Claude Code (env + tool-search load at process start). Then: ./install-repo.sh /path/to/your/repo"
