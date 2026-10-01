#!/usr/bin/env python3
"""200-line ratchet for source files.

  ratchet.py                 check STAGED changes (index vs HEAD) - pre-commit mode
  ratchet.py --commit SHA    replay one commit (SHA vs its first parent) - dry-run mode

FAIL when a NEW source file is over the cap, or an EXISTING file that is over
the cap afterwards has MORE lines than before. Shrinking/unchanged big files
pass, so legacy debt never blocks a commit - it only cannot grow.
Exit 0 = pass, 1 = offenders printed, 2 = usage/git error.
"""
import fnmatch
import json
import subprocess
import sys

CAP = 200
SRC_EXT = {".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
           ".swift", ".java", ".c", ".h", ".cpp", ".sql"}
SKIP_DIRS = {"test", "tests", "__tests__", "node_modules", "dist", "build",
             ".venv", "venv", "vendor", "migrations"}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
             "Cargo.lock", "Gemfile.lock", "go.sum", "uv.lock", "bun.lockb"}


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stderr.decode(errors="replace"))
        sys.exit(2)
    return r


def load_ignore(rev):
    """ratchet_ignore list from .check-all.json at `rev` (':' = index)."""
    spec = ":.check-all.json" if rev == ":" else f"{rev}:.check-all.json"
    r = git("show", spec, check=False)
    if r.returncode != 0:
        return []
    try:
        val = json.loads(r.stdout.decode(errors="replace")).get("ratchet_ignore", [])
    except (ValueError, AttributeError):
        return []
    return [str(v) for v in val] if isinstance(val, list) else []


def is_ignored(path, ignore):
    for pat in ignore:
        p = pat.rstrip("/")
        if fnmatch.fnmatch(path, pat) or path == p or path.startswith(p + "/"):
            return True
    return False


def in_scope(path, ignore):
    parts = path.split("/")
    name = parts[-1]
    dot = name.rfind(".")
    ext = name[dot:].lower() if dot > 0 else ""  # Big.PY is still Python
    if ext not in SRC_EXT or name in LOCKFILES or name.endswith(".min.js"):
        return False
    if any(d in SKIP_DIRS for d in parts[:-1]):
        return False
    stem = name[:dot]
    if name.startswith("test_") or stem.endswith("_test") or \
            ".test." in name or ".spec." in name:
        return False
    return not is_ignored(path, ignore)


def count_lines(spec):
    """Line count of a blob spec like 'HEAD:path' or ':path'; None if absent."""
    r = git("cat-file", "-p", spec, check=False)
    if r.returncode != 0:
        return None
    if b"\0" in r.stdout[:8000]:
        return 0  # binary: never counts
    return len(r.stdout.splitlines())


def changes(diff_args):
    """Yield (status, old_path, new_path) for added/copied/modified/renamed."""
    out = git("diff", "--name-status", "-z", "-M", "--diff-filter=ACMR",
              *diff_args).stdout.decode(errors="replace").split("\0")
    i = 0
    while i < len(out) and out[i]:
        st = out[i][0]
        if st in "RC":
            yield st, out[i + 1], out[i + 2]
            i += 3
        else:
            yield st, out[i + 1], out[i + 1]
            i += 2


def offenders(old_rev, new_spec_prefix, diff_args, ignore):
    bad = []
    for st, old_path, new_path in changes(diff_args):
        if not in_scope(new_path, ignore):
            continue
        new_n = count_lines(new_spec_prefix + new_path)
        if new_n is None or new_n <= CAP:
            continue
        old_n = None
        if old_rev and st != "C":
            old_n = count_lines(f"{old_rev}:{old_path}")
        if old_n is None or new_n > old_n:
            bad.append((new_path, old_n, new_n))
    return bad


def has_rev(rev):
    return git("rev-parse", "--verify", "-q", rev + "^{commit}",
               check=False).returncode == 0


def main(argv):
    if len(argv) == 2 and argv[0] == "--commit":
        sha = argv[1]
        if not has_rev(sha):
            sys.stderr.write(f"ratchet: no such commit {sha}\n")
            return 2
        parent = sha + "^" if has_rev(sha + "^") else None
        if parent:
            diff_args = [parent, sha]
        else:  # root commit: diff against the empty tree
            empty = git("hash-object", "-t", "tree", "/dev/null").stdout.decode().strip()
            diff_args = [empty, sha]
        bad = offenders(parent, sha + ":", diff_args, load_ignore(sha))
    elif not argv:
        head = "HEAD" if has_rev("HEAD") else None
        if head:
            diff_args = ["--cached", head]
        else:
            empty = git("hash-object", "-t", "tree", "/dev/null").stdout.decode().strip()
            diff_args = ["--cached", empty]
        bad = offenders(head, ":", diff_args, load_ignore(":"))
    else:
        sys.stderr.write(__doc__)
        return 2

    if not bad:
        return 0
    print(f"ratchet: {len(bad)} source file(s) over the {CAP}-line cap grew:")
    for path, old_n, new_n in bad:
        before = "new" if old_n is None else str(old_n)
        print(f"  {path}: {before} -> {new_n} lines")
    print(f"  fix: split it, or shrink it below HEAD size "
          f"(new files must be <= {CAP} lines).")
    print("  exempt a path: add it to \"ratchet_ignore\" in .check-all.json")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
