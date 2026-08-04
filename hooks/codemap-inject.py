#!/usr/bin/env python3
"""SessionStart hook — inject the repo codemap.

Prints the whole-repo `.codemap` (built by tools/codemap.py) at session start
so the agent has a compressed map of every tracked file, its LOC, and its
symbols, instead of starting cold and reaching for exploratory grep/ls.

Fail-open everywhere: not a git repo, no tools/codemap.py, any exception ->
exit 0 printing nothing. Never crash, never exit non-zero.

Kill switch: CODEMAP_INJECT=off -> exit 0 silently.
"""
import os
import subprocess
import sys

HEADER_1 = "CODEMAP — the whole repo, compressed. Every tracked file, its LOC, and its symbols."
HEADER_2 = ("Use it INSTEAD of exploratory grep/ls. It is a map, not proof: verify any "
            "load-bearing claim with semgrep or a real read before asserting it.")


def _repo_root():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:
        return None


def _short_sha():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:
        return None


def _header_sha(text):
    # First line looks like: #CODEMAP <repo> @<sha> ...
    try:
        first = text.splitlines()[0]
        for tok in first.split():
            if tok.startswith("@"):
                return tok[1:]
    except Exception:
        pass
    return None


STALE_CODEMAP_CAP = 30000


def _l0_py(root):
    """Same resolution pattern as _codemap_py: prefer repo-local tools/l0.py,
    fall back to the global mirror at ~/.claude/tools/l0.py."""
    local = os.path.join(root, "tools", "l0.py")
    if os.path.isfile(local):
        return local
    fallback = os.environ.get(
        "L0_GLOBAL_PY",
        os.path.join(os.path.expanduser("~"), ".claude", "tools", "l0.py"),
    )
    if os.path.isfile(fallback):
        return fallback
    return None


