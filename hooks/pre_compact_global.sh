#!/usr/bin/env bash
# ~/.claude/hooks/pre_compact_global.sh
#
# Global mechanical safety net before /compact. Runs in EVERY project.
# Pairs with the /compact-prep skill (LLM-driven prep).
#
# What this hook does (no LLM, just shell):
#   1. Snapshot branch + HEAD + dirty files
#   2. If .mulch/ is dirty AND `ml` CLI is available → run `ml sync`
#   3. Auto-commit ONLY tracked session-metadata MD files (.planning/STATE.md, etc.)
#      Source code, tests, migrations are NEVER auto-committed.
#   4. If on a feature branch with upstream and ahead of upstream → git push
#   5. Write .planning/COMPACT_HANDOFF.md with branch/HEAD/recent commits/dirty list
#   6. Emit a "resume hint" line that becomes part of post-compact context
#
# Output goes to the conversation as a SessionStart:compact reminder, so
# everything echoed here is visible to the post-compact Claude.

set -u

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || { echo "Pre-compact: cwd unreachable, skipping."; exit 0; }

echo "=== GLOBAL_PRE_COMPACT ==="
echo "Project: $ROOT"
echo "Time: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Not a git repo — only conversation context will be summarized."
  echo "=== GLOBAL_PRE_COMPACT_DONE ==="
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
echo "Branch: $BRANCH"
echo "HEAD: $HEAD_SHA"

emit_markdown_section() {
  file="$1"
  heading="$2"
  max_lines="${3:-80}"
  [ -f "$file" ] || return 0
  awk -v heading="$heading" -v max_lines="$max_lines" '
    $0 == heading { printing=1; count=0; next }
    printing && /^## / { exit }
    printing && count < max_lines { print; count++ }
  ' "$file"
}

emit_file_head() {
  file="$1"
  max_lines="${2:-160}"
  [ -f "$file" ] || return 0
  sed -n "1,${max_lines}p" "$file"
}

emit_load_bearing_context() {
  context_printed=0

  if [ -f "$ROOT/.planning/COMPACT_CONTEXT.md" ]; then
    echo "### .planning/COMPACT_CONTEXT.md"
    emit_file_head "$ROOT/.planning/COMPACT_CONTEXT.md" 180
    context_printed=1
  fi

  if [ -f "$ROOT/.planning/STATE.md" ]; then
    for heading in \
      "## Active Resume Point" \
      "## Essential Project Context" \
      "## Load-Bearing Context" \
      "## Non-Current But Essential Context" \
      "## Important Background" \
      "## Open Questions"
    do
      section="$(emit_markdown_section "$ROOT/.planning/STATE.md" "$heading" 90)"
      if [ -n "$section" ]; then
        echo "### .planning/STATE.md -> $heading"
        echo "$section"
        context_printed=1
      fi
    done
  fi

  if [ "$context_printed" = "0" ]; then
    echo "_No .planning/COMPACT_CONTEXT.md or matching STATE.md context sections found._"
  fi
}

# === MULCH SYNC ===
if command -v ml >/dev/null 2>&1 && [ -d "$ROOT/.mulch" ]; then
  MULCH_DIRTY=0
  git diff --quiet -- .mulch/ 2>/dev/null || MULCH_DIRTY=1
  git diff --cached --quiet -- .mulch/ 2>/dev/null || MULCH_DIRTY=1
  if [ -n "$(git ls-files --others --exclude-standard -- .mulch/ 2>/dev/null)" ]; then MULCH_DIRTY=1; fi
  if [ "$MULCH_DIRTY" = "1" ]; then
    echo "[mulch] .mulch/ has changes -> running ml sync"
    ml sync 2>&1 | tail -6 | sed 's/^/  /'
  else
    echo "[mulch] .mulch/ clean"
  fi
fi

# === AUTO-COMMIT SESSION METADATA ===
# Only auto-commit TRACKED markdown session-state files. Source code, tests,
# migrations, configs, and untracked files are NEVER auto-committed by this hook.
METADATA_CANDIDATES=(".planning/STATE.md" ".planning/COMPACT_CONTEXT.md" ".planning/INDEX.md" ".planning/STATE_CURRENT.md" "STATE_CURRENT.md")
METADATA_DIRTY=()
for f in "${METADATA_CANDIDATES[@]}"; do
  if [ -f "$f" ] && git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    if ! git diff --quiet -- "$f" 2>/dev/null; then
      METADATA_DIRTY+=("$f")
    fi
  fi
