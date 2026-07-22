#!/usr/bin/env python3
"""HARD routing gate — in a "route-only" repo, the orchestrator may NOT write
code directly; it must delegate the build to a coding sub-agent (codex 5.5
builder / Opus 4.8 (low effort) auditor).

Ro's intent (2026-07-09): the main session should ORCHESTRATE, not code. It's
fine (good, even) for it to READ/understand the codebase — graphify gives that
without eating the context window — but the actual writing of source belongs to
the coding agents, prompted well (see docs/CODING_AGENT_PROMPTING.md). This gate
forces that: PreToolUse on Write|Edit|MultiEdit DENIES a direct edit of a source
file in an armed repo.

OPT-IN per repo (safe rollout — never wedges a repo that didn't ask for it):
  a repo is "armed" only if a `.route-only` marker file exists at/above the
  target. Arm a pipeline with `touch <repo>/.route-only` (do it when the repo's
  autonomous session is idle, per the live-session safety rule). Nothing is
  armed by default.

Deliberately narrow so it enforces without collateral:
  * non-code target (.md/.json/.txt/.yaml/.toml/config, orientation files,
    memory, docs, tests) → ALWAYS allowed (orchestrator must still edit
    .now.md / .northstar.md / STATE / notes / docs directly).
  * repo not armed (no .route-only up-tree) → no-op.
  * codex/glm build via their OWN CLI (Bash), not Write/Edit — so the builders
    are unaffected; only DIRECT orchestrator edits are blocked.
  * kill-switch env ROUTING_GATE=0 → no-op.  Any error → fail-open (exit 0).
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

CODE_EXT = {"py", "js", "ts", "tsx", "jsx", "go", "rs", "rb", "java", "swift",
            "c", "cc", "cpp", "h", "hpp", "sh", "vue", "svelte", "php", "scala",
            "kt", "m", "mm", "sql", "css", "scss"}
# path fragments that are always allowed even if code-ish (orientation/infra)
ALLOW_FRAG = ("/.claude/", "/.planning/", "/node_modules/", "/.git/",
              "/memory/", "/docs/", "/.mulch/")


def _armed(start: Path) -> bool:
    for d in [start, *start.parents]:
        if (d / ".route-only").exists():
            return True
    return False


def _is_code(fp: str) -> bool:
    base = os.path.basename(fp)
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if ext not in CODE_EXT:
        return False
    low = fp.replace("\\", "/").lower()
    if any(f in low for f in ALLOW_FRAG):
        return False
    if "/test" in low or low.endswith((".test.ts", ".test.js", ".spec.ts",
                                       ".spec.js", "_test.py", "_test.go")):
        return False
    return True


def main() -> None:
    if os.environ.get("ROUTING_GATE") == "0":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") not in ("Write", "Edit", "MultiEdit"):
        return
    fp = str((data.get("tool_input", {}) or {}).get("file_path", "") or "")
    if not fp:
        return
    abspath = fp if os.path.isabs(fp) else os.path.join(os.getcwd(), fp)
    if not _is_code(abspath):
        return
    if not _armed(Path(abspath).parent):
        return
    sys.stderr.write(
        "ROUTE-ONLY GATE: this repo is orchestrate-only (.route-only marker) — "
        f"delegate the build of {os.path.basename(abspath)} to a coding sub-agent "
        "(codex builder / Opus-4.8-low auditor); do not write source directly. "
        "(kill-switch: ROUTING_GATE=0)\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over the gate
