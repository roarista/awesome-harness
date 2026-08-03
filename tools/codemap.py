#!/usr/bin/env python3
"""Generate a dense .codemap of the repo (single-file, stdlib only)."""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

EXCLUDE_DIRS = (".bak", "graphify-out/", "node_modules/", ".git/")
BUDGET_BYTES = 12000
BIN_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".woff", ".woff2", ".ttf")

SEMGREP_RULE = """rules:
  - id: pysym
    languages: [python]
    message: "$F"
    severity: INFO
    patterns:
      - pattern-either:
          - pattern: "def $F(...): ..."
          - pattern: "class $F(...): ..."
          - pattern: "class $F: ..."
"""

SH_FUNC_RE = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{", re.M
)


def repo_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return out.stdout.strip()


def short_sha(root):
    out = subprocess.run(
        ["git", "-C", root, "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() or "unknown"


def tracked_files(root):
    out = subprocess.run(
        ["git", "-C", root, "ls-files"], capture_output=True, text=True
    )
    files = out.stdout.splitlines()
    result = []
    for f in files:
        if any(f.startswith(d) or (d in f and d.endswith("/")) for d in EXCLUDE_DIRS):
            continue
        if ".bak" in f:
            continue
        result.append(f)
    return result


def loc(path):
    """Return line count, or None if the file could not be read."""
    try:
        with open(path, "r", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


def py_symbols_ast(path):
    """Fallback python symbol extraction via ast. Returns None (not []) if
    the file could not be read or parsed, so callers can distinguish that
    from a genuinely empty file."""
    syms = []
    try:
        with open(path, "r", errors="replace") as fh:
            src = fh.read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                syms.append(node.name)
    except (SyntaxError, ValueError, OSError):
        return None
    return syms


def sh_symbols(path):
    try:
        with open(path, "r", errors="replace") as fh:
            src = fh.read()
        return SH_FUNC_RE.findall(src)
    except OSError:
        return []


def run_semgrep(root, py_files):
    """Return dict path -> [symbol names in order], or None on failure."""
    if not py_files:
        return {}
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yml", delete=False
        ) as rf:
            rf.write(SEMGREP_RULE)
            rule_path = rf.name
        cmd = [
            "semgrep",
            "--config",
            rule_path,
            "--json",
            "--quiet",
        ] + [os.path.join(root, p) for p in py_files]
        out = subprocess.run(cmd, capture_output=True, text=True, cwd=root, timeout=180)
        os.unlink(rule_path)
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout)
        results = data.get("results", [])
        by_file = {}
        for r in results:
            path = r.get("path", "")
            rel = os.path.relpath(path, root) if os.path.isabs(path) else path
            name = r.get("extra", {}).get("message", "").strip()
            if not name:
                continue
            line = r.get("start", {}).get("line", 0)
            by_file.setdefault(rel, []).append((line, name))
        result = {}
        for rel, entries in by_file.items():
            entries.sort(key=lambda e: e[0])
            result[rel] = [n for _, n in entries]
        return result
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, ValueError):
        try:
            os.unlink(rule_path)
        except Exception:
            pass
        return None


HUB_EXTS = (".py", ".sh", ".json")


def build_hub_entries(files, root):
    """Rank files by how many OTHER tracked files literally contain their
    basename as a substring. Ground truth by grep, computed in-process
    (single read per candidate file, no per-file subprocess spawns).

    Returns a list of (path, count) sorted by count desc, count >= 3 only.
    """
    candidates = [f for f in files if f.endswith(HUB_EXTS)]
    texts = {}
    for f in candidates:
        try:
            with open(os.path.join(root, f), "r", errors="replace") as fh:
                texts[f] = fh.read()
        except OSError:
            texts[f] = ""

    counts = {}
    for target in candidates:
        base = os.path.basename(target)
        n = 0
        for other, text in texts.items():
            if other == target:
                continue
            if base in text:
                n += 1
        if n >= 3:
            counts[target] = n

    hub_entries = sorted(counts.items(), key=lambda kv: -kv[1])
    return hub_entries


