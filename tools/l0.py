#!/usr/bin/env python3
"""Diluted index -- names only, no signatures, no bodies. HARD CAP 1,500 bytes.
Usage: python3 tools/l0.py
Computed live, every call, from `git rev-parse --show-toplevel`. No cache.
"""
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

CAP = 1500


def _sibling_ref(name, root):
    """Resolve l0.py's sibling tool (l1.py / skeleton.py) relative to l0.py's
    own location, not a hardcoded guess. Returns a string to print in a
    header line, or None if the sibling doesn't exist anywhere."""
    here = Path(__file__).resolve().parent
    sib = here / name
    if not sib.is_file():
        return None
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


def build_header(root=None):
    l1_ref = _sibling_ref("l1.py", root)
    sk_ref = _sibling_ref("skeleton.py", root)
    zoom_line = (
        "Zoom in:   {} <area>       (files+LOC+entrypoints for one area)".format(l1_ref)
        if l1_ref else "Zoom in:   (l1.py not installed)"
    )
    api_line = (
        "Exact API: {} <file> (verbatim signatures)".format(sk_ref)
        if sk_ref else "Exact API: (skeleton.py not installed)"
    )
    return (
        "DILUTED INDEX -- not the code. Names only, no signatures, no bodies.\n"
        "{}\n"
        "{}\n"
    ).format(zoom_line, api_line)


HEADER = build_header()

EXCLUDE_COMPONENTS = {
    "docs", "tests", "test", "__tests__", "_legacy", ".artifacts", ".scratch",
    ".planning", ".claude", ".mulch", "node_modules", ".github", ".agents",
    "assets", "public", "research", "knowledge", "evals", "legacy",
}
SRC_EXTS = (".py", ".ts", ".tsx", ".js", ".jsx", ".sh", ".sql")

PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(\.*[\w.]*)\s+import\b|import\s+([\w.]+))", re.M
)
JS_IMPORT_RE = re.compile(r"""from\s+['"]([^'"]+)['"]""")
PY_MAIN_RE = re.compile(r"""^\s*if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)


def fail(root_name, msg):
    print(HEADER, end="")
    print("Repo {}: DILUTED INDEX UNAVAILABLE: {}".format(root_name, msg))
    sys.exit(0)


def get_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        print("Not inside a git repo: DILUTED INDEX UNAVAILABLE: "
              "`git rev-parse --show-toplevel` failed.")
        sys.exit(1)
    return out.stdout.strip()


def is_excluded(relpath):
    parts = relpath.split("/")[:-1]
    return any(p in EXCLUDE_COMPONENTS for p in parts)


def is_source(relpath):
    return os.path.splitext(relpath)[1] in SRC_EXTS


def module_key(relpath):
    """Build a dotted-module-style key for python longest-prefix resolution,
    and a plain path-based key set for JS/TS resolution."""
    noext, ext = os.path.splitext(relpath)
    if ext == ".py":
        dotted = noext.replace("/", ".")
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        return dotted
    return noext


def count_lines(path):
    try:
        with open(path, "r", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def has_entrypoint(path, ext):
    if ext == ".py":
        try:
            with open(path, "r", errors="replace") as fh:
                return bool(PY_MAIN_RE.search(fh.read()))
        except OSError:
            return False
    return False


def fit_block(block_lines, budget):
    """Fit a block (header + item lines) into budget bytes without ever
    cutting a line in half. Drops whole items from the bottom (lowest
    priority, since callers pre-sort descending) until it fits, or drops
    the whole block if even the header line does not fit. Returns
    (kept_lines, bytes_used)."""
    if not block_lines:
        return [], 0
    header, items = block_lines[0], block_lines[1:]
    header_bytes = len(header.encode("utf-8")) + 1
    if header_bytes > budget:
        return [], 0
    kept, used = [header], header_bytes
    for item in items:
        item_bytes = len(item.encode("utf-8")) + 1
        if used + item_bytes > budget:
            break
        kept.append(item)
        used += item_bytes
    return kept, used


def main():
    global HEADER
    root = get_root()
    HEADER = build_header(root)
    root_name = os.path.basename(root.rstrip("/"))

    sha_out = subprocess.run(
        ["git", "-C", root, "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    short_sha = sha_out.stdout.strip() or "unknown"
    date_out = subprocess.run(
        ["git", "-C", root, "log", "-1", "--format=%ad", "--date=short"],
        capture_output=True, text=True,
    )
    date = date_out.stdout.strip() or "unknown"

    ls = subprocess.run(
        ["git", "-C", root, "ls-files"], capture_output=True, text=True,
    )
    tracked = [l for l in ls.stdout.splitlines() if l]
    n_tracked = len(tracked)

    src_files = [f for f in tracked if is_source(f) and not is_excluded(f)]
    excluded_files = [f for f in tracked if is_source(f) and is_excluded(f)]
    n_src = len(src_files)

    total_loc = 0
    per_file_loc = {}
    for f in src_files:
        full = os.path.join(root, f)
        loc = count_lines(full)
        per_file_loc[f] = loc
        total_loc += loc
    loc_k = total_loc / 1000.0

    lang_counts = defaultdict(int)
    for f in src_files:
        lang_counts[os.path.splitext(f)[1].lstrip(".")] += 1
    lang_pct = {
        ext: (n / n_src * 100.0) if n_src else 0.0
        for ext, n in lang_counts.items()
    }
    top_langs = sorted(lang_counts.items(), key=lambda kv: -kv[1])[:3]
    langs_line = "LANGS: " + ", ".join(
        "{} {:.0f}% ({}f)".format(ext, lang_pct[ext], n) for ext, n in top_langs
    )

    lines = []
    lines.append(HEADER.rstrip("\n"))
    lines.append(
        "Repo {} @{} {}: {} tracked, {} source files, {:.0f}k LOC.".format(
            root_name, short_sha, date, n_tracked, n_src, loc_k
        )
    )
    lines.append(langs_line)

    # G1 minimum-signal check pieces computed up front.
    if n_src < 10:
        fail(root_name, "only {} source files found (< 10 minimum) -- "
             "check exclude filters or repo is genuinely tiny.".format(n_src))

    budget = CAP - sum(len(l.encode("utf-8")) + 1 for l in lines)

    # SOURCE ROOTS block: top-level dirs holding source, files/LOC.
    root_stats = defaultdict(lambda: [0, 0])  # [files, loc]
    for f in src_files:
        top = f.split("/", 1)[0] if "/" in f else "."
        root_stats[top][0] += 1
        root_stats[top][1] += per_file_loc[f]
    root_lines = ["SOURCE ROOTS (files/LOC):"]
    for top, (nf, nl) in sorted(root_stats.items(), key=lambda kv: -kv[1][0])[:8]:
        root_lines.append("  {}: {} files, {}k LOC".format(top, nf, round(nl / 1000.0, 1)))

    kept, used = fit_block(root_lines, budget)
    if kept:
        lines += kept
        budget -= used

    # AREAS block: 2nd-level dirs, descending by file count.
    area_stats = defaultdict(int)
    for f in src_files:
        parts = f.split("/")
        if len(parts) >= 3:
            area = parts[0] + "/" + parts[1]
        elif len(parts) == 2:
            area = parts[0]
        else:
            area = "."
        area_stats[area] += 1
    area_items = sorted(area_stats.items(), key=lambda kv: -kv[1])[:12]
    area_lines = ["AREAS (source files):"]
    for area, n in area_items:
        area_lines.append("  {}: {}".format(area, n))

    kept, used = fit_block(area_lines, budget)
    if kept:
        lines += kept
        budget -= used

    # MOST-IMPORTED block.
    py_files = {f for f in src_files if f.endswith(".py")}
    py_modmap = {module_key(f): f for f in py_files}
    py_mod_by_prefix_len = sorted(py_modmap.keys(), key=len, reverse=True)

    jsts_files = {f for f in src_files if os.path.splitext(f)[1] in (".ts", ".tsx", ".js", ".jsx")}
    jsts_noext = {os.path.splitext(f)[0]: f for f in jsts_files}

    import_counts = defaultdict(int)
    real_named = set()

    for f in src_files:
        full = os.path.join(root, f)
        ext = os.path.splitext(f)[1]
        try:
            with open(full, "r", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue

        if ext == ".py":
            seen_targets = set()
            fdir_parts = f.split("/")[:-1]
            for m in PY_IMPORT_RE.finditer(text):
                from_mod, plain_mod = m.group(1), m.group(2)
                mod = None
                if from_mod is not None:
                    ndots = len(from_mod) - len(from_mod.lstrip("."))
                    remainder = from_mod[ndots:]
                    if ndots > 0:
                        # relative import: resolve against the importing
                        # file's own package directory.
                        base = fdir_parts[: max(len(fdir_parts) - (ndots - 1), 0)]
                        remainder_parts = remainder.split(".") if remainder else []
                        mod = ".".join(base + remainder_parts)
                    else:
                        mod = from_mod
                elif plain_mod is not None:
                    mod = plain_mod
                if not mod:
                    continue
                match = None
                for cand in py_mod_by_prefix_len:
                    if mod == cand or mod.startswith(cand + "."):
                        match = cand
                        break
                if match and py_modmap[match] != f:
                    seen_targets.add(py_modmap[match])
            for t in seen_targets:
                import_counts[t] += 1
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            seen_targets = set()
            fdir = os.path.dirname(f)
            for m in JS_IMPORT_RE.finditer(text):
                spec = m.group(1)
                if not (spec.startswith(".") or spec.startswith("@/")):
                    continue
                if spec.startswith("@/"):
                    rel = spec[2:]
                    candidates = [rel, rel + "/index"]
                else:
                    joined = os.path.normpath(os.path.join(fdir, spec))
                    candidates = [joined, joined + "/index"]
                resolved = None
                for c in candidates:
                    c = c.replace(os.sep, "/")
                    if c in jsts_noext:
                        resolved = jsts_noext[c]
                        break
                if resolved and resolved != f:
                    seen_targets.add(resolved)
            for t in seen_targets:
                import_counts[t] += 1

    # A count of 1 is noise, not a hub -- never list it. Package markers
    # (__init__.py) are not real hubs either; imports routed through them
    # already accrued to the resolved target module above, so dropping the
    # marker here does not lose signal, only the noisy dupe entry.
    import_counts = {
        f: n for f, n in import_counts.items()
        if n >= 2 and os.path.basename(f) != "__init__.py"
    }

    # Resolver-dead check: if a language has enough source files to expect
    # signal but produced none, do not silently fall back to whichever
    # other language's resolver happened to work -- that is exactly the
    # inverted/misleading result this guard exists to prevent.
    best_py = max((n for f, n in import_counts.items() if f.endswith(".py")), default=0)
    best_ts = max((n for f, n in import_counts.items()
                    if os.path.splitext(f)[1] in (".ts", ".tsx", ".js", ".jsx")), default=0)
    py_pct = (len(py_files) / n_src * 100.0) if n_src else 0.0
    ts_pct = (len(jsts_files) / n_src * 100.0) if n_src else 0.0
    py_dead = py_pct >= 15.0 and best_py < 5
    ts_dead = ts_pct >= 15.0 and best_ts < 5

    top_imports = sorted(import_counts.items(), key=lambda kv: -kv[1])[:10]
    real_named.update(f for f, _ in top_imports)
    named_via_imports = 0

    # 3(c): dominant-language repos spend the whole budget on that language;
    # mixed repos (no single language >= 80%) show labelled top hubs per
    # language that clears the 15% signal floor.
    dominant_lang = next((ext for ext, pct in lang_pct.items() if pct >= 80.0), None)
    by_lang = defaultdict(list)
    for f, n in import_counts.items():
        by_lang[os.path.splitext(f)[1].lstrip(".")].append((f, n))
    for ext in by_lang:
        by_lang[ext].sort(key=lambda kv: -kv[1])

    if py_dead or ts_dead:
        reasons = []
        if py_dead:
            reasons.append("python resolver matched nothing ({} .py source files, "
                            "top count {})".format(len(py_files), best_py))
        if ts_dead:
            reasons.append("TS/JS resolver matched nothing ({} source files, "
                            "top count {})".format(len(jsts_files), best_ts))
        lines.append("MOST-IMPORTED UNAVAILABLE: " + "; ".join(reasons))
    elif top_imports and top_imports[0][1] > 5:
        header = ("MOST-IMPORTED (distinct importing files; python `from|import` "
                   "longest-prefix + TS/JS relative/@ resolution, static regex, not AST-exact):")
        if dominant_lang:
            mi_lines = [header]
            for f, n in by_lang.get(dominant_lang, [])[:10]:
                mi_lines.append("  {} <- {}".format(f, n))
        else:
            mi_lines = [header]
            eligible = sorted(
                (ext for ext, pct in lang_pct.items() if pct >= 15.0),
                key=lambda e: -lang_pct[e],
            )
            for ext in eligible:
                items = by_lang.get(ext, [])[:5]
                if not items:
                    continue
                mi_lines.append("  [{}]".format(ext))
                for f, n in items:
                    mi_lines.append("    {} <- {}".format(f, n))
        kept, used = fit_block(mi_lines, budget)
        named_via_imports = sum(1 for l in kept if " <- " in l)
        if kept:
            lines += kept
            budget -= used
    else:
        top_n = top_imports[0][1] if top_imports else 0
        lines.append(
            "MOST-IMPORTED: suppressed -- top count is {} (<=5); import regex "
            "likely not matching this repo's style.".format(top_n)
        )

    # ENTRY POINTS block.
    main_guard_count = 0
    for f in py_files:
        if has_entrypoint(os.path.join(root, f), ".py"):
            main_guard_count += 1

    pkg_scripts = []
    pkg_json = os.path.join(root, "package.json")
    if os.path.isfile(pkg_json):
        try:
            import json
            with open(pkg_json, "r", errors="replace") as fh:
                data = json.load(fh)
            pkg_scripts = list((data.get("scripts") or {}).keys())
        except (OSError, ValueError):
            pkg_scripts = []

    ep_lines = ["ENTRY POINTS: {} `__main__` guard(s)".format(main_guard_count)]
    if pkg_scripts:
        ep_lines.append("  package.json scripts: " + ", ".join(sorted(pkg_scripts)))
    kept, used = fit_block(ep_lines, budget)
    if kept:
        lines += kept
        budget -= used

    # G4: excluded-vs-tracked ratio warning.
    total_source_like = len(src_files) + len(excluded_files)
    if total_source_like and (len(excluded_files) / max(n_tracked, 1)) > 0.92:
        exc_dirs = defaultdict(int)
        for f in excluded_files:
            top = f.split("/", 1)[0]
            exc_dirs[top] += 1
        if exc_dirs:
            biggest = max(exc_dirs.items(), key=lambda kv: kv[1])
            warn = "WARNING: excluded files are >92% of tracked; largest excluded dir: {} ({} files)".format(
                biggest[0], biggest[1])
            kept, used = fit_block([warn], budget)
            if kept:
                lines += kept
                budget -= used

    out = "\n".join(lines) + "\n"
    out_bytes = out.encode("utf-8")

    # G1: the index must actually NAME real files, not just count them.
    # The only block that prints individual filenames is MOST-IMPORTED
    # (SOURCE ROOTS/AREAS are directory rollups, ENTRY POINTS is a count).
    # Require it to have named >= 10 real files, and separately require
    # >= 3 entries survived the byte budget (both conditions must hold,
    # or the tool would silently degrade to a directory-only dump).
    if len(top_imports) < 10 or named_via_imports < 3:
        fail(root_name, "MOST-IMPORTED named only {} candidate file(s) "
             "({} survived the byte budget); need >=10 candidates and "
             ">=3 printed to avoid a directory-only dump.".format(
                 len(top_imports), named_via_imports))

    # G2: minimum output size.
    if len(out_bytes) < 300:
        print(out, end="")
        sys.exit(1)

    if len(out_bytes) > CAP:
        # Should not happen given block budgeting, but guard anyway.
        out = HEADER + "Repo {} @{} {}: DILUTED INDEX UNAVAILABLE: output exceeded {} byte cap.\n".format(
            root_name, short_sha, date, CAP)
        print(out, end="")
        sys.exit(0)

    print(out, end="")
    sys.exit(0)


if __name__ == "__main__":
    main()