done

if [ ${#METADATA_DIRTY[@]} -gt 0 ]; then
  echo "[commit] auto-committing session metadata: ${METADATA_DIRTY[*]}"
  git add -- "${METADATA_DIRTY[@]}" 2>/dev/null
  if git commit -m "$(printf 'chore(state): auto-snapshot before /compact\n\nCo-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>')" --no-verify >/dev/null 2>&1; then
    HEAD_SHA=$(git rev-parse --short HEAD)
    echo "  -> $HEAD_SHA"
  else
    echo "  -> commit skipped (nothing to commit after stage)"
  fi
fi

# === WARN ABOUT UNCOMMITTED CODE (don't act, just inform) ===
DIRTY_CODE=$(git diff --name-only HEAD 2>/dev/null | grep -v '^\.planning/' | grep -v '^\.mulch/' | head -10)
if [ -n "$DIRTY_CODE" ]; then
  echo "[warn] uncommitted non-metadata files at compact time:"
  echo "$DIRTY_CODE" | sed 's/^/  /'
  echo "  (these were NOT auto-committed; they'll re-appear in working tree after compact)"
fi

# === PUSH TO ORIGIN ===
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)
if [ -n "$UPSTREAM" ] && [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
  AHEAD=$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)
  if [ "${AHEAD:-0}" -gt 0 ]; then
    echo "[push] pushing $AHEAD commit(s) to $UPSTREAM (backgrounded — won't block compaction)"
    ( git push >/dev/null 2>&1 & )   # detached: a slow/dead network can't stall /compact
  else
    echo "[push] in sync with $UPSTREAM"
  fi
elif [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "[push] on $BRANCH -> skipping auto-push"
fi

# === WRITE HANDOFF DOC ===
if [ -d "$ROOT/.planning" ]; then
  HANDOFF="$ROOT/.planning/COMPACT_HANDOFF.md"
  {
    echo "# Compact Handoff"
    echo ""
    echo "_Auto-generated by global PreCompact hook at $(date -u '+%Y-%m-%d %H:%M UTC'). Read first after compaction._"
    echo ""
    echo "**Branch:** \`$BRANCH\`"
    echo "**HEAD:** \`$HEAD_SHA\`"
    echo ""
    echo "## Last 20 commits"
    git log --oneline -20 2>/dev/null | sed 's/^/- /'
    echo ""
    echo "## Working tree at compact time"
    UNCOM=$(git status --short 2>/dev/null)
    if [ -n "$UNCOM" ]; then
      echo '```'
      echo "$UNCOM"
      echo '```'
    else
      echo "_clean_"
    fi
    echo ""
    echo "## Resume protocol"
    echo "1. Read \`.planning/STATE.md\` -> \`## Active Resume Point\` (if present)"
    if [ -d "$ROOT/.mulch" ] && command -v ml >/dev/null 2>&1; then
      echo "2. Run \`ml prime\` to load mulch domains"
    fi
    echo "3. Continue from the resume point"
    echo ""
    echo "## Load-bearing context"
    echo ""
    echo "_Bounded context copied into the compact hook output so the next terminal sees it even if the summary is aggressive._"
    echo ""
    emit_load_bearing_context
  } > "$HANDOFF" 2>/dev/null && echo "[handoff] wrote $HANDOFF"
fi

# === RESUME HINT (visible to post-compact Claude) ===
echo ""
echo "=== RESUME HINT (auto-injected into post-compact context) ==="
echo "Branch: $BRANCH @ $HEAD_SHA"
echo "Next: read .planning/COMPACT_HANDOFF.md then .planning/STATE.md '## Active Resume Point'"
echo ""
echo "=== LOAD-BEARING CONTEXT (bounded; preserve across compact) ==="
emit_load_bearing_context
echo "=== GLOBAL_PRE_COMPACT_DONE ==="
exit 0