def build_map(root, stdout_mode=False):
    warns = []
    files = tracked_files(root)
    bin_files = sorted(f for f in files if f.lower().endswith(BIN_EXTS))
    bin_set = set(bin_files)
    files = [f for f in files if f not in bin_set]
    py_files = [f for f in files if f.endswith(".py")]
    sh_files = [f for f in files if f.endswith(".sh")]
    md_files = [f for f in files if f.endswith(".md")]
    other_files = [f for f in files if f not in py_files and f not in sh_files and f not in md_files]

    semgrep_data = run_semgrep(root, py_files)
    if semgrep_data is None:
        warns.append("#WARN semgrep unavailable: missing or non-zero exit")
        semgrep_data = {}

    hub_entries = build_hub_entries(files, root)

    file_syms = {}
    unparseable = set()
    for f in files:
        if f.endswith(".md"):
            continue
        full = os.path.join(root, f)
        if f.endswith(".py"):
            syms = semgrep_data.get(f)
            if not syms:
                syms = py_symbols_ast(full)
                if syms is None:
                    unparseable.add(f)
                    syms = []
            file_syms[f] = syms
        elif f.endswith(".sh"):
            file_syms[f] = sh_symbols(full)
        else:
            file_syms[f] = []

    total_loc = 0
    file_lines = {}
    unreadable = set()
    for f in files:
        if f.endswith(".md"):
            continue
        n = loc(os.path.join(root, f))
        if n is None:
            unreadable.add(f)
            n = 0
        total_loc += n
        syms = file_syms.get(f, [])
        file_lines[f] = (n, syms)

    failed_files = sorted(unparseable | unreadable)
    if failed_files:
        warns.append(
            "#WARN {} file(s) unreadable/unparseable: {}".format(
                len(failed_files), ",".join(failed_files)
            )
        )

    non_md = [f for f in files if not f.endswith(".md")]
    dirs = {}
    for f in non_md:
        d = os.path.dirname(f)
        dirs.setdefault(d, []).append(f)

    def render(truncate_syms):
        lines = []
        sha = short_sha(root)
        reponame = os.path.basename(root)
        nf = len(non_md)
        header = "#CODEMAP {} @{} {}f/{}L py{} sh{} md{}".format(
            reponame, sha, nf, total_loc, len(py_files), len(sh_files), len(md_files)
        )
        lines.append(header)
        for w in warns:
            lines.append(w)
        for d in sorted(dirs.keys()):
            lines.append("[{}]".format(d if d else "."))
            for f in sorted(dirs[d]):
                base = os.path.basename(f)
                n, syms = file_lines[f]
                if f in unparseable or f in unreadable:
                    lines.append("{}|?|?PARSE-FAIL".format(base))
                    continue
                if truncate_syms and len(syms) > 8:
                    shown = syms[:8]
                    rest = len(syms) - 8
                    symstr = ",".join(shown) + ",...+{}".format(rest)
                else:
                    symstr = ",".join(syms)
                lines.append("{}|{}|{}".format(base, n, symstr))
        if hub_entries:
            top = hub_entries[:8]
            hub_str = " ".join(
                "{}<-{}".format(path, cnt) for path, cnt in top
            )
            lines.append("#HUB " + hub_str)
        else:
            lines.append("#HUB none")
        if bin_files:
            lines.append("#BIN {} files: {}".format(len(bin_files), ",".join(bin_files)))
        if md_files:
            lines.append("#DOC " + ",".join(sorted(md_files)))
        return "\n".join(lines) + "\n"

    text = render(False)
    if len(text.encode("utf-8")) > BUDGET_BYTES:
        text = render(True)
    return text


def main():
    stdout_mode = "--stdout" in sys.argv
    root = repo_root()
    if not root:
        root = os.getcwd()
    text = build_map(root, stdout_mode)
    if stdout_mode:
        sys.stdout.write(text)
        return
    out_path = os.path.join(root, ".codemap")
    with open(out_path, "w") as fh:
        fh.write(text)
    nbytes = len(text.encode("utf-8"))
    print("{} bytes ~{} tokens".format(nbytes, nbytes // 4))


if __name__ == "__main__":
    main()
