#!/usr/bin/env bash
# test_gates.sh - end-to-end tests for the strict-mode (.harness) gates:
# check-all requirement, .now.md, trellis, commit-msg audit trailer.
# Builds throwaway git repos + a fake harness under $TMPDIR; touches nothing else.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/gates_test.XXXXXX")"
trap 'rm -rf "$T"' EXIT
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS  $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL  $1"; [ -n "${2:-}" ] && sed 's/^/      | /' "$2"; }
lines() { python3 -c "import sys; sys.stdout.write(''.join(f'x{i} = {i}\n' for i in range(int(sys.argv[1]))))" "$1" > "$2"; }

# fake harness: real hooks, check-all that always passes
FH="$T/fakeh"; mkdir -p "$FH/tools/check-all" "$FH/tools/git-hooks"
ln -s "$HERE/pre-commit" "$HERE/commit-msg" "$HERE/ratchet.py" "$FH/tools/git-hooks/"
printf '#!/usr/bin/env bash\nexit 0\n' > "$FH/tools/check-all/check_all.sh"
export AWESOME_HARNESS="$FH"

# fake trellis: exit code from $T/trellis_rc; writes a unique report to --out
mkdir -p "$T/bin"
cat > "$T/bin/trellis" <<EOF
#!/bin/sh
out=""; bl=no
while [ \$# -gt 0 ]; do
  case "\$1" in --out) out="\$2"; shift ;; --baseline) bl=yes ;; esac; shift
done
[ -n "\$out" ] && echo "{\"run\": \"\$\$\", \"baseline_arg\": \"\$bl\"}" > "\$out"
exit \$(cat "$T/trellis_rc")
EOF
chmod +x "$T/bin/trellis"; echo 0 > "$T/trellis_rc"
FULLPATH="$T/bin:$PATH"; BAREPATH="/usr/bin:/bin"   # BAREPATH: no trellis
export PATH="$FULLPATH"

# try <label> <want: 0|1> <git commit args...> - commit in $R; on failure, reset
try() {
  local label="$1" want="$2" rc; shift 2
  ( cd "$R" && git commit -q "$@" ) >"$T/out.log" 2>&1; rc=$?
  [ $rc -ne 0 ] && rc=1
  if [ "$rc" = "$want" ]; then ok "$label"; else bad "$label (want rc=$want got $rc)" "$T/out.log"; fi
  [ $rc -ne 0 ] && ( cd "$R" && git reset -q --hard HEAD )
  return 0
}
has() { grep -q "$1" "$T/out.log" && ok "$2" || bad "$2" "$T/out.log"; }
new_repo() {
  R="$T/$1"; mkdir -p "$R"
  ( cd "$R" && git init -q && git config user.email t@t && git config user.name t \
    && git config commit.gpgsign false && git commit -q --allow-empty -m root )
  "$HERE/install.sh" "$R" >/dev/null || bad "install into $1"
}
stage() { (cd "$R" && git add "$@"); }
now() { date +%s%N >> "$R/.now.md"; stage .now.md; }

# --- check-all requirement ---------------------------------------------------
new_repo strict; touch "$R/.harness"
lines 5 "$R/a.py"; stage .harness a.py
try "strict + no .check-all.json -> blocked" 1 -m c1
has "requires .check-all.json" "  ...names the .check-all.json rule"

new_repo loose
lines 5 "$R/a.py"; stage a.py
try "non-strict + no .check-all.json -> passes" 0 -m c1
has "WARN check-all skipped" "  ...with a WARN on stderr"

# --- .now.md ----------------------------------------------------------------
R="$T/strict"; touch "$R/.harness"; lines 5 "$R/a.py"; echo "{}" > "$R/.check-all.json"; now
stage .harness .check-all.json a.py
try "strict seed (.check-all.json + .now.md + source) passes" 0 -m seed
echo "y = 1" >> "$R/a.py"; stage a.py
try "strict + source change + unstaged .now.md -> blocked" 1 -m n1
has "update .now.md" "  ...names the .now.md rule"
echo "y = 1" >> "$R/a.py"; stage a.py; now
try "strict + source change + staged .now.md -> passes" 0 -m n2
echo "doc" > "$R/notes.md"; stage notes.md
try "strict + docs-only change needs no .now.md" 0 -m n3

