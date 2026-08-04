"""Shared source-file exclusion predicate for l0.py and l1.py.

Two classes, so they can never silently diverge again:
- ALWAYS_EXCLUDE: never source, no matter how deep -- test/build/dep dirs.
- TOP_LEVEL_EXCLUDE: ambiguous names (real code when nested, e.g.
  virality's src/originated/research/ is 2058 LOC of live pipeline) --
  only excluded when they are the top-level path component.
"""

ALWAYS_EXCLUDE = {
    "__tests__", "tests", "test", "node_modules", ".venv", "dist", "build",
    ".next", "coverage",
}

TOP_LEVEL_EXCLUDE = {
    "research", "knowledge", "docs", "legacy", "assets", "public", "scratch",
    "prototypes",
    # additional top-level-only noise dirs carried over from the prior
    # single-class list, kept as top-level-only (not always-exclude, since
    # none of these are test/build/dependency dirs).
    "_legacy", ".artifacts", ".scratch", ".planning", ".claude", ".mulch",
    ".github", ".agents", "evals",
}


def is_excluded(relpath):
    """relpath is a file path relative to repo root, e.g. 'src/foo/bar.py'."""
    parts = relpath.split("/")[:-1]
    if not parts:
        return False
    if any(p in ALWAYS_EXCLUDE for p in parts):
        return True
    return parts[0] in TOP_LEVEL_EXCLUDE
