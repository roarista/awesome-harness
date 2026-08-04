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
    r"^\s*(export\s+.*|function\s+\w.*|class\s+\w.*|const\s+\w+\s*=\s*\(.*|"
    r"const\s+\w+\s*=\s*async\s*\(.*|interface\s+\w.*|type\s+\w+\s*=.*)$"
)
SH_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")

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
        m = TS_RE.match(line)
        if m:
            text = m.group(1).rstrip()
            sigs.append((i, text[:-1].rstrip() if text.endswith("{") else text))
    return sigs

def sh_skeleton(lines):
    return [(i, l.rstrip()) for i, l in enumerate(lines, 1) if SH_RE.match(l)]

def process_file(path, relpath, out, totals):
    ext = os.path.splitext(path)[1]
    if ext not in (".py", ".ts", ".tsx", ".js", ".jsx", ".sh"):
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
        except SyntaxError:
            out.append("{}|PARSE-FAILED".format(relpath))
            return
    elif ext == ".sh":
        sigs = sh_skeleton(src.splitlines())
    else:
        sigs = ts_skeleton(src.splitlines())

    out.append("{}|{}".format(relpath, total_lines))
    out += ["{}:{}".format(lineno, sig) for lineno, sig in sigs]

def main():
    recursive = "-r" in sys.argv[1:] or "--recursive" in sys.argv[1:]
    paths = [a for a in sys.argv[1:] if a not in ("-r", "--recursive")]
    if not paths:
        sys.exit(1)

    files = resolve_paths(paths, recursive)
    if not files:
        sys.exit(1)

    out, totals, cwd = [], {"files": 0, "src_bytes": 0}, os.getcwd()
    for f in sorted(set(files)):
        try:
            relpath = os.path.relpath(f, cwd)
        except ValueError:
            relpath = f
        process_file(f, relpath, out, totals)

    for line in out:
        print(line)

    out_bytes = sum(len(l.encode("utf-8")) + 1 for l in out)
    src_bytes = totals["src_bytes"]
    ratio = (src_bytes / out_bytes) if out_bytes else 0
    print("#SKELETON {} files, {} bytes, {:.1f}:1 vs {} source bytes".format(
        totals["files"], out_bytes, ratio, src_bytes))
    sys.exit(0)

if __name__ == "__main__":
    main()
