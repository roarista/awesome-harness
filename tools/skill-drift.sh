#!/usr/bin/env bash
# skill-drift.sh — diff repo skills against their installed (live) copies.
#   skills/<n>/SKILL.md        vs ~/.claude/skills/<n>/SKILL.md
#   codex/skills/<n>/SKILL.md  vs ~/.codex/skills/<n>/SKILL.md
# Usage: tools/skill-drift.sh [skill-name ...]   (no args = every repo skill)
# Exit 0 = in sync, 1 = drift or missing live copy. Fix: re-run install.sh.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_LIVE="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
CODEX_LIVE="${CODEX_SKILLS_DIR:-${CODEX_HOME:-$HOME/.codex}/skills}"
SKIP=" codex/caveman "   # legacy: install.sh removes it from the live layer
drift=0 checked=0

check() { # $1=label $2=repo file $3=live file
  local name; name="$(basename "$(dirname "$2")")"
  case "$SKIP" in *" $1/$name "*) return ;; esac
  if [ -n "$WANT" ]; then case " $WANT " in *" $name "*) ;; *) return ;; esac; fi
  checked=$((checked + 1))
  if [ ! -f "$3" ]; then echo "MISSING $1 $name: $3"; drift=1
  elif ! cmp -s "$2" "$3"; then
    echo "DRIFT   $1 $name: $(diff "$2" "$3" | grep -c '^[<>]') lines differ ($3)"; drift=1
  fi
}

WANT="$*"
for f in "$REPO"/skills/*/SKILL.md; do
  check claude "$f" "$CLAUDE_LIVE/$(basename "$(dirname "$f")")/SKILL.md"
done
for f in "$REPO"/codex/skills/*/SKILL.md; do
  check codex "$f" "$CODEX_LIVE/$(basename "$(dirname "$f")")/SKILL.md"
done
if [ "$checked" -eq 0 ]; then echo "skill-drift: no skills matched '${WANT}'" >&2; exit 1; fi
[ "$drift" -eq 0 ] && echo "skill-drift: $checked copies in sync"
exit "$drift"
