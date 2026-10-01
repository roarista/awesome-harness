#!/usr/bin/env bash
# dry_run.sh [-n N] [--check-all] <repo>...  - READ-ONLY report, before installing.
# Per repo: replays the 200-line ratchet over the last N non-merge commits
# (each vs its parent), and flags automated committers:
#   - >=10 commits in the last 24h (all refs)
#   - a bot / non-human author among the last 200 commits
#   - a prepare-commit-msg / post-commit / post-merge hook that runs `git commit`
# --check-all also times check_all.sh --fast where .check-all.json opts in.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N=30; RUN_CA=0
while [ $# -gt 0 ]; do
  case "$1" in
    -n) N="$2"; shift 2 ;;
    --check-all) RUN_CA=1; shift ;;
    *) break ;;
  esac
done
BOT_RE='\[bot\]|github-actions|dependabot|renovate|actions@github|bot@|automation'

printf '%-18s | %8s | %11s | %-40s | %s\n' repo replayed would-block automated? check-all
for repo in "$@"; do
  name="$(basename "$repo")"
  if ! git -C "$repo" rev-parse --verify -q HEAD >/dev/null; then
    printf '%-18s | %8s | %11s | %-40s | %s\n' "$name" - - "not a repo / no HEAD" -; continue
  fi
  blocked=0; replayed=0; hits=""
  for sha in $(git -C "$repo" rev-list --no-merges -n "$N" HEAD); do
    replayed=$((replayed+1))
    if ! out="$(cd "$repo" && python3 "$HERE/ratchet.py" --commit "$sha" 2>&1)"; then
      blocked=$((blocked+1))
      hits="$hits ${sha:0:7}:$(echo "$out" | grep -c ' -> ')f"
    fi
  done

  why=""
  c24="$(git -C "$repo" log --all --since='24 hours ago' --format=%H | sort -u | wc -l | tr -d ' ')"
  [ "$c24" -ge 10 ] && why="$why ${c24}c/24h"
  # authors only: committer "GitHub <noreply@github.com>" is just a web-UI merge
  bots="$(git -C "$repo" log --all -n 200 --format='%an <%ae>' \
    | sort -u | grep -Ei "$BOT_RE" | head -3 | tr '\n' ';')"
  [ -n "$bots" ] && why="$why bot:$bots"
  hooks="$(cd "$repo" && git rev-parse --git-path hooks)"
  case "$hooks" in /*) ;; *) hooks="$repo/$hooks" ;; esac
  for h in prepare-commit-msg post-commit post-merge post-rewrite; do
    [ -f "$hooks/$h" ] && grep -v '^[[:space:]]*#' "$hooks/$h" | grep -Eq 'git( -C [^ ]+)? commit' && why="$why hook:$h"
  done
  [ -z "$why" ] && why="no (${c24}c/24h)"

  ca="-"
  if [ -f "$repo/.check-all.json" ]; then
    ca="opted-in"
    if [ $RUN_CA -eq 1 ]; then
      s=$SECONDS
      perl -e 'alarm shift; exec @ARGV' 120 bash "$HERE/../check-all/check_all.sh" \
        "$repo" --fast >"${TMPDIR:-/tmp}/dryrun_ca_$name.log" 2>&1
      rc=$?; ca="opted-in rc=$rc $((SECONDS-s))s"; [ $rc -eq 142 ] && ca="opted-in TIMEOUT(pass)"
    fi
  fi
  printf '%-18s | %8s | %11s | %-40s | %s\n' "$name" "$replayed" "$blocked" "$why" "$ca"
  [ -n "$hits" ] && echo "    blocked:$hits"
done
exit 0
