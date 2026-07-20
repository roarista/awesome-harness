#!/usr/bin/env bash
# Runnable fixture for the explicit Codex installer.  Uses no real user config.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CODEX_HOME="$TMP/codex-home"
FAKE_HOME="$TMP/fake-home"
mkdir -p "$FAKE_HOME/.claude"
printf '%s\n' '{"keep":"claude"}' > "$FAKE_HOME/.claude/settings.json"

repo(){ mkdir -p "$1"; git -C "$1" init -q; git -C "$1" config user.email test@example.invalid; git -C "$1" config user.name test; }
REPO_A="$TMP/repo-a"; REPO_B="$TMP/repo-b"
repo "$REPO_A"; repo "$REPO_B"
mkdir -p "$REPO_B/.codex"
cat > "$REPO_B/.codex/hooks.json" <<'EOF'
{"metadata":{"keep":true},"hooks":{"PreToolUse":[{"matcher":"other","hooks":[{"type":"command","command":"echo keep"}]},{"matcher":"exec_command","hooks":[{"type":"command","command":"python3 \"$(git rev-parse --show-toplevel)/.codex/awesome-harness/pre_tool_use.py\""}]}]}}
EOF

HOME="$FAKE_HOME" "$SRC/install.sh" --codex > "$TMP/global.out"
ADAPTER="$(python3 -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).resolve())' "$CODEX_HOME/awesome-harness/hooks/pre_tool_use.py")"
test -f "$ADAPTER"
SKILL="$CODEX_HOME/skills/caveman/SKILL.md"
test -f "$SKILL"
cmp -s "$SRC/codex/skills/caveman/SKILL.md" "$SKILL"
test ! -e "$CODEX_HOME/awesome-harness/skills/caveman/SKILL.md"
test "$(cat "$FAKE_HOME/.claude/settings.json")" = '{"keep":"claude"}'
test "$(find "$FAKE_HOME/.claude" -type f | sed "s#^$FAKE_HOME/.claude/##" | sort)" = 'settings.json'
HOME="$FAKE_HOME" "$SRC/install.sh" --dry-run > "$TMP/claude-dry.out"
grep -q 'wiring ~/.claude/settings.json' "$TMP/claude-dry.out"
test "$(cat "$FAKE_HOME/.claude/settings.json")" = '{"keep":"claude"}'
HOME="$FAKE_HOME" "$SRC/install.sh" --codex > "$TMP/global-second.out"

HOME="$FAKE_HOME" "$SRC/install-repo.sh" --codex "$REPO_A" > "$TMP/repo-a.out"
HOME="$FAKE_HOME" "$SRC/install-repo.sh" --codex "$REPO_A" > "$TMP/repo-a-second.out"
HOME="$FAKE_HOME" "$SRC/install-repo.sh" --codex "$REPO_B" > "$TMP/repo-b.out"
HOME="$FAKE_HOME" "$SRC/install-repo.sh" --codex "$REPO_B" > "$TMP/repo-b-second.out"
python3 - "$REPO_A/.codex/hooks.json" "$REPO_B/.codex/hooks.json" "$ADAPTER" <<'PY'
import json, sys
for name in sys.argv[1:3]:
    data = json.load(open(name))
    pre = data["hooks"]["PreToolUse"]
    assert {x["matcher"] for x in pre} >= {"^Bash$", "^apply_patch$"}
    for matcher in ("^Bash$", "^apply_patch$"):
        entry = next(x for x in pre if x["matcher"] == matcher)
        assert any(h["command"] == f'python3 "{sys.argv[3]}"' for h in entry["hooks"])
data = json.load(open(sys.argv[2]))
assert data["metadata"] == {"keep": True}
pre = data["hooks"]["PreToolUse"]
assert any(x["matcher"] == "other" for x in pre)
assert not any(x["matcher"] == "exec_command" and len(x["hooks"]) == 1 and "awesome-harness/pre_tool_use.py" in x["hooks"][0]["command"] for x in pre)
PY
test -f "$REPO_A/.codex/awesome-harness.json"
test "$(cat "$FAKE_HOME/.claude/settings.json")" = '{"keep":"claude"}'
test "$(find "$REPO_B/.codex" -name 'hooks.json.bak.*' | wc -l | tr -d ' ')" = 1

before_a="$(cat "$REPO_A/.codex/hooks.json")"; before_marker="$(cat "$REPO_A/.codex/awesome-harness.json")"
stamp_a="$(stat -f %m "$REPO_A/.codex/hooks.json")"
sleep 1
HOME="$FAKE_HOME" "$SRC/install-repo.sh" --codex --dry-run "$REPO_A" > "$TMP/dry-repo.out"
test "$(cat "$REPO_A/.codex/hooks.json")" = "$before_a"
test "$(cat "$REPO_A/.codex/awesome-harness.json")" = "$before_marker"
test "$(stat -f %m "$REPO_A/.codex/hooks.json")" = "$stamp_a"
grep -q 'DRY:' "$TMP/dry-repo.out"
HOME="$FAKE_HOME" "$SRC/install.sh" --codex --dry-run > "$TMP/dry-global.out"
grep -q 'DRY:' "$TMP/dry-global.out"
adapter_before="$(cat "$ADAPTER")"; adapter_stamp="$(stat -f %m "$ADAPTER")"
skill_before="$(cat "$SKILL")"; skill_stamp="$(stat -f %m "$SKILL")"
sleep 1
HOME="$FAKE_HOME" "$SRC/install.sh" --codex --dry-run > "$TMP/dry-global-second.out"
test "$(cat "$ADAPTER")" = "$adapter_before"
test "$(stat -f %m "$ADAPTER")" = "$adapter_stamp"
test "$(cat "$SKILL")" = "$skill_before"
test "$(stat -f %m "$SKILL")" = "$skill_stamp"

printf '{bad\n' > "$TMP/bad.json"
if python3 "$SRC/scripts/merge_codex_hooks.py" "$TMP/bad.json" "$ADAPTER" > /dev/null 2>&1; then
  echo "malformed JSON unexpectedly accepted" >&2; exit 1
fi
echo "PASS test_codex_install"
