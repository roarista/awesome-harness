#!/usr/bin/env python3
"""
claudemd_drift.py — fast, deterministic harness-doc drift validator.

Usage: python3 claudemd_drift.py [REPO_DIR] [--json]
Exit:  0 = no drift, 1 = drift found.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Structural docs — always checked when present
STRUCTURAL_DOCS = [
    "CLAUDE.md",
    "AGENTS.md",
    "START_HERE.md",
    "STATE_CURRENT.md",
]

# Sprint/work-log docs — noisy by default; opt-in via --include-state
STATE_LOG_DOCS = [
    ".planning/STATE.md",
]

# File extensions that clearly indicate a filesystem path (leaf must end in one of these
# for a bare token to be considered a path candidate)
CODE_EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".md", ".sh", ".sql",
             ".yml", ".yaml", ".toml", ".txt", ".env", ".lock", ".html", ".css"}

# Skip tokens that start with these (URLs, env-vars, etc.)
URL_PREFIXES = ("http://", "https://", "//")

# Slash-command shape: /word or /word:subword — single segment, no further slash,
# optional colon-subcommand, no dot-extension.
_SLASH_CMD_RE = re.compile(r'^/[A-Za-z][\w-]*(:[\w-]+)?$')


def is_slash_command(token: str) -> bool:
    """Return True if token is a slash command like /goal or /gsd:quick."""
    return bool(_SLASH_CMD_RE.match(token))


# Extensions that are meaningful at repo root without a directory path
_ROOT_ONLY_EXTS = {".md", ".json", ".sh", ".yml", ".yaml", ".toml", ".txt",
                   ".env", ".lock", ".html", ".css"}
# Source code extensions — only checked when accompanied by a directory (slash present)
_CODE_ONLY_EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".sql"}


def looks_like_path(token: str) -> bool:
    """Return True if token should be treated as a path candidate to check."""
    if not token:
        return False
    if token.startswith("$"):
        return False
    for p in URL_PREFIXES:
        if token.startswith(p):
            return False
    if " " in token:
        return False
    if "*" in token:
        return False
    if "(" in token or ")" in token:
        return False
    if is_slash_command(token):
        return False
    # Skip brace-expanded shell globs ({a,b,c} patterns)
    if "{" in token or "}" in token:
        return False
    # Skip template placeholders (<placeholder> or NNN-style)
    if "<" in token or ">" in token:
        return False
    # Skip ellipsis-prefixed truncated paths
    if token.startswith("…") or token.startswith("..."):
        return False
    # Skip tokens containing /... (literal ellipsis mid-path, e.g. openai-codex/.../file)
    if "/..." in token:
        return False
    # Skip numeric-only placeholders like out-NNN.json, result-NNNN.jsonl
    # (capital N sequences used as placeholders in sprint logs)
    if re.search(r'-N{2,}\.', token):
        return False
    # Skip .git/ internal paths — not doc-level drift
    if token.startswith(".git/"):
        return False
    # Skip multi-line-number refs like file.ts:58/64 or file.ts:445/910/506
    # (these have a colon before the slash, indicating line numbers not path segments)
    if re.search(r'\.\w+:\d+/', token):
        return False

    has_slash = "/" in token
    # Strip :linenumber suffix before checking extension
    leaf = Path(token.split(":")[0]).name
    suffix = Path(leaf).suffix
    is_dotpath = re.match(r'^\.[A-Za-z]', token) is not None

    # Bare source-code filename (no slash, not a dotpath) = shorthand agent/module name,
    # not a file path we can check — skip to avoid false positives.
    if suffix in _CODE_ONLY_EXTS and not has_slash and not is_dotpath:
        return False

    # Must have a code/doc extension or be a dotpath
    all_exts = _ROOT_ONLY_EXTS | _CODE_ONLY_EXTS
    has_known_ext = suffix in all_exts
    if not (has_known_ext or is_dotpath):
        return False

    # Bare root-level filename without slash: only allow root-level extensions
    if not has_slash and not is_dotpath:
        return suffix in _ROOT_ONLY_EXTS

    # Dotpath without a slash (e.g. .contains, .filter, .node, .universalName) —
    # these are method/property names, not filesystem paths. Require either a slash
    # or a known extension.
    if is_dotpath and not has_slash and suffix not in all_exts:
        return False

    return True


def extract_path_candidates(text: str) -> list:
    """Extract candidate path tokens from doc text.

    Primary source: backtick-wrapped tokens (highest fidelity, exact as written).
    Secondary source: bare tokens outside backticks that end with a code extension
    (very conservative — avoids prose false positives).
    """
    candidates = []

    # --- A: backtick-wrapped tokens ---
    backtick_re = re.compile(r'`([^`\n]+?)`')
    backtick_spans = []
    for m in backtick_re.finditer(text):
        backtick_spans.append((m.start(), m.end()))
        tok = m.group(1).strip().rstrip("/:,;.")
        if tok:
            candidates.append(tok)

    # --- B: bare tokens outside backtick spans that have a code extension ---
    # Mask backtick content so we don't double-extract
    masked = list(text)
    for start, end in backtick_spans:
        for i in range(start, end):
            masked[i] = ' '
    masked_text = ''.join(masked)

    # Only match tokens that end with a recognised extension — avoids prose noise
    ext_pat = '|'.join(re.escape(e) for e in CODE_EXTS)
    bare_re = re.compile(
        r'(?<![.\w/~])'              # not preceded by path chars
        r'(\.?[A-Za-z0-9][\w.\-/]*' # token body (may start with dot)
        r'(?:' + ext_pat + r'))'     # must end with a code extension
    )
    for m in bare_re.finditer(masked_text):
        tok = m.group(1).rstrip("/:,;.")
        if tok and '/' in tok:       # only include if it looks like a path
            candidates.append(tok)

    # Deduplicate while preserving order
    seen = set()
    result = []
    for tok in candidates:
        if tok not in seen:
            seen.add(tok)
            result.append(tok)
    return result


def extract_npm_scripts(text: str) -> list:
    """Extract npm/pnpm/yarn script names referenced in doc text."""
    patterns = [
        re.compile(r'(?:npm|pnpm)\s+run\s+([\w:\-]+)'),
        re.compile(r'yarn\s+([\w:\-]+)'),
    ]
    scripts = []
    for pat in patterns:
        for m in pat.finditer(text):
            scripts.append(m.group(1))
    seen = set()
    result = []
    for s in scripts:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result


def path_exists_anywhere(tok: str, repo: Path) -> bool:
    """Return True if token resolves to an existing path, or should be excluded.

    1. ~/... — expand via os.path.expanduser; valid external refs.
    2. ../... — resolve relative to repo; if outside repo boundary, exclude (external).
    3. Absolute paths — check directly.
    4. Repo-relative — check repo / tok (handles dotfiles like .claude/settings.json).
    """
    # Strip :linenumber suffix (e.g. file.ts:128)
    tok_path = tok.split(":")[0]

    if tok_path.startswith("~/"):
        expanded = Path(os.path.expanduser(tok_path))
        return expanded.exists()

    if tok_path.startswith("../"):
        resolved = (repo / tok_path).resolve()
        try:
            resolved.relative_to(repo.resolve())
            return resolved.exists()
        except ValueError:
            return True  # outside repo — treat as external, don't flag

    if tok_path.startswith("/"):
        return Path(tok_path).exists()

    return (repo / tok_path).exists()


def main():
    parser = argparse.ArgumentParser(description="CLAUDE.md/AGENTS.md drift validator")
    parser.add_argument("repo_dir", nargs="?", default=".", help="Repo root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--include-state", "--all-docs",
        dest="include_state", action="store_true",
        help="Also scan .planning/STATE.md (noisy sprint log; excluded by default)",
    )
    args = parser.parse_args()

    repo = Path(args.repo_dir).resolve()

    # Build the list of docs to scan
    doc_names_to_check = list(STRUCTURAL_DOCS)
    if args.include_state:
        doc_names_to_check.extend(STATE_LOG_DOCS)

    # --- 1. Read docs ---
    docs_checked = []
    doc_contents = {}

    for name in doc_names_to_check:
        p = repo / name
        if p.exists():
            doc_contents[name] = p.read_text(encoding="utf-8", errors="replace")
            docs_checked.append(name)

    # Note when .planning/STATE.md was skipped
    _state_log_skipped = (
        not args.include_state
        and any((repo / n).exists() for n in STATE_LOG_DOCS)
    )

    if not doc_contents:
        if args.json:
            print(json.dumps({
                "missing_paths": [],
                "missing_commands": [],
                "docs_checked": [],
                "counts": {"paths": 0, "commands": 0},
            }))
        else:
            print("No harness docs found.")
            print("drift: 0 paths, 0 commands")
        sys.exit(0)

    # --- 2. Path-reference check ---
    missing_paths = []

    for doc_name, text in doc_contents.items():
        candidates = extract_path_candidates(text)
        for tok in candidates:
            if not looks_like_path(tok):
                continue
            if not path_exists_anywhere(tok, repo):
                missing_paths.append({"doc": doc_name, "path": tok})

    # --- 3. Command check ---
    missing_commands = []

    pkg_json = repo / "package.json"
    defined_scripts = set()
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
            defined_scripts = set(pkg.get("scripts", {}).keys())
        except (json.JSONDecodeError, OSError):
            pass

        for doc_name, text in doc_contents.items():
            for script in extract_npm_scripts(text):
                if script not in defined_scripts:
                    missing_commands.append({"doc": doc_name, "script": script})

    # --- 4. Output ---
    n_paths = len(missing_paths)
    n_cmds = len(missing_commands)

    if args.json:
        print(json.dumps({
            "missing_paths": missing_paths,
            "missing_commands": missing_commands,
            "docs_checked": docs_checked,
            "counts": {"paths": n_paths, "commands": n_cmds},
        }, indent=2))
    else:
        if docs_checked:
            print(f"Docs checked: {', '.join(docs_checked)}")
        if _state_log_skipped:
            print("(.planning/STATE.md excluded by default; use --include-state to scan it)")
        if missing_paths:
            print("\nMISSING PATHS (referenced in docs but not found on disk):")
            for item in missing_paths:
                print(f"  [{item['doc']}] {item['path']}")
        else:
            print("\nMISSING PATHS: none")
        if missing_commands:
            print("\nMISSING COMMANDS (npm scripts referenced but not defined):")
            for item in missing_commands:
                print(f"  [{item['doc']}] npm run {item['script']}")
        else:
            print("\nMISSING COMMANDS: none")
        print(f"\ndrift: {n_paths} paths, {n_cmds} commands")

    sys.exit(1 if (n_paths > 0 or n_cmds > 0) else 0)


if __name__ == "__main__":
    main()
