#!/usr/bin/env python3
"""Verbatim per-file signature skeletons, stdlib only, zero fabrication.
Usage: python3 tools/skeleton.py <path> [<path>...] [-r|--recursive]
"""
import ast
import os
import re
import subprocess
import sys

SKIP_DIRS = {
    "node_modules", ".venv", "dist", "build", "__pycache__", ".git",
    ".artifacts", ".scratch", "_legacy",
}
SKIP_PREFIXES = ("_archive",)
TS_RE = re.compile(
    r"^(export\s+.*|function\s+\w.*|class\s+\w.*|const\s+\w+\s*=\s*\(.*|"
    r"const\s+\w+\s*=\s*async\s*\(.*|const\s+\w+\s*=\s*<[^=>]*>\s*\(.*|"
    r"const\s+\w+\s*:\s*[\w.]+(?:<[^=]*>)?\s*=\s*\(.*|"
    r"interface\s+\w.*|type\s+\w+\s*=.*)$"
)
SH_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")
SQL_RE = re.compile(
    r"^\s*(CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|INDEX|UNIQUE\s+INDEX|FUNCTION|VIEW|"
    r"POLICY|TRIGGER)\b.*|ALTER\s+TABLE\b.*)$",
    re.IGNORECASE,
)
SUPPORTED_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".sql")
DEFAULT_MAX_BYTES = 16000
MAX_SIG_LINE = 400

def should_skip_dir(name):
    return name in SKIP_DIRS or any(name.startswith(p) for p in SKIP_PREFIXES)

