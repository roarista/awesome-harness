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
    r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+([^\n#]+)|import\s+([\w.]+))", re.M
)
# Static (`from '...'`) and dynamic (`import('...')` / `await import('...')`)
# specifiers both count -- dynamic-import-only hubs (e.g. lib/ai.ts) were
# invisible to the static-only regex.
JS_IMPORT_RE = re.compile(
    r"""from\s+['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)"""
)
JS_EXPLICIT_EXT_RE = re.compile(r"\.(js|jsx|ts|tsx|mjs|cjs)$")
PY_MAIN_RE = re.compile(r"""^\s*if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)


def fail(root_name, msg):
    print(HEADER, end="")
    print("Repo {}: DILUTED INDEX UNAVAILABLE: {}".format(root_name, msg))
    sys.exit(1)


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
    # Only the top-level path component is checked. Matching at any depth
    # silently drops live code that happens to sit under a subdirectory
    # named e.g. "research" (virality's src/originated/research/, 2058 LOC
    # of live code, is not a docs/legacy dump).
    parts = relpath.split("/")[:-1]
    return bool(parts) and parts[0] in EXCLUDE_COMPONENTS


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
    the whole block if even the header line does not fit.

    The "... and N more" disclosure line is reserved for and, when
    n_dropped > 0, appended into the returned kept_lines itself -- its
    bytes are counted BEFORE deciding how many items fit, so it can never
    be the thing that pushes the block (and therefore the whole index)
    over budget. Returns (kept_lines, bytes_used, n_dropped)."""
    if not block_lines:
        return [], 0, 0
    header, items = block_lines[0], block_lines[1:]
    header_bytes = len(header.encode("utf-8")) + 1
    if header_bytes > budget:
        return [], 0, len(block_lines)
    item_bytes = [len(item.encode("utf-8")) + 1 for item in items]
    n = len(items)
    # Search from "keep everything" down to "keep nothing" for the largest
    # k whose kept items plus header plus (if any dropped) the note line
    # all fit in budget. The note's byte length depends on n-k (digit
    # count), so it must be recomputed per candidate k, not assumed fixed.
    for k in range(n, -1, -1):
        used = header_bytes + sum(item_bytes[:k])
        dropped = n - k
        note_bytes = 0
        if dropped:
            note = "  ... and {} more".format(dropped)
            note_bytes = len(note.encode("utf-8")) + 1
        if used + note_bytes <= budget:
            kept = [header] + items[:k]
            if dropped:
                kept.append(note)
            return kept, used + note_bytes, dropped
    # Even the header alone plus a "... and N more" for everything doesn't
    # fit (header_bytes <= budget already checked above, so this is only
    # reachable if the note itself can't fit alongside the header).
    return [header], header_bytes, n


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

    dropped_blocks = []

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

    # Reserve worst-case bytes for the "#DROPPED (budget): ..." disclosure
    # line up front, before any block consumes budget, so the disclosure
    # itself can never be the thing that gets silently dropped. Unused
    # reservation (fewer blocks actually dropped, or none) is returned to
    # budget right before that line is emitted, below.
    ALL_BLOCK_NAMES = ["source_roots", "areas", "most_imported", "entrypoints"]
    dropped_reserve = len(
        ("#DROPPED (budget): " + ", ".join(ALL_BLOCK_NAMES)).encode("utf-8")
    ) + 1
    budget -= dropped_reserve

    # SOURCE ROOTS block: top-level dirs holding source, files/LOC.
    root_stats = defaultdict(lambda: [0, 0])  # [files, loc]
    for f in src_files:
        top = f.split("/", 1)[0] if "/" in f else "."
        root_stats[top][0] += 1
        root_stats[top][1] += per_file_loc[f]
    root_lines = ["SOURCE ROOTS (files/LOC):"]
    for top, (nf, nl) in sorted(root_stats.items(), key=lambda kv: -kv[1][0])[:8]:
        root_lines.append("  {}: {} files, {}k LOC".format(top, nf, round(nl / 1000.0, 1)))

    kept, used, dropped = fit_block(root_lines, budget)
    if kept:
        lines += kept
        budget -= used
    elif root_lines:
        fb_kept, fb_used, _ = fit_block(
            ["SOURCE ROOTS: dropped entirely (no byte budget remaining)"], budget)
        if fb_kept:
            lines += fb_kept
            budget -= fb_used
        else:
            dropped_blocks.append("source_roots")

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

    kept, used, dropped = fit_block(area_lines, budget)
    if kept:
        lines += kept
        budget -= used
    elif area_lines:
        fb_kept, fb_used, _ = fit_block(
            ["AREAS: dropped entirely (no byte budget remaining)"], budget)
        if fb_kept:
            lines += fb_kept
            budget -= fb_used
        else:
            dropped_blocks.append("areas")

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
                from_mod, import_list, plain_mod = m.group(1), m.group(2), m.group(3)
                mod = None
                names = []
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
                    if import_list:
                        # `from PKG import NAME` -- NAME may be a submodule
                        # (PKG/NAME.py), not just an attribute of PKG's
                        # __init__.py. Resolving only against PKG collapses
                        # every submodule import onto the package marker,
                        # which is then dropped as noise below -- undercounting
                        # real hub files (e.g. `from storage import db`).
                        cleaned = import_list.replace("(", " ").replace(")", " ").replace("\\", " ")
                        for part in cleaned.split(","):
                            part = part.strip()
                            if not part:
                                continue
                            first = part.split(" as ")[0].strip()
                            name = first.split()[0] if first else ""
                            if name and name != "*":
                                names.append(name)
                elif plain_mod is not None:
                    mod = plain_mod
                if not mod:
                    continue
                submodule_hit = False
                for name in names:
                    cand_full = mod + "." + name if mod else name
                    if cand_full in py_modmap and py_modmap[cand_full] != f:
                        seen_targets.add(py_modmap[cand_full])
                        submodule_hit = True
                if submodule_hit:
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
                spec = m.group(1) or m.group(2)
                if not spec:
                    continue
                if not (spec.startswith(".") or spec.startswith("@/")):
                    continue
                # explicit extensions (import "./foo.js") must be stripped
                # before matching against the extension-less lookup table.
                spec_noext = JS_EXPLICIT_EXT_RE.sub("", spec)
                if spec_noext.startswith("@/"):
                    rel = spec_noext[2:]
                    candidates = [rel, rel + "/index"]
                else:
                    joined = os.path.normpath(os.path.join(fdir, spec_noext))
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
    # (__init__.py) are still dropped here since they represent the
    # package-attribute-import case, not a real hub file; genuine submodule
    # imports (`from PKG import submodule`) are resolved directly onto the
    # submodule file above and are unaffected by this filter.
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
                   "longest-prefix + TS/JS relative/@ resolution, static regex, not AST-exact; "
                   "counted over {} non-test source files of {} tracked):".format(n_src, n_tracked))
        if dominant_lang:
            mi_lines = [header]
            for f, n in by_lang.get(dominant_lang, [])[:10]:
                mi_lines.append("  {} <- {}".format(f, n))
        else:
            # Rank globally across eligible languages instead of a flat
            # per-language top-5 -- a flat allocation drops a genuinely
            # bigger hub (e.g. intrn's #6 lib/cache.ts, 36 importers) in
            # favor of low-importer rows from a language with fewer hubs.
            eligible_exts = {ext for ext, pct in lang_pct.items() if pct >= 15.0}
            global_items = [
                (f, n, os.path.splitext(f)[1].lstrip("."))
                for f, n in import_counts.items()
                if os.path.splitext(f)[1].lstrip(".") in eligible_exts
            ]
            global_items.sort(key=lambda t: -t[1])
            mi_lines = [header]
            for f, n, ext in global_items[:10]:
                mi_lines.append("  [{}] {} <- {}".format(ext, f, n))
        kept, used, dropped = fit_block(mi_lines, budget)
        named_via_imports = sum(1 for l in kept if " <- " in l)
        if kept:
            lines += kept
            budget -= used
        else:
            dropped_blocks.append("most_imported")
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

    # In a repo that is mostly not python (e.g. Next.js with two throwaway
    # __main__-guarded scripts), the package.json scripts are the real
    # entry points -- lead with those instead of burying them after a
    # near-meaningless guard count.
    if py_pct < 15.0 and pkg_scripts:
        ep_lines = ["ENTRY POINTS: package.json scripts: " + ", ".join(sorted(pkg_scripts))]
        if main_guard_count:
            ep_lines.append("  ({} `__main__` guard(s) also present)".format(main_guard_count))
    else:
        ep_lines = ["ENTRY POINTS: {} `__main__` guard(s)".format(main_guard_count)]
        if pkg_scripts:
            ep_lines.append("  package.json scripts: " + ", ".join(sorted(pkg_scripts)))
    kept, used, dropped = fit_block(ep_lines, budget)
    if kept:
        lines += kept
        budget -= used
    elif ep_lines:
        fb_kept, fb_used, _ = fit_block(
            ["ENTRY POINTS: dropped entirely (no byte budget remaining)"], budget)
        if fb_kept:
            lines += fb_kept
            budget -= fb_used
        else:
            dropped_blocks.append("entrypoints")

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
            kept, used, _dropped = fit_block([warn], budget)
            if kept:
                lines += kept
                budget -= used

    budget += dropped_reserve  # return the reservation; actual line is <= it
    if dropped_blocks:
        drop_line = "#DROPPED (budget): " + ", ".join(dropped_blocks)
        kept, used, _ = fit_block([drop_line], budget)
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
        sys.exit(1)

    print(out, end="")
    sys.exit(0)


if __name__ == "__main__":
    main()
