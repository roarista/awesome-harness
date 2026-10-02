#!/usr/bin/env bash
# test_pre_commit.sh - end-to-end tests for the 200-line ratchet hook + installer.
# Builds throwaway git repos under $TMPDIR; touches nothing else.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="$(cd "$HERE/../.." && pwd)"
export AWESOME_HARNESS="$HARNESS"
T="$(mktemp -d "${TMPDIR:-/tmp}/ratchet_test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0

ok()  { PASS=$((PASS+1)); echo "PASS  $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL  $1"; [ -n "${2:-}" ] && sed 's/^/      | /' "$2"; }
lines() { python3 -c "import sys; sys.stdout.write(''.join(f'x{i} = {i}\n' for i in range(int(sys.argv[1]))))" "$1" > "$2"; }

# commit_expect <label> <want: 0|1> [env...] - tries a commit in $R
commit_expect() {
  local label="$1" want="$2"; shift 2
  local out="$T/out.log" rc
  ( cd "$R" && env "$@" git commit -q -m "$label" ) >"$out" 2>&1; rc=$?
  [ $rc -ne 0 ] && rc=1
  if [ "$rc" = "$want" ]; then ok "$label"; else bad "$label (want rc=$want got $rc)" "$out"; fi
  [ $rc -ne 0 ] && ( cd "$R" && git reset -q --hard HEAD 2>/dev/null; git clean -qfd )
  return 0
}

new_repo() {
  R="$T/$1"; mkdir -p "$R"
  ( cd "$R" && git init -q && git config user.email t@t && git config user.name t \
    && git config commit.gpgsign false && git commit -q --allow-empty -m root )
}

# --- ratchet behaviour -------------------------------------------------------
new_repo ratchet
"$HERE/install.sh" "$R" >/dev/null || bad "install into fresh repo"

lines 150 "$R/small.py"; (cd "$R" && git add small.py)
commit_expect "new 150-line file passes" 0

lines 250 "$R/big_new.py"; (cd "$R" && git add big_new.py)
commit_expect "new 250-line file fails" 1

lines 300 "$R/legacy.py"; (cd "$R" && git add legacy.py)
commit_expect "seed 300-line legacy file (SKIP_RATCHET=1 passes)" 0 SKIP_RATCHET=1

lines 301 "$R/legacy.py"; (cd "$R" && git add legacy.py)
commit_expect "existing 300-line file growing to 301 fails" 1

lines 290 "$R/legacy.py"; (cd "$R" && git add legacy.py)
commit_expect "shrinking 300 -> 290 passes" 0

echo "x = 1" >> "$R/legacy.py"; (cd "$R" && git add legacy.py)
commit_expect "growing 290 -> 291 fails (ratchet tightened)" 1

mkdir -p "$R/tests"; lines 400 "$R/tests/test_big.py"; lines 400 "$R/app.spec.ts"
(cd "$R" && git add tests app.spec.ts)
commit_expect "400-line test files pass" 0

lines 400 "$R/notes.md"; (cd "$R" && git add notes.md)
commit_expect "400-line non-source file passes" 0

lines 260 "$R/gen.py"; echo '{"ratchet_ignore": ["gen.py"]}' > "$R/.check-all.json"
(cd "$R" && git add gen.py .check-all.json)
commit_expect "ratchet_ignore exempts a path (check-all opt-in path also runs)" 0

lines 250 "$R/big2.py"; (cd "$R" && git add big2.py)
commit_expect "SKIP_RATCHET=1 passes a 250-line new file" 0 SKIP_RATCHET=1
( cd "$R" && echo y >> small.py && git add small.py && SKIP_RATCHET=1 git commit -q -m w ) 2>"$T/skip.err"
grep -q "SKIP_RATCHET=1" "$T/skip.err" && ok "SKIP_RATCHET prints a loud warning" \
  || bad "SKIP_RATCHET prints a loud warning" "$T/skip.err"

lines 260 "$R/renamed_src.py"; (cd "$R" && git add renamed_src.py)
commit_expect "seed 260-line file for rename" 0 SKIP_RATCHET=1
(cd "$R" && git mv renamed_src.py renamed_dst.py)
commit_expect "pure rename of a big file passes" 0

lines 300 "$R/v.py"; (cd "$R" && git add v.py)
( cd "$R" && git commit -q --no-verify -m nv ) && ok "--no-verify bypasses" || bad "--no-verify bypasses"