# --- commit-msg audit trailer -------------------------------------------------
mkdir -p "$R/.artifacts"
printf '# audit\nVERDICT: PASS\n' > "$R/.artifacts/pass.md"
printf '# audit\n**VERDICT:** PASS WITH FIXES\n' > "$R/.artifacts/pwf.md"
printf '# audit\nVERDICT: REJECT\n' > "$T/reject.md"
big() { lines 30 "$R/$1"; stage "$1"; now; }
big b1.py; try "big change, no Audit trailer -> blocked" 1 -m big
has "no 'Audit: <path>' trailer" "  ...names the audit rule"
big b1.py; try "trailer -> REJECT report (absolute path) -> blocked" 1 -m big -m "Audit: $T/reject.md"
has "says REJECT" "  ...says REJECT"
big b1.py; try "trailer -> missing report -> blocked" 1 -m big -m "Audit: .artifacts/nope.md"
big b1.py; try "trailer -> PASS report (repo-relative) -> passes" 0 -m big -m "Audit: .artifacts/pass.md"
big b2.py; try "trailer -> PASS WITH FIXES report -> passes" 0 -m big -m "Audit: .artifacts/pwf.md"
lines 5 "$R/s.py"; stage s.py; now
try "small change (5 lines) needs no trailer" 0 -m small
R="$T/loose"; lines 30 "$R/b1.py"; stage b1.py
try "non-strict big change, no trailer -> passes" 0 -m big

# --- trellis -------------------------------------------------------------------
R="$T/strict"; TB="$R/.artifacts/trellis/baseline.json"
ts() { echo "export const v$1 = $1;" > "$R/x.ts"; stage x.ts; now; }
echo 2 > "$T/trellis_rc"; ts 1
try "strict + trellis exit 2 -> blocked" 1 -m t1
has "trellis policy failed" "  ...names the trellis rule"
[ ! -f "$TB" ] && ok "  ...no baseline written on a policy fail" || bad "baseline written on fail"
echo 0 > "$T/trellis_rc"; ts 2
try "strict + trellis exit 0 -> passes" 0 -m t2
has "trellis: baseline created" "  ...baseline created"
B1="$(cat "$TB" 2>/dev/null)"; ts 3
try "strict + trellis exit 0 again -> passes" 0 -m t3
B2="$(cat "$TB" 2>/dev/null)"
[ -n "$B2" ] && [ "$B1" != "$B2" ] && echo "$B2" | grep -q '"baseline_arg": "yes"' \
  && ok "  ...baseline advanced and --baseline was passed" || bad "baseline advance ($B1 / $B2)"
echo 2 > "$T/trellis_rc"; ts 4
try "strict + trellis exit 2 with baseline -> blocked" 1 -m t4
[ "$(cat "$TB")" = "$B2" ] && ok "  ...baseline unchanged after fail" || bad "baseline moved on fail"
echo 1 > "$T/trellis_rc"; ts 5
try "strict + trellis exit 1 (tool error) -> passes" 0 -m t5
has "tool error, not a policy verdict" "  ...with a WARN"
[ "$(cat "$TB")" = "$B2" ] && ok "  ...baseline unchanged after tool error" || bad "baseline moved on error"
ts 6; ( cd "$R" && PATH="$BAREPATH" git commit -q -m t6 ) >"$T/out.log" 2>&1 \
  && { bad "strict + staged TS + no trellis on PATH -> blocked" "$T/out.log"; } \
  || { ok "strict + staged TS + no trellis on PATH -> blocked"; (cd "$R" && git reset -q --hard HEAD); }
has "trellis is not on PATH" "  ...names the missing tool"
R="$T/loose"; echo 2 > "$T/trellis_rc"; echo "export const a = 1;" > "$R/x.ts"; stage x.ts
try "non-strict + trellis exit 2 -> passes" 0 -m t7
has "WARN trellis policy failed" "  ...with a WARN"

# --- fix round 1 (audit) ---------------------------------------------------------
R="$T/strict"; echo 0 > "$T/trellis_rc"
printf '# audit\n> Example: VERDICT: PASS\nVERDICT: REJECT\n' > "$R/.artifacts/quoted.md"
big f1.py; try "F1 quoted 'VERDICT: PASS' before real REJECT -> blocked" 1 -m big -m "Audit: .artifacts/quoted.md"
has "says REJECT" "  ...says REJECT"
F='```'
printf '# audit\n> VERDICT: PASS\n' > "$R/.artifacts/q_only.md"
printf '# audit\n%s\nVERDICT: PASS\n%s\n' "$F" "$F" > "$R/.artifacts/f_only.md"
printf '# audit\n%s\nVERDICT: REJECT\n%s\nVERDICT: PASS\n' "$F" "$F" > "$R/.artifacts/f_rej.md"
big f1b.py; try "F1b quoted-only 'VERDICT: PASS' -> blocked" 1 -m big -m "Audit: .artifacts/q_only.md"
big f1c.py; try "F1c fenced-only 'VERDICT: PASS' -> blocked" 1 -m big -m "Audit: .artifacts/f_only.md"
big f1d.py; try "F1d real PASS after a fenced REJECT example -> passes" 0 -m big -m "Audit: .artifacts/f_rej.md"
printf '# audit\n~~~\nVERDICT: PASS\n~~~\n' > "$R/.artifacts/t_only.md"
printf '# audit\n~~~~\nVERDICT: REJECT\n~~~~\nVERDICT: PASS\n' > "$R/.artifacts/t_rej.md"
big f1e.py; try "F1e ~~~-fenced-only 'VERDICT: PASS' -> blocked" 1 -m big -m "Audit: .artifacts/t_only.md"
big f1f.py; try "F1f real PASS after a closed ~~~ REJECT example -> passes" 0 -m big -m "Audit: .artifacts/t_rej.md"
export AUDIT_MIN_LINES=999999
big f2.py; try "F2 AUDIT_MIN_LINES=999999 env ignored in strict -> blocked" 1 -m big
unset AUDIT_MIN_LINES
cp "$R/.harness" "$T/harness.bak"; echo "audit_min_lines=100" >> "$R/.harness"
big f2u.py; try "F2 UNSTAGED .harness audit_min_lines=100 has no effect -> blocked" 1 -m big
cp "$T/harness.bak" "$R/.harness"
for bogus in 1.5 99999999999999999999 0; do
  echo "audit_min_lines=$bogus" >> "$R/.harness"; stage .harness
  big "f2_$bogus.py"; try "F2 staged invalid audit_min_lines=$bogus -> default 20 -> blocked" 1 -m big
  has "WARN.*audit_min_lines" "  ...with a WARN"