def _run_l0(root, l0_py):
    try:
        out = subprocess.run(
            ["python3", l0_py],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return None
        text = out.stdout
        if not text:
            return None
        if "DILUTED INDEX UNAVAILABLE" in text:
            return None
        if len(text.encode("utf-8", "ignore")) < 300:
            return None
        return text
    except Exception:
        return None


def _codemap_py(root):
    """Return the path to codemap.py to run, or None if neither exists.

    Prefer the copy inside this repo (root/tools/codemap.py); fall back to
    the global mirror at ~/.claude/tools/codemap.py so repos that only have
    the hook installed (not the full tools/ dir) still get a codemap.
    """
    local = os.path.join(root, "tools", "codemap.py")
    if os.path.isfile(local):
        return local
    fallback = os.environ.get(
        "CODEMAP_GLOBAL_PY",
        os.path.join(os.path.expanduser("~"), ".claude", "tools", "codemap.py"),
    )
    if os.path.isfile(fallback):
        return fallback
    return None


def _regenerate(root, codemap_py):
    try:
        out = subprocess.run(
            ["python3", codemap_py],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return None
    except Exception:
        return None
    codemap_path = os.path.join(root, ".codemap")
    try:
        with open(codemap_path, "r") as f:
            return f.read()
    except Exception:
        return None


def _codemap_fallback(root):
    """Today's codemap path, unchanged, plus the stale-file byte cap guard."""
    codemap_py = _codemap_py(root)
    if not codemap_py:
        return None

    codemap_path = os.path.join(root, ".codemap")
    current_sha = _short_sha()

    existing = None
    existing_size = 0
    if os.path.isfile(codemap_path):
        try:
            existing_size = os.path.getsize(codemap_path)
        except Exception:
            existing_size = 0
        # Guard: never serve an on-disk .codemap larger than the cap, even
        # if it's fresh — a huge file is the exact bug this fixes.
        if existing_size > STALE_CODEMAP_CAP:
            return "CODEMAP SKIPPED: .codemap is {} bytes (cap {}) — run: python3 ~/.claude/tools/codemap.py".format(
                existing_size, STALE_CODEMAP_CAP
            )
        try:
            with open(codemap_path, "r") as f:
                existing = f.read()
        except Exception:
            existing = None

    stale = True
    if existing is not None and current_sha:
        stale = _header_sha(existing) != current_sha

    body = None
    if existing is None or stale:
        regenerated = _regenerate(root, codemap_py)
        if regenerated is not None:
            if len(regenerated.encode("utf-8", "ignore")) > STALE_CODEMAP_CAP:
                return "CODEMAP SKIPPED: .codemap is {} bytes (cap {}) — run: python3 ~/.claude/tools/codemap.py".format(
                    len(regenerated.encode("utf-8", "ignore")), STALE_CODEMAP_CAP
                )
            body = regenerated
        elif existing is not None:
            built_sha = _header_sha(existing) or "unknown"
            body = "#STALE built@{} HEAD@{}\n{}".format(
                built_sha, current_sha or "unknown", existing
            )
        else:
            body = None
    else:
        body = existing

    if not body:
        return None

    return "{}\n{}\n{}".format(HEADER_1, HEADER_2, body)


def build_output():
    """Return the text to print, or None to print nothing.

    Order: L0 (diluted index) first when it honestly produces a real named
    index for this repo; otherwise fall back to the whole-repo codemap.
    Each repo self-selects — no size threshold needed.
    """
    if os.environ.get("CODEMAP_INJECT") == "off":
        return None

    root = _repo_root()
    if not root:
        return None

    l0_py = _l0_py(root)
    if l0_py:
        l0_text = _run_l0(root, l0_py)
        if l0_text:
            return l0_text

    return _codemap_fallback(root)


def main():
    try:
        text = build_output()
        if text:
            print(text)
    except Exception:
        pass
    sys.exit(0)


def _selftest():
    import tempfile
    import shutil

    ok = True

    # --- Test 1: stale sha path -> regenerates and drops the stale prefix
    # (relies on the live repo's own .codemap; this test runs from within
    # the repo so tools/codemap.py and git are both real.)
    root = _repo_root()
    if root:
        codemap_path = os.path.join(root, ".codemap")
        had_existing = os.path.isfile(codemap_path)
        backup = None
        if had_existing:
            with open(codemap_path, "r") as f:
                backup = f.read()
        try:
            # Force a stale header.
            with open(codemap_path, "w") as f:
                f.write("#CODEMAP fake @deadbeef 0f/0L\nstale body\n")
            out = build_output()
            current = _short_sha()
            if out is None or (current and current not in out.splitlines()[2]):
                print("FAIL: stale-sha path did not regenerate a fresh codemap")
                ok = False
            else:
                print("PASS: stale-sha path regenerates")
        except Exception as e:
            print("FAIL: stale-sha path raised {}".format(e))
            ok = False
        finally:
            if backup is not None:
                with open(codemap_path, "w") as f:
                    f.write(backup)
            elif os.path.isfile(codemap_path):
                os.remove(codemap_path)

    # --- Test 2: both repo copy and global copy missing -> print nothing, exit 0
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmpdir, capture_output=True)
        this_script = os.path.abspath(__file__)
        missing_global = os.path.join(tmpdir, "no-such-global-codemap.py")
        env = dict(os.environ, CODEMAP_GLOBAL_PY=missing_global)
        out = subprocess.run(
            ["python3", this_script], cwd=tmpdir, capture_output=True, text=True, env=env,
        )
        if out.stdout.strip() != "" or out.returncode != 0:
            print("FAIL: both-missing path printed something or exited non-zero")
            ok = False
        else:
            print("PASS: both-missing path prints nothing")
    except Exception as e:
        print("FAIL: both-missing path raised {}".format(e))
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # --- Test 3: repo copy missing, global copy present -> falls back and produces a map
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-q", "-m", "init"], cwd=tmpdir, capture_output=True)
        this_script = os.path.abspath(__file__)
        real_root = _repo_root()
        global_codemap_py = os.path.join(real_root, "tools", "codemap.py") if real_root else None
        if not global_codemap_py or not os.path.isfile(global_codemap_py):
            print("PASS: fallback path skipped (no tools/codemap.py available to inject as global)")
        else:
            env = dict(os.environ, CODEMAP_GLOBAL_PY=global_codemap_py)
            out = subprocess.run(
                ["python3", this_script], cwd=tmpdir, capture_output=True, text=True, env=env,
            )
            if out.stdout.strip() == "" or out.returncode != 0:
                print("FAIL: fallback path (repo missing, global present) produced no map")
                ok = False
            else:
                print("PASS: fallback path (repo missing, global present) produces a map")
    except Exception as e:
        print("FAIL: fallback path raised {}".format(e))
        ok = False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
