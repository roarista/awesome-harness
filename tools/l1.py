#!/usr/bin/env python3
"""One area, on demand: file list + LOC + [entry] markers. HARD CAP 8,000 bytes.
Usage: python3 tools/l1.py <area>
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

CAP = 8000

EXCLUDE_COMPONENTS = {
    "docs", "tests", "test", "__tests__", "_legacy", ".artifacts", ".scratch",
    ".planning", ".claude", ".mulch", "node_modules", ".github", ".agents",
    "assets", "public", "research", "knowledge", "evals", "legacy",
}
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


def is_excluded(relpath):
    parts = relpath.split("/")[:-1]
    return any(p in EXCLUDE_COMPONENTS for p in parts)


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
    if len(sys.argv) != 2:
        print("Usage: python3 tools/l1.py <area>")
        sys.exit(1)
    requested = sys.argv[1]

    root = get_root()
    ls = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, text=True)
    tracked = [l for l in ls.stdout.splitlines() if l]
    src_files = [f for f in tracked if is_source(f) and not is_excluded(f)]

    by_area = defaultdict(list)
    for f in src_files:
        by_area[area_of(f)].append(f)

    if requested not in by_area:
        valid = sorted(by_area.keys(), key=lambda a: -len(by_area[a]))
        print("Unknown area: {}".format(requested))
        print("Valid areas:")
        for a in valid:
            print("  {} ({} files)".format(a, len(by_area[a])))
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
        lines.append("#TRUNCATED {} more files, run: tools/skeleton.py -r {}".format(
            dropped, requested))

    out = "\n".join(lines) + "\n"
    print(out, end="")
    sys.exit(0)


if __name__ == "__main__":
    main()
