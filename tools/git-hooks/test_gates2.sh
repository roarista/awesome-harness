#!/usr/bin/env bash
# test_gates2.sh - strict-gate tests, fix round 4 (test_gates.sh is at its 200-line cap):
# tracked .now.md rule, missing check-all runner, timeout ruling, CommonMark fence length.
# Builds throwaway git repos + fake harnesses under $TMPDIR; touches nothing else.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/gates2_test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS  $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL  $1"; [ -n "${2:-}" ] && sed 's/^/      | /' "$2"; }
lines() { python3 -c "import sys; sys.stdout.write(''.join(f'x{i} = {i}\n' for i in range(int(sys.argv[1]))))" "$1" > "$2"; }

# fake harness <dir> <check_all body or "none">: real hooks + a stub check-all
fake_harness() {
  mkdir -p "$1/tools/check-all" "$1/tools/git-hooks"
  ln -s "$HERE/pre-commit" "$HERE/commit-msg" "$HERE/ratchet.py" "$1/tools/git-hooks/"
  [ "$2" = none ] || printf '#!/usr/bin/env bash\n%s\n' "$2" > "$1/tools/check-all/check_all.sh"
}
FH="$T/fh"; fake_harness "$FH" "exit 0"
FHN="$T/fhn"; fake_harness "$FHN" none
FHS="$T/fhs"; fake_harness "$FHS" "sleep 30"
export AWESOME_HARNESS="$FH"

try() {
  local label="$1" want="$2" rc; shift 2
  ( cd "$R" && git commit -q "$@" ) >"$T/out.log" 2>&1; rc=$?
  [ $rc -ne 0 ] && rc=1
  if [ "$rc" = "$want" ]; then ok "$label"; else bad "$label (want rc=$want got $rc)" "$T/out.log"; fi
  [ $rc -ne 0 ] && ( cd "$R" && git reset -q --hard HEAD )
  return 0
}
has() { grep -q "$1" "$T/out.log" && ok "$2" || bad "$2" "$T/out.log"; }
stage() { (cd "$R" && git add "$@"); }
# new_repo NAME [strict] - repo with .check-all.json (+ .harness) committed, shims installed
new_repo() {
  R="$T/$1"; mkdir -p "$R"
  ( cd "$R" && git init -q && git config user.email t@t && git config user.name t \
    && git config commit.gpgsign false && echo '{}' > .check-all.json \
    && { [ "${2:-}" = strict ] && touch .harness || true; } \
    && git add -A && git commit -q --no-verify -m root )
  "$HERE/install.sh" "$R" >/dev/null || bad "install into $1"
}

# --- FIX 1: strict repo needs a tracked .now.md ------------------------------------
new_repo nonow strict
lines 5 "$R/a.py"; stage a.py
try "strict + source change + no .now.md anywhere -> blocked" 1 -m n1
has "strict repo needs a tracked .now.md" "  ...names the tracked-.now.md rule"
lines 5 "$R/a.py"; stage a.py; echo "NOW: x" > "$R/.now.md"
try "strict + untracked, unstaged .now.md on disk -> blocked" 1 -m n2
has "strict repo needs a tracked .now.md" "  ...names the tracked-.now.md rule"
lines 5 "$R/a.py"; echo "NOW: x" > "$R/.now.md"; stage a.py .now.md
try "strict + newly staged .now.md with source -> passes" 0 -m n3
echo "y = 1" >> "$R/a.py"; (cd "$R" && git rm -q .now.md); stage a.py
try "strict + staged deletion of .now.md with source -> blocked" 1 -m n4
has "strict repo needs a tracked .now.md" "  ...names the tracked-.now.md rule"

# --- FIX 2: missing check-all runner -----------------------------------------------
AWESOME_HARNESS="$FHN"; echo "y = 2" >> "$R/a.py"; echo "NOW: y" >> "$R/.now.md"; stage a.py .now.md
try "strict + check-all runner missing -> blocked" 1 -m r1
has "check-all runner not found" "  ...names the missing runner"
new_repo loose
AWESOME_HARNESS="$FHN"; lines 5 "$R/a.py"; stage a.py
try "non-strict + check-all runner missing -> WARN and pass" 0 -m r2
has "WARN check-all runner not found" "  ...with a WARN"

# --- RULING: check-all timeout stays WARN-and-pass, even strict ---------------------
R="$T/nonow"; AWESOME_HARNESS="$FHS"; echo "y = 3" >> "$R/a.py"; echo "NOW: z" >> "$R/.now.md"
stage a.py .now.md
( cd "$R" && CHECK_ALL_TIMEOUT=1 git commit -q -m tmo ) >"$T/out.log" 2>&1 \
  && ok "strict + check-all timeout -> WARN and pass (deliberate ruling)" \
  || bad "strict + check-all timeout -> WARN and pass" "$T/out.log"
has "timed out" "  ...with the timeout WARN"
AWESOME_HARNESS="$FH"   # run_group_timeout already killed the sleep group

# --- FIX 3: CommonMark fence length --------------------------------------------------
mkdir -p "$R/.artifacts"
printf 'VERDICT: PASS\n~~~~\n~~~\n~~~~\nVERDICT: REJECT\n' > "$R/.artifacts/nest_rej.md"
printf '~~~~\n~~~\nVERDICT: REJECT\n~~~\n~~~~\nVERDICT: PASS\n' > "$R/.artifacts/nest_pass.md"
printf '````\n```\nVERDICT: PASS\n```\n' > "$R/.artifacts/bt_open.md"
big() { lines 30 "$R/$1"; echo "NOW: $1" >> "$R/.now.md"; stage "$1" .now.md; }
big g1.py; try "~~~ inside ~~~~ does not close it; outside REJECT seen -> blocked" 1 -m big -m "Audit: .artifacts/nest_rej.md"
has "says REJECT" "  ...says REJECT"
big g2.py; try "REJECT nested in ~~~~ is hidden; outside PASS -> passes" 0 -m big -m "Audit: .artifacts/nest_pass.md"
big g3.py; try "\`\`\` inside unterminated \`\`\`\` stays hidden -> no verdict -> blocked" 1 -m big -m "Audit: .artifacts/bt_open.md"

# --- round 5: a type change (file -> symlink) is a source change -----------------------
new_repo tchg strict
lines 5 "$R/s.py"; echo "NOW: s" > "$R/.now.md"; stage s.py .now.md; try "tchg setup" 0 -m t0
(cd "$R" && rm s.py && ln -s .now.md s.py); stage s.py
try "strict + file->symlink type change, .now.md unstaged -> blocked" 1 -m t1

echo "---- $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