done
echo "audit_min_lines=100" >> "$R/.harness"; stage .harness
big f2s.py; try "F2 STAGED audit_min_lines=100 -> 30-line change needs no trailer" 0 -m big
cp "$T/harness.bak" "$R/.harness"; stage .harness; now
try "F2 restore .harness (staged threshold 100 still covers this)" 0 -m restore
(cd "$R" && git rm -q s.py)
try "F3 deletion-only source change + unstaged .now.md -> blocked" 1 -m d1
has "update .now.md" "  ...names the .now.md rule"
echo 2 > "$T/trellis_rc"; (cd "$R" && git rm -q x.ts); now
try "F3 deleting a .ts file triggers trellis (exit 2 -> blocked)" 1 -m d2
has "trellis policy failed" "  ...names the trellis rule"
echo 0 > "$T/trellis_rc"
AWESOME_HARNESS="$T/nowhere"; echo "doc2" >> "$R/notes.md"; stage notes.md
try "F4 strict + harness hook missing -> shim blocks" 1 -m h1
has "BLOCKED: harness hook missing" "  ...names the missing hook"
R="$T/loose"; echo "doc" >> "$R/notes.md"; stage notes.md
try "F4 non-strict + harness hook missing -> WARN and pass" 0 -m h2
has "WARN harness hook missing" "  ...with a WARN"
AWESOME_HARNESS="$FH"
R="$T/partial"; mkdir -p "$R/.githooks"
( cd "$R" && git init -q && git config user.email t@t && git config user.name t \
  && git config core.hooksPath .githooks && printf '#!/bin/sh\nexit 0\n' > .githooks/commit-msg \
  && chmod +x .githooks/commit-msg && git add .githooks && git commit -q --no-verify -m root )
"$HERE/install.sh" "$R" > "$T/part.log"; rc=$?
[ $rc -ne 0 ] && grep -q REFUSED "$T/part.log" && [ ! -e "$R/.githooks/pre-commit" ] \
  && [ -z "$(cd "$R" && git status --porcelain)" ] \
  && ok "F5 refused commit-msg -> nothing installed (no partial pre-commit)" || bad "F5 partial install" "$T/part.log"

# --- fix round 3: strictness = .harness in index OR working tree ----------------
R="$T/strict"; rm "$R/.harness"; echo "z = 1" >> "$R/a.py"; stage a.py
try "F6 unstaged rm .harness still strict (.now.md gate blocks)" 1 -m s1
rm "$R/.harness"; big f6.py
try "F6 unstaged rm .harness still strict (commit-msg blocks big change)" 1 -m big
rm "$R/.harness"; AWESOME_HARNESS="$T/nowhere"; echo "doc3" >> "$R/notes.md"; stage notes.md
try "F6 unstaged rm .harness + missing hook -> shim still blocks" 1 -m s2
AWESOME_HARNESS="$FH"; (cd "$R" && git rm -q --cached .harness); echo "z = 2" >> "$R/a.py"; stage a.py
try "F6 git rm --cached .harness (file on disk) still strict -> blocked" 1 -m s3
(cd "$R" && git rm -q .harness); echo "z = 3" >> "$R/a.py"; stage a.py
try "F6 staged git rm .harness -> non-strict, commit allowed" 0 -m s4

# --- installer: commit-msg shim ------------------------------------------------
HK="$T/strict/.git/hooks"
grep -q awesome-harness-commit-msg-shim "$HK/commit-msg" && ok "commit-msg shim installed" \
  || bad "commit-msg shim installed"
"$HERE/install.sh" --uninstall "$T/strict" >/dev/null
[ ! -e "$HK/commit-msg" ] && [ ! -e "$HK/pre-commit" ] && ok "uninstall removes both shims" \
  || bad "uninstall removes both shims"

echo "---- $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
