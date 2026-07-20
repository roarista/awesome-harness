#!/usr/bin/env bash
# Runtime proof for the Codex adapter.  Everything, including auth state and
# hook logs, is isolated beneath mktemp and removed on exit.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
if ! command -v codex >/dev/null 2>&1; then
  echo "SKIP test_codex_runtime_smoke: codex is not on PATH" >&2
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
ORIGINAL_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
AUTH_SOURCE="$ORIGINAL_CODEX_HOME/auth.json"
if [ ! -f "$AUTH_SOURCE" ]; then
  echo "SKIP test_codex_runtime_smoke: no local Codex auth.json for disposable session" >&2
  exit 0
fi
export CODEX_HOME="$TMP/codex-home"
export HOME="$TMP/home"
export AWESOME_HARNESS_SMOKE_LOG="$TMP/hook-events.jsonl"
REPO="$TMP/repo"
mkdir -p "$HOME" "$CODEX_HOME" "$REPO"
# Codex needs credentials even though its config and every artifact remain
# temporary. This copy is mode 600, never printed, and is removed by the trap.
cp "$AUTH_SOURCE" "$CODEX_HOME/auth.json"
chmod 600 "$CODEX_HOME/auth.json"
git -C "$REPO" init -q
git -C "$REPO" config user.email smoke@example.invalid
git -C "$REPO" config user.name smoke
printf '%s\n' '# fixture' > "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -qm fixture

"$SRC/install.sh" --codex
"$SRC/install-repo.sh" --codex "$REPO"

# Add a test-only observer alongside the installed adapter. It writes only the
# tool name to a temp log and intentionally emits no hook response.
PROBE="$TMP/probe.py"
printf '%s\n' \
  '#!/usr/bin/env python3' \
  'import json, os, sys' \
  'payload = json.load(sys.stdin)' \
  'with open(os.environ["AWESOME_HARNESS_SMOKE_LOG"], "a", encoding="utf-8") as out:' \
  '    out.write(json.dumps({"tool_name": payload.get("tool_name")}, sort_keys=True) + "\n")' \
  > "$PROBE"
chmod +x "$PROBE"
python3 - "$REPO/.codex/hooks.json" "$PROBE" <<'PY'
import json
import sys

path, probe = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
for entry in data["hooks"]["PreToolUse"]:
    if entry.get("matcher") in {"^Bash$", "^apply_patch$"}:
        entry["hooks"].append({"type": "command", "command": f'python3 "{probe}"'})
with open(path, "w", encoding="utf-8") as out:
    json.dump(data, out, indent=2, sort_keys=True)
    out.write("\n")
PY

# `--dangerously-bypass-hook-trust` is confined to this disposable repository.
# The prompt asks for exactly one harmless shell action plus one tiny patch.
set +e
codex exec --ephemeral --dangerously-bypass-approvals-and-sandbox \
  --dangerously-bypass-hook-trust -C "$REPO" \
  'Run exactly one harmless Bash command: printf smoke-bash. Then use apply_patch to create proof.txt containing exactly smoke-patch followed by a newline. Do not edit any other file. Reply only DONE.' \
  >"$TMP/codex.out" 2>"$TMP/codex.err"
CODEX_RC=$?
set -e
if [ "$CODEX_RC" -ne 0 ]; then
  cat "$TMP/codex.err" >&2
  echo "FAIL test_codex_runtime_smoke: codex exec rc=$CODEX_RC" >&2
  exit "$CODEX_RC"
fi

if [ ! -f "$REPO/proof.txt" ] || [ "$(cat "$REPO/proof.txt" 2>/dev/null || true)" != 'smoke-patch' ]; then
  cat "$TMP/codex.out" >&2
  cat "$TMP/codex.err" >&2
  echo "FAIL test_codex_runtime_smoke: expected proof.txt with smoke-patch" >&2
  exit 1
fi
FILES="$(find "$REPO" -path "$REPO/.git" -prune -o -type f -print | sed "s#^$REPO/##" | sort)"
EXPECTED_FILES=$'.codex/awesome-harness.json\n.codex/hooks.json\nREADME.md\nproof.txt'
if [ "$FILES" != "$EXPECTED_FILES" ]; then
  echo "FAIL test_codex_runtime_smoke: unexpected files beyond installer config and fixture output: $FILES" >&2
  exit 1
fi
python3 - "$AWESOME_HARNESS_SMOKE_LOG" <<'PY'
import json
import sys

events = [json.loads(line)["tool_name"] for line in open(sys.argv[1], encoding="utf-8")]
missing = {"Bash", "apply_patch"}.difference(events)
if missing:
    raise SystemExit(f"missing hook events: {sorted(missing)}; got {events}")
PY
echo "PASS test_codex_runtime_smoke"
