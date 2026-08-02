#!/usr/bin/env bash
# c6-vestigial.sh — "what does this repo DECLARE that it never actually uses?"
# Prevents: P1 (agent writes `from tenacity import retry` because tenacity is in
#           pyproject.toml — and nothing has ever imported it).
#
# This is the class NO tool covered: semgrep sees code, not manifests; graphify and
# repowise both build graphs FROM code, so a declared-and-never-imported dependency is
# invisible to all three. It takes a manifest ∩ import-set difference, which is why it
# is its own chain rather than a rule.
#
# Usage: REPO=/path tools/chains/c6-vestigial.sh
set -euo pipefail
CHAIN_NAME=c6-vestigial
. "$(dirname "$0")/_lib.sh"
full_file c6-vestigial >/dev/null
echo "== c6-vestigial $REPO_NAME" >> "$FULL"

DEPS=$(python3 - "$REPO" <<'PY'
import sys, os, json, re
root = sys.argv[1]; out = []
p = os.path.join(root, "pyproject.toml")
if os.path.exists(p):
    deps = []
    try:
        try:
            import tomllib                      # py3.11+
        except ImportError:
            import tomli as tomllib             # py3.9/3.10 with tomli installed
        d = tomllib.load(open(p, "rb"))
        deps = list((d.get("project") or {}).get("dependencies") or [])
        for grp in ((d.get("project") or {}).get("optional-dependencies") or {}).values():
            deps += list(grp)
    except Exception:
        # FALLBACK: no TOML parser on this interpreter (measured: system python3.9 on macOS).
        # Scrape every quoted requirement inside a dependencies = [...] block. Reporting a
        # parse failure as "no dependencies" would be the exact P5/P6 shape this chain exists to kill.
        txt = open(p, errors="ignore").read()
        for blk in re.findall(r"dependencies\s*=\s*\[(.*?)\]", txt, re.S):
            deps += re.findall(r"[\"']([^\"']+)[\"']", blk)
        print("NOTE pyproject parsed by regex fallback (no tomllib/tomli)", file=sys.stderr)
    for x in deps:
        out.append(("py", re.split(r"[<>=!\[; ]", x.strip())[0]))
r = os.path.join(root, "requirements.txt")
if os.path.exists(r):
    for line in open(r, errors="ignore"):
        line = line.strip()
        if line and not line.startswith(("#", "-")):
            out.append(("py", re.split(r"[<>=!\[; ]", line)[0]))
j = os.path.join(root, "package.json")
if os.path.exists(j):
    try:
        d = json.load(open(j))
        for k in ("dependencies", "devDependencies"):
            out += [("js", n) for n in (d.get(k) or {})]
    except Exception as e:
        print("PARSE_ERROR package.json", e, file=sys.stderr)
seen = set()
for lang, n in out:
    if n and (lang, n) not in seen:
        seen.add((lang, n)); print(lang, n)
PY
) 2>>"$FULL" || true

ND=$(printf '%s' "$DEPS" | grep -c . || true)
if [ "$ND" = 0 ]; then
  say "PREFLIGHT FAIL: no dependencies parsed from pyproject.toml/requirements.txt/package.json."
  say "  A zero here means 'could not read the manifest', NOT 'no vestigial deps' (P5/P6)."
  exit 0
fi
say "PREFLIGHT ok: $ND declared dependencies parsed from this repo's manifests."

VEST=""; NV=0
{ echo; echo "== per-dependency import counts (live tree only; .claude/worktrees excluded)"; } >> "$FULL"
while read -r lang name; do
  [ -n "${name:-}" ] || continue
  # PyPI distribution name != import name for a long tail of packages. Without this map
  # the chain cries wolf on pillow/opencv-python/pyyaml and gets ignored, which is worse
  # than not running it at all.
  case "$name" in
    pillow|Pillow) mod=PIL ;; opencv-python|opencv-python-headless) mod=cv2 ;;
    python-dotenv) mod=dotenv ;; pyyaml|PyYAML) mod=yaml ;;
    beautifulsoup4) mod=bs4 ;; python-dateutil) mod=dateutil ;;
    google-genai) mod='google\.genai|google' ;; google-generativeai) mod='google\.generativeai|google' ;;
    scikit-learn) mod=sklearn ;; scikit-image) mod=skimage ;;
    protobuf) mod=google ;; msgpack-python) mod=msgpack ;;
    pytest-*|ruff|black|mypy|pyright|isort|pre-commit) mod="__TOOLING__" ;;
    *) mod="$(printf '%s' "$name" | tr '-' '_')" ;;
  esac
  if [ "$mod" = "__TOOLING__" ]; then echo "py $name SKIPPED (dev tooling, invoked as a CLI)" >> "$FULL"; continue; fi
  base="$(printf '%s' "$name" | sed 's|^@[^/]*/||')"
  if [ "$lang" = py ]; then
    n=$({ grep -rIn --include='*.py' $EXCL -cE "^[[:space:]]*(import|from) ($mod|$name)\b" "$REPO" 2>/dev/null || true; } \
        | awk -F: '{s+=$2} END{print s+0}')
  else
    n=$({ grep -rIn --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' $EXCL \
          -cE "(from|require\()[[:space:]]*['\"]($name|$base)" "$REPO" 2>/dev/null || true; } \
        | awk -F: '{s+=$2} END{print s+0}')
  fi
  echo "$lang $name imports=$n" >> "$FULL"
  if [ "$n" -eq 0 ] 2>/dev/null; then VEST="$VEST$lang $name"$'\n'; NV=$((NV+1)); fi
done <<< "$DEPS"

say "VESTIGIAL: $NV of $ND declared dependencies are imported ZERO times in the live tree."
printf '%s' "$VEST" | grep . | head -8 | while read -r l; do echo "  · $l"; done > "$OUTDIR/.h6" || true
while read -r l; do say "$l"; done < "$OUTDIR/.h6"; rm -f "$OUTDIR/.h6"
[ "$NV" -gt 8 ] && say "  … $((NV-8)) more in FULL"
say "CAVEAT: a hit can still be a transitive pin, a CLI-only tool, or a plugin loaded by name."
say "  Never delete on this probe alone — but NEVER import one either (that is P1)."
exit 0
