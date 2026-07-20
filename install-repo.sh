#!/usr/bin/env bash
# awesome-harness per-repo setup. Opt-in markers that activate the (otherwise
# dormant) global hooks for one repo: a code-map graph, mulch memory, a north
# star, and graph auto-refresh on commit. Safe to re-run; never overwrites an
# existing .northstar.md or a tracked file.
#
#   ./install-repo.sh /path/to/repo
#   ./install-repo.sh --codex [--dry-run] /absolute/path/to/repo
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
CODEX=0; DRY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --codex) CODEX=1; shift ;;
    --dry-run) DRY=1; shift ;;
    *) break ;;
  esac
done

if [ "$CODEX" = 1 ]; then
  [ "$#" = 1 ] || { echo "usage: $0 --codex [--dry-run] /absolute/path/to/repo"; exit 1; }
  case "$1" in /*) REPO="$1" ;; *) echo "Codex install requires an absolute repo path"; exit 1 ;; esac
  REPO="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null)" || { echo "not a git repo: $1"; exit 1; }
  CODEX_DEST="${CODEX_HOME:-$HOME/.codex}/awesome-harness"
  ADAPTER="$CODEX_DEST/hooks/pre_tool_use.py"
  [ -f "$ADAPTER" ] || { echo "Codex adapter is not installed: run ./install.sh --codex first"; exit 1; }
  echo "awesome-harness Codex adapter → repo: $REPO"
  if [ "$DRY" = 1 ]; then
    python3 "$SRC/scripts/merge_codex_hooks.py" --dry-run "$REPO/.codex/hooks.json" "$ADAPTER"
    if [ -e "$REPO/.codex/awesome-harness.json" ]; then
      echo "DRY: workflow marker unchanged: $REPO/.codex/awesome-harness.json"
    else
      echo "DRY: would create workflow-only marker: $REPO/.codex/awesome-harness.json"
    fi
  else
    python3 "$SRC/scripts/merge_codex_hooks.py" "$REPO/.codex/hooks.json" "$ADAPTER"
    if [ ! -e "$REPO/.codex/awesome-harness.json" ]; then
      mkdir -p "$REPO/.codex"
      printf '%s\n' '{' '  "version": 1,' '  "route_only_policy": "workflow-only"' '}' > "$REPO/.codex/awesome-harness.json"
      echo "created workflow-only marker: $REPO/.codex/awesome-harness.json"
    else
      echo "workflow-only marker unchanged: $REPO/.codex/awesome-harness.json"
    fi
  fi
  echo "done. Review the merged hooks in Codex (/hooks), trust this repository, and restart Codex before expecting hooks to run."
  echo "The marker is policy only: it does not role-gate or block native direct patches."
  exit 0
fi

REPO="${1:-$PWD}"
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
