#!/usr/bin/env bash
# install.sh [--uninstall] <repo>...
# Installs tiny pre-commit and commit-msg SHIMS that exec the awesome-harness
# copies in tools/git-hooks/ (so updates propagate without reinstalling).
# Per hook (own marker each):
# - hooks dir from `git rev-parse --git-path hooks` (respects core.hooksPath)
# - a foreign <hook> is MOVED to <hook>.local (chained, never deleted)
# - idempotent; --uninstall removes the shim and restores <hook>.local
# - refuses when <hook> is tracked by git (e.g. core.hooksPath=.githooks):
#   replacing it would edit a committed file in that repo.
set -u

HOOK_NAMES="pre-commit commit-msg"
HARNESS_DEFAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() { echo "usage: $0 [--uninstall] <repo>..." >&2; exit 2; }

MODE=install
[ "${1:-}" = "--uninstall" ] && { MODE=uninstall; shift; }
[ $# -ge 1 ] || usage

# is_ours FILE NAME / write_shim FILE NAME
is_ours() { [ -f "$1" ] && grep -q "awesome-harness-$2-shim" "$1"; }

write_shim() {
  local MARKER="awesome-harness-$2-shim" N="$2"
  cat > "$1" <<EOF
#!/usr/bin/env bash
# $MARKER - installed by awesome-harness tools/git-hooks/install.sh
# Real logic lives in the harness so updates propagate. Uninstall with:
#   $HARNESS_DEFAULT/tools/git-hooks/install.sh --uninstall <repo>
H="\${AWESOME_HARNESS:-$HARNESS_DEFAULT}/tools/git-hooks/$N"
if [ ! -f "\$H" ]; then
  # strict = .harness in the index or the working tree (same rule as the hooks)
  if git cat-file -e :.harness 2>/dev/null || [ -f "\$(git rev-parse --show-toplevel)/.harness" ]; then
    echo "$N: BLOCKED: harness hook missing at \$H (strict repo: .harness; fix AWESOME_HARNESS, or bypass: git commit --no-verify)" >&2
    exit 1
  fi
  echo "$N: WARN harness hook missing at \$H - gate skipped" >&2
  L="\$(git rev-parse --git-path hooks)/$N.local"
  [ -x "\$L" ] && exec "\$L" "\$@"
  exit 0
fi
exec bash "\$H" "\$@"
EOF
  chmod +x "$1"
}

# do_hook REPO NAME [check] - install/uninstall one shim; `check` only runs the
# refusal checks and writes nothing
do_hook() {
  local repo="$1" n="$2" phase="${3:-apply}" hooks top hook local_hook rel
  top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || {
    echo "[$repo] SKIP: not a git repo"; return 1; }
  hooks="$(cd "$top" && git rev-parse --git-path hooks)"
  case "$hooks" in /*) ;; *) hooks="$top/$hooks" ;; esac
  hook="$hooks/$n"; local_hook="$hooks/$n.local"

  if [ "$MODE" = uninstall ]; then
    if ! is_ours "$hook" "$n"; then
      echo "[$repo] uninstall: no $n shim at $hook - nothing to do"; return 0
    fi
    rm -f "$hook"
    if [ -f "$local_hook" ]; then
      mv "$local_hook" "$hook"
      echo "[$repo] uninstall: removed shim, restored $n.local -> $n"
    else
      echo "[$repo] uninstall: removed shim ($hook)"
    fi
    return 0
  fi

  if is_ours "$hook" "$n"; then
    [ "$phase" = check ] && return 0
    write_shim "$hook" "$n"
    echo "[$repo] already installed - $n shim refreshed ($hook)"; return 0
  fi
  if [ -e "$hook" ]; then
    rel="${hook#$top/}"
    if [ "$rel" != "$hook" ] && git -C "$top" ls-files --error-unmatch "$rel" >/dev/null 2>&1; then
      echo "[$repo] REFUSED: $rel is tracked by git; installing would edit a committed file."
      echo "        Chain the harness hook from that file by hand, or decide per repo."
      return 1
    fi
    if [ -e "$local_hook" ]; then
      echo "[$repo] REFUSED: both $n (foreign) and $n.local exist - resolve by hand"
      return 1
    fi
    [ "$phase" = check ] && return 0
    mv "$hook" "$local_hook"
    echo "[$repo] moved existing $n -> $n.local (will be chained)"
  fi
  [ "$phase" = check ] && return 0
  mkdir -p "$hooks"; write_shim "$hook" "$n"
  echo "[$repo] installed $n shim at $hook"
}

# install: every refusal check runs before anything is written, so a refused
# repo is left untouched (no partial install)
do_repo() {
  local n r=0
  if [ "$MODE" = install ]; then
    for n in $HOOK_NAMES; do do_hook "$1" "$n" check || return 1; done
  fi
  for n in $HOOK_NAMES; do do_hook "$1" "$n" || r=1; done
  return $r
}

rc=0
for r in "$@"; do do_repo "$r" || rc=1; done
exit $rc
