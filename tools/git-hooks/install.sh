#!/usr/bin/env bash
# install.sh [--uninstall] <repo>...
# Installs a tiny pre-commit SHIM that execs the awesome-harness copy of
# tools/git-hooks/pre-commit (so updates propagate without reinstalling).
# - hooks dir from `git rev-parse --git-path hooks` (respects core.hooksPath)
# - a foreign pre-commit is MOVED to pre-commit.local (chained, never deleted)
# - idempotent; --uninstall removes the shim and restores pre-commit.local
# - refuses when pre-commit is tracked by git (e.g. core.hooksPath=.githooks):
#   replacing it would edit a committed file in that repo.
set -u

MARKER="awesome-harness-pre-commit-shim"
HARNESS_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() { echo "usage: $0 [--uninstall] <repo>..." >&2; exit 2; }

MODE=install
[ "${1:-}" = "--uninstall" ] && { MODE=uninstall; shift; }
[ $# -ge 1 ] || usage

is_ours() { [ -f "$1" ] && grep -q "$MARKER" "$1"; }

write_shim() {
  cat > "$1" <<EOF
#!/usr/bin/env bash
# $MARKER - installed by awesome-harness tools/git-hooks/install.sh
# Real logic lives in the harness so updates propagate. Uninstall with:
#   $HARNESS_DEFAULT/tools/git-hooks/install.sh --uninstall <repo>
H="\${AWESOME_HARNESS:-$HARNESS_DEFAULT}/tools/git-hooks/pre-commit"
if [ ! -f "\$H" ]; then
  echo "pre-commit: WARN harness hook missing at \$H - gate skipped" >&2
  L="\$(git rev-parse --git-path hooks)/pre-commit.local"
  [ -x "\$L" ] && exec "\$L" "\$@"
  exit 0
fi
exec bash "\$H" "\$@"
EOF
  chmod +x "$1"
}

do_repo() {
  local repo="$1" hooks top hook local_hook rel
  top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || {
    echo "[$repo] SKIP: not a git repo"; return 1; }
  hooks="$(cd "$top" && git rev-parse --git-path hooks)"
  case "$hooks" in /*) ;; *) hooks="$top/$hooks" ;; esac
  hook="$hooks/pre-commit"; local_hook="$hooks/pre-commit.local"

  if [ "$MODE" = uninstall ]; then
    if ! is_ours "$hook"; then
      echo "[$repo] uninstall: no shim at $hook - nothing to do"; return 0
    fi
    rm -f "$hook"
    if [ -f "$local_hook" ]; then
      mv "$local_hook" "$hook"
      echo "[$repo] uninstall: removed shim, restored pre-commit.local -> pre-commit"
    else
      echo "[$repo] uninstall: removed shim ($hook)"
    fi
    return 0
  fi

  mkdir -p "$hooks"
  if is_ours "$hook"; then
    write_shim "$hook"
    echo "[$repo] already installed - shim refreshed ($hook)"; return 0
  fi
  if [ -e "$hook" ]; then
    rel="${hook#$top/}"
    if [ "$rel" != "$hook" ] && git -C "$top" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
      echo "[$repo] REFUSED: $rel is tracked by git; installing would edit a committed file."
      echo "        Chain the harness hook from that file by hand, or decide per repo."
      return 1
    fi
    if [ -e "$local_hook" ]; then
      echo "[$repo] REFUSED: both pre-commit (foreign) and pre-commit.local exist - resolve by hand"
      return 1
    fi
    mv "$hook" "$local_hook"
    echo "[$repo] moved existing pre-commit -> pre-commit.local (will be chained)"
  fi
  write_shim "$hook"
  echo "[$repo] installed shim at $hook"
}

rc=0
for r in "$@"; do do_repo "$r" || rc=1; done
exit $rc