def git_files(start):
    """Returns files for a git repo, or None if `start` is not one."""
    root = subprocess.run(
        ["git", "-C", start, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True).stdout.strip()
    if not root:
        return None
    rel_start = os.path.relpath(os.path.abspath(start), root)
    args = ["git", "-C", root, "ls-files"]
    if rel_start != ".":
        args += ["--", rel_start]
    out = subprocess.run(args, capture_output=True, text=True)
    return [
        os.path.join(root, rel) for rel in out.stdout.splitlines()
        if not any(should_skip_dir(p) for p in rel.split("/")[:-1])
    ]

def walk_files(start, recursive):
    files = []
    if recursive:
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            files += [os.path.join(dirpath, fn) for fn in filenames]
    else:
        for fn in sorted(os.listdir(start)):
            full = os.path.join(start, fn)
            if os.path.isfile(full):
                files.append(full)
    return files

def resolve_paths(paths, recursive):
    resolved, seen = [], set()

    def add(f):
        ap = os.path.abspath(f)
        if ap not in seen:
            seen.add(ap)
            resolved.append(ap)

    for p in paths:
        if not os.path.exists(p):
            continue
        if os.path.isfile(p):
            add(p)
            continue
        gfiles = git_files(p)
        if gfiles is not None:
            target = os.path.abspath(p)
            for f in gfiles:
                if recursive:
                    if f != target and not f.startswith(target + os.sep):
                        continue
                elif os.path.dirname(f) != target:
                    continue
                add(f)
        else:
            for f in walk_files(p, recursive):
                add(f)
    return resolved

def py_skeleton(src):
    sigs = []

    def visit(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = ast.unparse(child.args)
                prefix = "async def" if isinstance(child, ast.AsyncFunctionDef) else "def"
                ret = " -> " + ast.unparse(child.returns) if child.returns is not None else ""
                sigs.append((child.lineno, "{} {}({}){}".format(prefix, child.name, args, ret)))
            elif isinstance(child, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in child.bases)
                sig = "class {}({})".format(child.name, bases) if bases else "class {}".format(child.name)
                sigs.append((child.lineno, sig))
                visit(child)

    visit(ast.parse(src))  # raises SyntaxError on bad source
    sigs.sort(key=lambda t: t[0])
    return sigs

def ts_skeleton(lines):
    sigs = []
    for i, line in enumerate(lines, 1):
        if len(line) > MAX_SIG_LINE:
            m = TS_RE.match(line[:MAX_SIG_LINE])
            if m:
                sigs.append((i, "#SIG-TOO-LONG ({} chars)".format(len(line.rstrip("\n")))))
            continue
        m = TS_RE.match(line)
        if m:
            text = m.group(1).rstrip()
            sigs.append((i, text[:-1].rstrip() if text.endswith("{") else text))
    return sigs

def sh_skeleton(lines):
    return [(i, l.rstrip()) for i, l in enumerate(lines, 1) if SH_RE.match(l)]

def sql_skeleton(lines):
    sigs = []
    for i, line in enumerate(lines, 1):
        m = SQL_RE.match(line)
        if m:
            text = m.group(1).rstrip()
            sigs.append((i, text[:-1].rstrip() if text.endswith("(") else text))
    return sigs

def process_file(path, relpath, out, totals, explicit):
    """out is a list of (kind, text) tuples. kind is 'file' or 'sig'."""
    ext = os.path.splitext(path)[1]
    if ext not in SUPPORTED_EXTS:
        if path in explicit:
            out.append(("file", "{}|UNSUPPORTED-EXT {}".format(relpath, ext)))
            totals["unsupported"] += 1
        return
    try:
        with open(path, "r", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return
    total_lines = src.count("\n") + (1 if src and not src.endswith("\n") else 0)
    src_bytes = len(src.encode("utf-8"))
    totals["src_bytes"] += src_bytes
    totals["files"] += 1

    if ext == ".py":
        try:
            sigs = py_skeleton(src)
        except (SyntaxError, ValueError):
            out.append(("file", "{}|PARSE-FAILED".format(relpath)))
            return
    elif ext == ".sh":
        sigs = sh_skeleton(src.splitlines())
    elif ext == ".sql":
        sigs = sql_skeleton(src.splitlines())
    else:
        sigs = ts_skeleton(src.splitlines())

    out.append(("file", "{}|{}".format(relpath, total_lines)))
    out += [("sig", "{}:{}".format(lineno, sig)) for lineno, sig in sigs]

def parse_max_bytes(argv):
    max_bytes = DEFAULT_MAX_BYTES
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--max-bytes":
            if i + 1 < len(argv):
                try:
                    max_bytes = int(argv[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
            i += 1
            continue
        if a.startswith("--max-bytes="):
            try:
                max_bytes = int(a.split("=", 1)[1])
            except ValueError:
                pass
            i += 1
            continue
        rest.append(a)
        i += 1
    return max_bytes, rest

def main():
    argv = sys.argv[1:]
    max_bytes, argv = parse_max_bytes(argv)
    recursive = "-r" in argv or "--recursive" in argv
    paths = [a for a in argv if a not in ("-r", "--recursive")]
    if not paths:
        print("skeleton.py: no path given. Usage: skeleton.py <path> [<path>...] [-r]", file=sys.stderr)
        sys.exit(1)

    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        for p in missing:
            print("skeleton.py: path does not exist (or is a dangling symlink): {}".format(p), file=sys.stderr)
        if len(missing) == len(paths):
            sys.exit(1)

    explicit = {os.path.abspath(p) for p in paths if os.path.isfile(p)}

    files = resolve_paths(paths, recursive)
    if not files:
        print("skeleton.py: no files found under given path(s) (empty dir, or all excluded)", file=sys.stderr)
        sys.exit(1)

    out, totals, cwd = [], {"files": 0, "src_bytes": 0, "unsupported": 0}, os.getcwd()
    for f in sorted(set(files)):
        try:
            relpath = os.path.relpath(f, cwd)
        except ValueError:
            relpath = f
        process_file(f, relpath, out, totals, explicit)

    total_files_out = sum(1 for kind, _ in out if kind == "file")
    total_sigs_out = sum(1 for kind, _ in out if kind == "sig")

    emitted, used, truncated = [], 0, False
    reserve = 80
    for kind, line in out:
        line_bytes = len(line.encode("utf-8")) + 1
        if used + line_bytes + reserve > max_bytes:
            truncated = True
            break
        emitted.append((kind, line))
        used += line_bytes

    for _, line in emitted:
        print(line)

    emitted_files = sum(1 for kind, _ in emitted if kind == "file")
    emitted_sigs = sum(1 for kind, _ in emitted if kind == "sig")

    out_bytes = sum(len(l.encode("utf-8")) + 1 for _, l in emitted)
    src_bytes = totals["src_bytes"]
    ratio = (src_bytes / out_bytes) if out_bytes else 0
    unsupported = totals["unsupported"]
    tail = "#SKELETON {} files, {} bytes, {:.1f}:1 vs {} source bytes".format(
        totals["files"], out_bytes, ratio, src_bytes)
    if unsupported:
        tail += " ({} unsupported)".format(unsupported)
    print(tail)
    if truncated:
        print("#TRUNCATED {} files, {} signatures (cap {} bytes, use --max-bytes to raise)".format(
            total_files_out - emitted_files, total_sigs_out - emitted_sigs, max_bytes))
    if totals["files"] == 0 and unsupported > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
