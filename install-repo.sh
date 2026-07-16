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

# 5. optional deterministic commit gate
if [ ! -f .check-all.json ]; then
  echo "[check-all] no .check-all.json (gate is opt-in). To enable: cp $SRC/templates/check-all.json $REPO/.check-all.json and edit the commands."
fi

echo "done. Add a 'query graphify-out/graph.json first' line to this repo's CLAUDE.md/AGENTS.md so agents use the map."