# --- replay mode -------------------------------------------------------------
(cd "$R" && lines 220 grow.py && git add grow.py && git commit -q --no-verify -m g)
( cd "$R" && python3 "$HERE/ratchet.py" --commit HEAD >/dev/null ); rc=$?
[ $rc -eq 1 ] && ok "replay --commit flags a blocked commit" || bad "replay --commit (rc=$rc)"
( cd "$R" && python3 "$HERE/ratchet.py" --commit HEAD~1 >/dev/null ); rc=$?
[ $rc -eq 1 ] && ok "replay of --no-verify 300-line commit flags it" || bad "replay HEAD~1 (rc=$rc)"

# --- check-all timeout never wedges -----------------------------------------
FH="$T/fakeh"; mkdir -p "$FH/tools/check-all" "$FH/tools/git-hooks"
ln -s "$HERE/pre-commit" "$HERE/ratchet.py" "$FH/tools/git-hooks/"
MARK=$((40000 + $$ % 900))   # unique sleep length so pgrep only sees ours
printf '#!/usr/bin/env bash\nsleep %s &\nsleep %s &\nwait\n' "$MARK" "$MARK" \
  > "$FH/tools/check-all/check_all.sh"
lines 10 "$R/tiny.py"; (cd "$R" && git add tiny.py)
SECONDS=0
commit_expect "check-all timeout (1s) warns and passes" 0 CHECK_ALL_TIMEOUT=1 AWESOME_HARNESS="$FH"
grep -q "timed out" "$T/out.log" && ok "timeout prints the warning" || bad "timeout warning" "$T/out.log"
[ $SECONDS -lt 10 ] && ok "timeout did not wedge (${SECONDS}s)" || bad "timeout wedged (${SECONDS}s)"
if pgrep -f "sleep $MARK" >/dev/null; then
  bad "grandchildren killed on timeout (sleep $MARK survived)"; pkill -f "sleep $MARK"
else ok "grandchildren killed on timeout (no 'sleep $MARK' survives)"; fi

lines 250 "$R/Big.PY"; (cd "$R" && git add Big.PY)
commit_expect "new 250-line Big.PY fails (extension case-insensitive)" 1

# --- installer: preserve, chain, idempotent, uninstall -----------------------
new_repo chain
HK="$R/.git/hooks"
printf '#!/bin/sh\necho LOCAL_RAN >> "%s/ran.log"\nexit 0\n' "$T" > "$HK/pre-commit"
chmod +x "$HK/pre-commit"; cp "$HK/pre-commit" "$T/orig_hook"
"$HERE/install.sh" "$R" >/dev/null && "$HERE/install.sh" "$R" > "$T/inst2.log"
[ -f "$HK/pre-commit.local" ] && cmp -s "$HK/pre-commit.local" "$T/orig_hook" \
  && ok "pre-existing hook preserved as pre-commit.local" || bad "preserve existing hook"
grep -q "already installed" "$T/inst2.log" && cmp -s "$HK/pre-commit.local" "$T/orig_hook" \
  && [ ! -e "$HK/pre-commit.local.local" ] && ok "install twice is idempotent" || bad "idempotent" "$T/inst2.log"
lines 10 "$R/a.py"; (cd "$R" && git add a.py)
commit_expect "commit passes through shim" 0
grep -q LOCAL_RAN "$T/ran.log" 2>/dev/null && ok "pre-commit.local was chained" || bad "chain local"
printf '#!/bin/sh\nexit 1\n' > "$HK/pre-commit.local"
lines 10 "$R/b.py"; (cd "$R" && git add b.py)
commit_expect "failing pre-commit.local still blocks" 1
cp "$T/orig_hook" "$HK/pre-commit.local"
"$HERE/install.sh" --uninstall "$R" >/dev/null
cmp -s "$HK/pre-commit" "$T/orig_hook" && [ ! -e "$HK/pre-commit.local" ] \
  && ok "uninstall restores original hook" || bad "uninstall restore"

# --- installer: core.hooksPath + tracked hook refusal ------------------------
new_repo hookspath
(cd "$R" && mkdir .githooks && git config core.hooksPath .githooks)
"$HERE/install.sh" "$R" >/dev/null && [ -f "$R/.githooks/pre-commit" ] \
  && ok "respects core.hooksPath" || bad "core.hooksPath"
(cd "$R" && git add .githooks && git commit -q --no-verify -m track)
"$HERE/install.sh" --uninstall "$R" >/dev/null
printf '#!/bin/sh\nexit 0\n' > "$R/.githooks/pre-commit"; chmod +x "$R/.githooks/pre-commit"
(cd "$R" && git add .githooks && git commit -q --no-verify -m tracked)
"$HERE/install.sh" "$R" > "$T/ref.log"; rc=$?
[ $rc -ne 0 ] && grep -q REFUSED "$T/ref.log" && [ -z "$(cd "$R" && git status --porcelain)" ] \
  && ok "refuses to replace a git-tracked hook" || bad "tracked refusal" "$T/ref.log"

echo "---- $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
