#!/usr/bin/env bash
# awesome-harness per-repo setup. Opt-in markers that activate the (otherwise
# dormant) global hooks for one repo: a code-map graph, mulch memory, a north
# star, and graph auto-refresh on commit. Safe to re-run; never overwrites an
# existing .northstar.md or a tracked file.
#
#   ./install-repo.sh /path/to/repo
set -euo pipefail

REPO="${1:-$PWD}"
SRC="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
[ -d .git ] || { echo "not a git repo: $REPO"; exit 1; }
echo "awesome-harness → repo: $REPO"

# 1. graphify code-map + wiki
if command -v graphify >/dev/null 2>&1; then
  if [ ! -f graphify-out/graph.json ]; then
    echo "[graphify] building initial code map (AST-only, no API cost)…"
    nice -n 15 graphify update . || echo "  graphify update failed — check 'graphify --help'"
  else
    echo "[graphify] graph exists; refreshing"; nice -n 15 graphify update . || true
  fi
  grep -qxF "graphify-out/" .gitignore 2>/dev/null || echo "graphify-out/" >> .gitignore
else
  echo "[graphify] not installed — skipping (install: uv tool install graphifyy)"
fi

# 1b. repowise code-intelligence (COMPLEMENTS graphify: git-hotspots/risk, code-health).
# Index-only = no API key, no LLM cost. Niced + non-fatal.
# IMPORTANT: `repowise init` — even with --index-only — auto-wires the repowise MCP
# server + `repowise-augment` agent hooks into GLOBAL Claude config
# (~/.claude/settings.json) and the Claude Desktop config. There is NO documented
# flag to suppress that global wiring (checked `repowise init --help`; --no-claude-md
# / --no-codex / --no-distill-hook do not cover the MCP/augment autowiring). We keep
# repowise STRICTLY opt-in per repo, so we snapshot those two global files before init
# and restore them after — guaranteeing the installer leaves global config untouched.
if command -v repowise >/dev/null 2>&1; then
  echo "[repowise] indexing (AST + git history + graph + dead code; --index-only = no API cost)…"
  _cc_settings="$HOME/.claude/settings.json"
  _cc_desktop="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
  _snap="$(mktemp -d 2>/dev/null || echo "/tmp/repowise-snap.$$")"; mkdir -p "$_snap"
  _had_desktop=0
  [ -f "$_cc_settings" ] && cp "$_cc_settings" "$_snap/settings.json" 2>/dev/null || true
  if [ -f "$_cc_desktop" ]; then _had_desktop=1; cp "$_cc_desktop" "$_snap/desktop.json" 2>/dev/null || true; fi
  # --no-claude-md also protects this repo's existing CLAUDE.md from being clobbered.
  nice -n 15 repowise init --index-only -y --no-claude-md --no-codex --no-distill-hook . || true
  # Revert ANY repowise autowiring init added to global config.
  [ -f "$_snap/settings.json" ] && cp "$_snap/settings.json" "$_cc_settings" 2>/dev/null || true
  if [ "$_had_desktop" = "1" ]; then
    cp "$_snap/desktop.json" "$_cc_desktop" 2>/dev/null || true
  else
    # Desktop config did not exist before; if init created one (repowise-only), drop it.
    [ -f "$_cc_desktop" ] && rm -f "$_cc_desktop" 2>/dev/null || true
  fi
  rm -rf "$_snap" 2>/dev/null || true
  grep -qxF ".repowise/" .gitignore 2>/dev/null || echo ".repowise/" >> .gitignore
  echo "[repowise] index built; global Claude config restored (repowise stays opt-in per repo)"
else
  echo "[repowise] not installed — skipping (install: pip install repowise  — needs Python ≥3.11)"
fi

# 2. graph auto-refresh on commit (non-blocking, niced, locked)
HOOKDIR="$(git rev-parse --git-common-dir)/hooks"; mkdir -p "$HOOKDIR"
if [ -f "$HOOKDIR/post-commit" ]; then
  echo "[hook] post-commit already exists — leaving it (add templates/post-commit manually if you want auto-refresh)"
else
  cp "$SRC/templates/post-commit" "$HOOKDIR/post-commit"; chmod +x "$HOOKDIR/post-commit"
  echo "[hook] installed post-commit graph auto-refresh"
fi

# 3. north star (anti-drift) — never clobber an existing one
if [ -f .northstar.md ]; then
  echo "[northstar] .northstar.md exists — leaving it"
else
  cp "$SRC/templates/northstar.md" .northstar.md
  echo "[northstar] created .northstar.md — EDIT IT: set OBJECTIVE / DONE_WHEN / NOT_NOW"
fi

# 3b. front-door doc (read-first orientation) — never clobber an existing one
if [ -f FRONT_DOOR.md ] || [ -f .planning/FRONT_DOOR.md ]; then
  echo "[front-door] FRONT_DOOR.md exists — leaving it"
else
  cp "$SRC/templates/FRONT_DOOR.md" FRONT_DOOR.md
  echo "[front-door] created FRONT_DOOR.md stub — FILL IT: the one doc a fresh agent reads first (see MEMORY_STANDARD.md)"
fi

# 4. mulch per-repo memory
if command -v ml >/dev/null 2>&1; then
  echo "[mulch] wiring ml prime/sync into this repo's Claude hooks"
  ml setup claude >/dev/null 2>&1 && echo "  ml setup claude done" || echo "  ml setup claude failed (run it manually)"
else
  echo "[mulch] 'ml' not installed — skipping"
fi

# 5. arming markers (route-only + check-all) — ARMED BY DEFAULT, opt-OUT with HARNESS_NO_ARM=1.
# Never clobber an existing marker. route-only makes the repo orchestrate-only
# (blocks direct Write/Edit of source); check-all gates commits on a fast readiness pass.
if [ "${HARNESS_NO_ARM:-}" = "1" ]; then
  echo "[arm] HARNESS_NO_ARM=1 — skipping route-only + check-all arming"
else
  if [ -f .route-only ]; then
    echo "[route-only] .route-only exists — leaving it"
  else
    touch .route-only
    echo "[route-only] armed (orchestrate-only). Disarm: rm $REPO/.route-only"
  fi
  if [ -f .check-all.json ]; then
    echo "[check-all] .check-all.json exists — leaving it"
  else
    printf '%s\n' '{"fast": [], "full": []}' > .check-all.json
    echo "[check-all] armed with a minimal (no-op) gate — edit $REPO/.check-all.json to add fast/full commands"
  fi
fi

echo "done. Add a 'query graphify-out/graph.json first' line to this repo's CLAUDE.md/AGENTS.md so agents use the map."
