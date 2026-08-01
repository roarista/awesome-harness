#!/usr/bin/env bash
# git-sync.sh — commit + integrate + push WITHOUT ever discarding anyone else's work.
#
# WHY: multiple Claude Code terminals run against the same repo at once. The hazard is
# a terminal that is BEHIND pushing over a terminal that was AHEAD. This script only
# ever ADDS ("solo agrega, no quita") and it CHECKS that guarantee after the fact.
#
# HARD BANS (never emitted, ever): push --force / --force-with-lease, reset --hard,
# checkout --theirs/--ours, clean -fd. If the situation would need one of those, we
# STOP and exit non-zero for a human. Fail LOUD, never fail-open.
#
# Commits TRACKED modifications only (git add -u). Untracked files are a STOP unless
# you pass --include-untracked — blind `add -A` has published .env files and
# half-written sources before.
#
# Every commit is stamped with a "Terminal: <id>" trailer so you can tell WHICH of the
# parallel terminals made it. Before committing/pushing, a READ-ONLY survey reports the
# other remote branches (AHEAD / RECENT / STALE) so nobody's work dies unnoticed.
#
# Usage: git-sync.sh [--dry-run] [--include-untracked] [-m "message"] [-C <repo>]
#                    [--terminal <id>]
# ponytail: plain git porcelain, no deps, no daemon, no wrapper CLI. --dry-run is the
# SAME code path with mutations stubbed out, not a hand-maintained parallel script.
set -uo pipefail

DRY=0; MSG=""; REPO="."; INC_UNTRACKED=0; TERM_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --include-untracked) INC_UNTRACKED=1 ;;
    -m|--message) MSG="${2:-}"; shift ;;
    -C) REPO="${2:-.}"; shift ;;
    --terminal) TERM_ID="${2:-}"; shift ;;
    -h|--help) sed -n '2,23p' "$0"; exit 0 ;;
    *) echo "git-sync: unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

