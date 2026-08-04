#!/usr/bin/env python3
"""One area, on demand: file list + LOC + [entry] markers. HARD CAP 8,000 bytes.
Usage: <this file's path> <area> -- run with no args for the exact path.
"""
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from exclude import is_excluded  # noqa: E402

CAP = 8000


def _sibling_ref(name, root):
    """Resolve l1.py's sibling tool (skeleton.py) relative to l1.py's own
    location, not a hardcoded guess. Returns a string to print, or a
    stdlib-only fallback path if the sibling can't be found on disk."""
    here = Path(__file__).resolve().parent
    sib = here / name
    if not sib.is_file():
        return "tools/{} (not installed)".format(name)
    root_path = Path(root).resolve() if root else None
    if root_path is not None:
        try:
            rel = sib.relative_to(root_path)
            return str(rel)
        except ValueError:
            pass
    home = str(Path.home())
    sib_str = str(sib)
    if sib_str.startswith(home):
        return "~" + sib_str[len(home):]
    return sib_str

SRC_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".sql")
PY_MAIN_RE = re.compile(r"""^\s*if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)


def get_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        print("Not inside a git repo.")
        sys.exit(1)
    return out.stdout.strip()


def is_source(relpath):
    return os.path.splitext(relpath)[1] in SRC_EXTS


def area_of(relpath):
    parts = relpath.split("/")
    if len(parts) >= 3:
        return parts[0] + "/" + parts[1]
    if len(parts) == 2:
        return parts[0]
    return "."


def count_lines(path):
    try:
        with open(path, "r", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def is_entry(full, ext, pkg_scripts_dirs):
    if ext == ".py":
        try:
            with open(full, "r", errors="replace") as fh:
                return bool(PY_MAIN_RE.search(fh.read()))
        except OSError:
            return False
    return False


def main():
    root = get_root()

    if len(sys.argv) != 2:
        here_ref = _sibling_ref("l1.py", root)
        print("Usage: {} <area>".format(here_ref))
        sys.exit(1)
    requested = sys.argv[1]

    ls = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True)
    tracked = [l for l in ls.stdout.splitlines() if l]
    src_files = [f for f in tracked if is_source(f) and not is_excluded(f)]

    by_area = defaultdict(list)
    for f in src_files:
        by_area[area_of(f)].append(f)

    if requested not in by_area:
        valid = sorted(by_area.keys(), key=lambda a: -len(by_area[a]))
        print("Unknown area: {}".format(requested))
        print("Valid areas ({} total, showing top 15):".format(len(valid)))
        for a in valid[:15]:
            print("  {} ({} files)".format(a, len(by_area[a])))
        if len(valid) > 15:
            print("  ... and {} more".format(len(valid) - 15))
        sys.exit(1)

    files = sorted(by_area[requested])
    rows = []
    for f in files:
        full = os.path.join(root, f)
        ext = os.path.splitext(f)[1]
        loc = count_lines(full)
        entry = is_entry(full, ext, None)
        rows.append((f, loc, entry))

    # largest files first, per spec, so truncation drops smallest last.
    rows.sort(key=lambda r: -r[1])

    header = "Area {} ({} files):\n".format(requested, len(rows))
    lines = [header.rstrip("\n")]
    dropped = 0
    used = len(header.encode("utf-8"))

    kept_rows = []
    for f, loc, entry in rows:
        text = "  {}  {} LOC{}".format(f, loc, "  [entry]" if entry else "")
        text_bytes = len(text.encode("utf-8")) + 1
        trailer_reserve = 60
        if used + text_bytes + trailer_reserve > CAP:
            dropped += 1
            continue
        kept_rows.append(text)
        used += text_bytes

    lines += kept_rows
    if dropped:
        sk_ref = _sibling_ref("skeleton.py", root)
        lines.append("#TRUNCATED {} more files, run: {} -r {}".format(
            dropped, sk_ref, requested))

    out = "\n".join(lines) + "\n"
    print(out, end="")
    sys.exit(0)


if __name__ == "__main__":
    main()
