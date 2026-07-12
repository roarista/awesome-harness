#!/usr/bin/env python3
"""Manifest-sha hook-integrity guard — guard the guards.

Detects if any hook script or settings.json was silently changed, added, or
removed since the last blessed baseline. A neutered guard (someone edited a
hook to a no-op, or swapped settings.json) is otherwise invisible; this surfaces
it LOUDLY to Ro at SessionStart.

Watched set: every top-level *.py / *.sh / *.js in ~/.claude/hooks/ (NON-
recursive; state/ and manifest/ are subdirs and are skipped by construction)
plus ~/.claude/settings.json. Baseline: one "sha  path" per line at
~/.claude/hooks/manifest/hooks.sha256.

Modes:
  * default (SessionStart): compare current vs baseline. Missing baseline →
    create silently, exit 0. MISMATCH → alert via the hook JSON "systemMessage"
    field (the one field shown to the user), naming each changed/added/removed
    file. Always exit 0 — advisory only. SessionStart fires once/session, so a
    real tamper alert is not spammy.
  * --bless → re-baseline to current hashes, print count, exit 0.
  * --selftest → temp-dir asserts, exit 0/1.

Kill-switch FILE-level: env MANIFEST_GUARD=0 → no-op. MANIFEST_GUARD=warn
(default) = alert only. No enforce/block mode — advisory by design. Fail-open.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

HOOKS_DIR = Path.home() / ".claude" / "hooks"
SETTINGS = Path.home() / ".claude" / "settings.json"
MANIFEST_DIR = HOOKS_DIR / "manifest"
MANIFEST = MANIFEST_DIR / "hooks.sha256"
EXTS = (".py", ".sh", ".js")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _watched(hooks_dir: Path, settings: Path) -> list:
    """Sorted list of absolute paths under watch (top-level hook scripts + settings)."""
    paths = []
    try:
        for p in sorted(hooks_dir.iterdir()):
            if p.is_file() and p.suffix in EXTS:
                paths.append(p)
    except OSError:
        pass
    if settings.is_file():
        paths.append(settings)
    return paths


def _current(hooks_dir: Path, settings: Path) -> dict:
    out = {}
    for p in _watched(hooks_dir, settings):
        try:
            out[str(p)] = _sha256(p)
        except OSError:
            pass
    return out


def _read_baseline(manifest: Path) -> dict:
    out = {}
    try:
        for line in manifest.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            sha, _, path = line.partition("  ")
            if sha and path:
                out[path] = sha
    except OSError:
        pass
    return out


def _write_baseline(manifest: Path, cur: dict) -> int:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha}  {path}" for path, sha in sorted(cur.items())]
    manifest.write_text("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)


def _diff(baseline: dict, cur: dict):
    changed = sorted(p for p in cur if p in baseline and cur[p] != baseline[p])
    added = sorted(p for p in cur if p not in baseline)
    removed = sorted(p for p in baseline if p not in cur)
    return changed, added, removed


def _short(p: str) -> str:
    home = str(Path.home())
    return p.replace(home, "~") if p.startswith(home) else p


def bless(hooks_dir=HOOKS_DIR, settings=SETTINGS, manifest=MANIFEST) -> int:
    cur = _current(hooks_dir, settings)
    return _write_baseline(manifest, cur)


def check(hooks_dir=HOOKS_DIR, settings=SETTINGS, manifest=MANIFEST):
    """Return (changed, added, removed) or None if baseline was just created."""
    cur = _current(hooks_dir, settings)
    if not manifest.is_file():
        _write_baseline(manifest, cur)
        return None
    baseline = _read_baseline(manifest)
    return _diff(baseline, cur)


def main() -> None:
    mode = os.environ.get("MANIFEST_GUARD", "warn")
    if mode == "0":
        return
    # consume stdin if present (SessionStart payload); we don't need it
    try:
        sys.stdin.read()
    except Exception:
        pass
    result = check()
    if result is None:
        return  # baseline created this run
    changed, added, removed = result
    if not (changed or added or removed):
        return
    parts = ["HOOK-INTEGRITY ALERT: watched hook/settings files differ from the blessed baseline."]
    if changed:
        parts.append("CHANGED:\n  " + "\n  ".join(_short(p) for p in changed))
    if added:
        parts.append("ADDED:\n  " + "\n  ".join(_short(p) for p in added))
    if removed:
        parts.append("REMOVED:\n  " + "\n  ".join(_short(p) for p in removed))
    parts.append("If this was you, re-bless: python3 ~/.claude/hooks/manifest-guard.py --bless")
    print(json.dumps({"systemMessage": "\n".join(parts)}))


def _selftest() -> None:
    import tempfile
    d = Path(tempfile.mkdtemp())
    hooks = d / "hooks"
    hooks.mkdir()
    manifest = d / "manifest" / "hooks.sha256"
    settings = d / "settings.json"
    # N files
    (hooks / "a.py").write_text("print(1)\n")
    (hooks / "b.sh").write_text("echo hi\n")
    (hooks / "c.js").write_text("console.log(1)\n")
    (hooks / "ignore.txt").write_text("not watched\n")
    settings.write_text('{"x":1}\n')

    n = _write_baseline(manifest, _current(hooks, settings))
    assert n == 4, f"expected 4 watched (3 scripts + settings), got {n}"
    # clean
    ch, ad, rm = _diff(_read_baseline(manifest), _current(hooks, settings))
    assert not (ch or ad or rm), "fresh baseline should be clean"
    # mutate one byte
    (hooks / "a.py").write_text("print(2)\n")
    ch, ad, rm = _diff(_read_baseline(manifest), _current(hooks, settings))
    assert ch == [str(hooks / "a.py")], f"mismatch should name a.py, got {ch}"
    assert not ad and not rm, "only a change, no add/remove"
    # re-bless → clean again
    _write_baseline(manifest, _current(hooks, settings))
    ch, ad, rm = _diff(_read_baseline(manifest), _current(hooks, settings))
    assert not (ch or ad or rm), "after re-bless should be clean"
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        try:
            _selftest()
        except AssertionError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
    elif "--bless" in sys.argv:
        try:
            count = bless()
            print(f"blessed: {count} files recorded in {_short(str(MANIFEST))}")
        except Exception as e:
            print(f"bless error: {e}")
        sys.exit(0)
    else:
        try:
            main()
        except Exception:
            sys.exit(0)  # fail-open