# WHICH terminal is this? explicit flag > $HARNESS_TERMINAL > tty basename + shell PID > host-PID.
TERM_ID="${TERM_ID:-${HARNESS_TERMINAL:-}}"; _t="$(tty 2>/dev/null || true)"; case "$_t" in /dev/*) TERM_ID="${TERM_ID:-$(basename "$_t")-$$}" ;; *) TERM_ID="${TERM_ID:-$(hostname -s 2>/dev/null || echo host)-$$}" ;; esac

die() { echo "git-sync: STOP — $*" >&2; exit 1; }
g()   { git -C "$REPO" "$@"; }                      # real git (reads are always real)
# run: side-effecting git. In --dry-run it prints and does nothing (rc 0), so the ONE
# real code path below is what --dry-run reports.
run() {
  if [ "$DRY" = 1 ]; then echo "DRY-RUN: would run: git $*"; return 0; fi
  echo "+ git $*" >&2
  g "$@"
}

g rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository: $REPO"
BRANCH="$(g rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] || die "detached HEAD — checkout a branch first."
if g rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then die "merge in progress — resolve it by hand."; fi
# --git-path returns a repo-relative path, so resolve it against the ABSOLUTE git dir —
# otherwise these tests silently read our own cwd instead of $REPO.
GITDIR="$(g rev-parse --absolute-git-dir)"
if [ -d "$GITDIR/rebase-merge" ] || [ -d "$GITDIR/rebase-apply" ]; then
  die "rebase in progress — resolve it by hand (git rebase --continue|--abort)."
fi
# Another terminal's interrupted operation must never be silently completed by our commit.
for _op in CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
  if [ -e "$GITDIR/$_op" ]; then
    die "$_op present — an interrupted operation is in progress in this repo. Finish or abort it by hand."
  fi
done
if [ "$(g rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
  die "shallow clone — the 'nothing was removed' commit-count guarantee is meaningless here. Run: git fetch --unshallow"
fi

UP="$(g rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
[ -n "$UP" ] || die "branch '$BRANCH' has no upstream. Set one deliberately: git push -u origin $BRANCH"
REMOTE="${UP%%/*}"
RBRANCH="${UP#"$REMOTE"/}"                          # remote-side branch; may differ from $BRANCH

# --- 1. fetch FIRST, and remember where the remote was ------------------------
run fetch "$REMOTE" "$RBRANCH" || die "git fetch $REMOTE $RBRANCH failed (bad ref, network, or auth). Nothing was changed."
PRE_REMOTE="$(g rev-parse "$UP" 2>/dev/null || echo "")"
PRE_REMOTE_COUNT="$(g rev-list --count "$UP" 2>/dev/null || echo 0)"
echo "git-sync: branch=$BRANCH upstream=$UP remote_branch=$RBRANCH remote_head=${PRE_REMOTE:0:12} ($PRE_REMOTE_COUNT commits) terminal=$TERM_ID"

# --- 1b. survey the OTHER remote branches (READ-ONLY report, never blocks) -----
# Parallel terminals leave branches behind. Do not commit/push blindly on top of them:
# anything AHEAD of us holds work that would be lost if ignored; anything with nothing
# we lack whose last commit is older than GIT_BRANCH_STALE_DAYS is left to die. This
# block NEVER merges, deletes, blocks, or changes the exit code.
STALE_DAYS="${GIT_BRANCH_STALE_DAYS:-3}"
# --dry-run must NOT mutate: 'fetch --all --prune' both fetches and DELETES
# remote-tracking refs. In dry-run we survey whatever refs already exist.
if [ "$DRY" = 1 ]; then
  echo "DRY-RUN: would run: git fetch --all --prune (surveying the refs already present)"
else
  g fetch --all --prune >/dev/null 2>&1 || echo "git-sync: (survey) 'git fetch --all --prune' failed — survey may be incomplete" >&2
fi
SURVEY_NOW="$(date +%s)"
# Exclude OURSELVES by EXACT field match. A grep pattern would treat '.' (and every
# other BRE metacharacter) in a branch name as a wildcard and silently drop innocent
# branches from the survey — the exact failure this survey exists to prevent.
SURVEY_ALL="$(g for-each-ref --sort=-committerdate \
  --format='%(refname:short)|%(committerdate:unix)|%(committerdate:short)|%(authorname)' \
  refs/remotes 2>/dev/null | awk -F'|' -v a="$REMOTE" -v b="$UP" '$1!=a && $1!=b' || true)"
SURVEY_TOTAL=0
[ -n "$SURVEY_ALL" ] && SURVEY_TOTAL="$(printf '%s\n' "$SURVEY_ALL" | wc -l | tr -d ' ')"
echo "git-sync: branch survey (read-only) — $SURVEY_TOTAL other remote branch(es); stale = nothing we lack AND older than ${STALE_DAYS}d"
SURVEY_AHEAD=""
SURVEY_CAP=20
SURVEY_SHOWN=0
SURVEY_OMITTED=0
# Classify EVERY branch. The cap applies only to PRINTED RECENT/STALE lines — an AHEAD
# branch is always printed, or work outside the cap would die silently.
if [ "$SURVEY_TOTAL" -gt 0 ]; then
  while IFS='|' read -r _ref _ts _when _who; do
    [ -n "$_ref" ] || continue
    _counts="$(g rev-list --left-right --count "HEAD...$_ref" 2>/dev/null || true)"
    _ours="$(printf '%s' "$_counts" | awk '{print ($1==""?0:$1)}')"
    _theirs="$(printf '%s' "$_counts" | awk '{print ($2==""?0:$2)}')"
    _age=$(( (SURVEY_NOW - _ts) / 86400 ))
    if [ "${_theirs:-0}" -gt 0 ]; then
      _class="AHEAD "; _note="has $_theirs commit(s) we do NOT have — integrate before it is lost"
      SURVEY_AHEAD="$SURVEY_AHEAD$_ref"$'\n'
    elif [ "$_age" -gt "$STALE_DAYS" ]; then
      _class="STALE "; _note="ignore, let it die"
    else
      _class="RECENT"; _note="nothing we lack, but recent — keep an eye on it"
    fi
    if [ "$_class" = "AHEAD " ] || [ "$SURVEY_SHOWN" -lt "$SURVEY_CAP" ]; then
      [ "$_class" = "AHEAD " ] || SURVEY_SHOWN=$(( SURVEY_SHOWN + 1 ))
      printf 'git-sync:   %s %s  ahead=%s behind=%s  age=%sd  last=%s by %s  [%s]\n' \
        "$_class" "$_ref" "${_theirs:-0}" "${_ours:-0}" "$_age" "$_when" "$_who" "$_note"
    else
      SURVEY_OMITTED=$(( SURVEY_OMITTED + 1 ))
    fi
  done <<< "$(printf '%s\n' "$SURVEY_ALL")"
  if [ "$SURVEY_OMITTED" -gt 0 ]; then
    echo "git-sync:   ... $SURVEY_OMITTED older branch(es) omitted (showing the $SURVEY_CAP most recently committed; every AHEAD branch is always shown)"
  fi
fi
if [ -n "$SURVEY_AHEAD" ]; then
  echo "git-sync: !! ATTENTION — these branches carry commits you do not have:" >&2
  printf '%s' "$SURVEY_AHEAD" | sed '/^$/d;s/^/git-sync:      /' >&2
  printf '%s' "$SURVEY_AHEAD" | sed '/^$/d' | while read -r _b; do
    echo "git-sync:      inspect (read-only): git log $_b ^HEAD --oneline" >&2
  done
  echo "git-sync: (not blocking — decide by hand whether that work must be integrated)" >&2
fi

# --- 2. commit local work (only ever adds a commit) ---------------------------
UNTRACKED="$(g ls-files --others --exclude-standard)"
if [ -n "$UNTRACKED" ] && [ "$INC_UNTRACKED" = 0 ]; then
  echo "git-sync: untracked files present:" >&2
  printf '%s\n' "$UNTRACKED" | sed 's/^/  /' >&2
  die "refusing to commit untracked files (secrets / half-written files get published this way). .gitignore them, 'git add' them deliberately, or re-run with --include-untracked."
fi
TRACKED_DIRTY="$(g status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ] || { [ "$INC_UNTRACKED" = 1 ] && [ -n "$UNTRACKED" ]; }; then
  [ -n "$MSG" ] || MSG="sync: work in progress from $(hostname -s 2>/dev/null || echo terminal) $(date +%Y-%m-%dT%H:%M:%S)"
  # Stamp WHICH terminal made this commit — auto-generated and -m messages alike.
  case "$MSG" in *"Terminal: $TERM_ID"*) ;; *) MSG="$MSG

Terminal: $TERM_ID" ;; esac
  if [ "$INC_UNTRACKED" = 1 ]; then
    run add -A || die "git add failed — nothing committed, nothing pushed."
  else
    run add -u || die "git add -u failed — nothing committed, nothing pushed."
  fi
  run commit -m "$MSG" || die "git commit FAILED (a pre-commit hook rejected it, or there was nothing to commit). Your work is STAGED but NOT committed and NOTHING was pushed. Fix the cause and re-run."
else
  echo "git-sync: working tree clean, nothing to commit"
fi

# --- 3. integrate remote work BEFORE pushing ----------------------------------
# NOT --autostash: by this point step 2 has committed every tracked modification and
# refused to proceed with untracked files, so there is nothing to stash. If another
# process dirties the tree mid-run, git refuses the rebase and we STOP below with the
# work intact — strictly safer than stashing and hoping the stash comes back.
if ! run pull --rebase "$REMOTE" "$RBRANCH"; then
  CONFLICTS="$(g diff --name-only --diff-filter=U 2>/dev/null)"
  REBASING=0
  if [ -d "$GITDIR/rebase-merge" ] || [ -d "$GITDIR/rebase-apply" ]; then REBASING=1; fi
  if [ -n "$CONFLICTS" ] || [ "$REBASING" = 1 ]; then
    # Abort restores the pre-rebase tree. Never auto-resolve.
    g rebase --abort >/dev/null 2>&1 || true
    echo "git-sync: STOP — rebase CONFLICTED and was ABORTED. Nothing was pushed, nothing lost;" >&2
    echo "git-sync: your work is safe in local commit $(g rev-parse --short HEAD) on $BRANCH." >&2
    if [ -n "$CONFLICTS" ]; then echo "git-sync: conflicting paths:" >&2; echo "$CONFLICTS" >&2; fi
    echo "git-sync: resolve by hand: git pull --rebase $REMOTE $RBRANCH  (then re-run)" >&2
  else
    echo "git-sync: STOP — 'git pull --rebase $REMOTE $RBRANCH' failed WITHOUT a rebase conflict" >&2
    echo "git-sync: (bad remote ref, network/auth, a hook, or a dirty tree). See git's error" >&2
    echo "git-sync: above. Nothing was pushed; your work is safe in local commit $(g rev-parse --short HEAD) on $BRANCH." >&2
  fi
  exit 1
fi

# --- 4. push (plain, never forced) --------------------------------------------
if [ -n "$(g log --oneline "$UP..HEAD" 2>/dev/null)" ]; then
  run push "$REMOTE" "HEAD:refs/heads/$RBRANCH" || die "push rejected. Do NOT force. Re-run git-sync (someone pushed mid-run) or resolve by hand."
else
  echo "git-sync: nothing to push (already up to date with $UP)"
fi

# --- 5. PROVE nothing was taken away ------------------------------------------
run fetch "$REMOTE" "$RBRANCH" >/dev/null 2>&1 || true
POST_REMOTE="$(g rev-parse "$UP")"
POST_COUNT="$(g rev-list --count "$UP")"
if [ -n "$PRE_REMOTE" ]; then
  g merge-base --is-ancestor "$PRE_REMOTE" "$POST_REMOTE" \
    || die "GUARANTEE VIOLATED: pre-run remote ${PRE_REMOTE:0:12} is no longer an ancestor of ${POST_REMOTE:0:12}. Remote history was rewritten — investigate by hand NOW."
  [ "$POST_COUNT" -ge "$PRE_REMOTE_COUNT" ] \
    || die "GUARANTEE VIOLATED: remote commit count shrank ($PRE_REMOTE_COUNT -> $POST_COUNT)."
fi
echo "git-sync: OK — remote ${PRE_REMOTE:0:12} ($PRE_REMOTE_COUNT) -> ${POST_REMOTE:0:12} ($POST_COUNT); every pre-existing remote commit still reachable (only added, nothing removed)."
