#!/usr/bin/env python3
"""harness-coach — weekly, propose-only harness self-improvement pass.

Reads the last 7 days of Claude Code session transcripts, mines them with
DETERMINISTIC metrics (no model — the logs are ~1GB/week, far too big to feed
raw), then hands a small DIGEST to GPT-5.5 (via `codex exec`) which returns a
ranked, propose-only report: where we waste tokens, where code came out weak,
and concrete suggested diffs to CLAUDE.md / hooks / skills.

It NEVER edits the harness. It writes one markdown report to
  ~/Downloads/harness-coach/YYYY-MM-DD.md
and posts a macOS notification. Ro reads it and decides what to apply.

Design: deterministic pre-filter (cheap, bounded CPU) → one model call over a
capped digest. Same trick as precompact-handoff. Fail-safe: any stage error
leaves no half-written report (temp + atomic rename).

Run: python3 harness-coach.py [--days 7] [--deep 30] [--no-model]
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
OUTDIR = Path.home() / "Downloads" / "harness-coach"
OVERSIZE = 2048          # a tool_result over this many chars is "bloat"
REREAD_N = 3             # same file Read >= this many times in a session = churn
DIGEST_CAP = 45000       # hard cap on chars handed to the model
MODEL_TIMEOUT = 900      # codex exec can be slow; weekly batch, generous


def token_proxy(nbytes: int) -> int:
    """Rough token estimate. ~4 chars/token; transcripts are ~1/4 real text."""
    return nbytes // 4


def mine_session(path: Path) -> dict:
    """Deep per-session metrics. Streams lines; tolerant of junk."""
    tools = Counter()
    reads = Counter()          # file_path -> times Read
    toolres_bytes = 0
    oversize_hits = 0
    errors = 0
    text_bytes = 0
    for ln in path.read_text(errors="replace").splitlines():
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        msg = obj.get("message") or obj
        content = msg.get("content")
        if isinstance(content, str):
            text_bytes += len(content)
            continue
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict):
                continue
            t = it.get("type")
            if t == "text":
                text_bytes += len(it.get("text", ""))
            elif t == "tool_use":
                name = it.get("name", "?")
                tools[name] += 1
                if name == "Read":
                    fp = (it.get("input") or {}).get("file_path", "")
                    if fp:
                        reads[fp] += 1
            elif t == "tool_result":
                c = it.get("content", "")
                if isinstance(c, list):
                    c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                c = str(c)
                toolres_bytes += len(c)
                if len(c) > OVERSIZE:
                    oversize_hits += 1
                if it.get("is_error") or re.search(
                    r"\b(error|failed|command not found|traceback|exception)\b", c, re.I):
                    errors += 1
    rereads = {fp: n for fp, n in reads.items() if n >= REREAD_N}
    return {
        "tools": tools,
        "tool_calls": sum(tools.values()),
        "rereads": rereads,
        "toolres_bytes": toolres_bytes,
        "oversize_hits": oversize_hits,
        "errors": errors,
        "text_bytes": text_bytes,
    }


def build_digest(days: int, deep: int) -> str:
    cutoff = dt.datetime.now().timestamp() - days * 86400
    files = [p for p in PROJECTS.rglob("*.jsonl") if p.stat().st_mtime >= cutoff]
    if not files:
        return ""

    # Phase A — cheap byte-level stats over ALL files (fast).
    per_project = defaultdict(lambda: {"sessions": 0, "bytes": 0})
    sized = []
    for p in files:
        proj = p.parent.name
        b = p.stat().st_size
        per_project[proj]["sessions"] += 1
        per_project[proj]["bytes"] += b
        sized.append((b, p))
    total_bytes = sum(b for b, _ in sized)
    sized.sort(reverse=True)

    # Phase B — deep-parse only the top-N biggest sessions (bounded CPU).
    agg_tools = Counter()
    agg_oversize = agg_errors = agg_toolres = 0
    reread_rows, offender_rows = [], []
    for b, p in sized[:deep]:
        m = mine_session(p)
        agg_tools.update(m["tools"])
        agg_oversize += m["oversize_hits"]
        agg_errors += m["errors"]
        agg_toolres += m["toolres_bytes"]
        if m["rereads"]:
            worst = sorted(m["rereads"].items(), key=lambda kv: -kv[1])[:3]
            reread_rows.append((p.parent.name, sum(m["rereads"].values()), worst))
        offender_rows.append((p.parent.name, token_proxy(b), m["tool_calls"],
                              m["oversize_hits"], m["errors"]))
    reread_rows.sort(key=lambda r: -r[1])
    offender_rows.sort(key=lambda r: -r[1])

    L = []
    L.append(f"# session digest — last {days} days")
    L.append(f"- total sessions: {len(files)}")
    L.append(f"- total volume: {total_bytes/1e6:.0f} MB (~{token_proxy(total_bytes):,} token-proxy)")
    L.append(f"- deep-parsed: top {min(deep,len(files))} biggest sessions\n")

    L.append("## volume by project")
    for proj, d in sorted(per_project.items(), key=lambda kv: -kv[1]["bytes"])[:15]:
        L.append(f"- {proj}: {d['sessions']} sessions, {d['bytes']/1e6:.0f} MB")

    L.append("\n## tool-call mix (deep sample)")
    for name, n in agg_tools.most_common(15):
        L.append(f"- {name}: {n}")
    L.append(f"\n- oversized tool_results (>{OVERSIZE} chars): {agg_oversize}")
    L.append(f"- tool_result bytes (deep sample): {agg_toolres/1e6:.1f} MB")
    L.append(f"- error/failure signals: {agg_errors}")

    L.append("\n## worst file re-read churn (same file Read many times in one session)")
    for proj, tot, worst in reread_rows[:12]:
        w = ", ".join(f"{Path(fp).name}×{n}" for fp, n in worst)
        L.append(f"- {proj}: {tot} redundant reads — {w}")

    L.append("\n## biggest sessions (token proxy / tool calls / bloat / errors)")
    for proj, tok, calls, over, err in offender_rows[:12]:
        L.append(f"- {proj}: ~{tok:,} tok, {calls} calls, {over} bloated results, {err} errors")

    return "\n".join(L)[:DIGEST_CAP]


HOOKS_DIR = Path.home() / ".claude" / "hooks"
SKILLS_DIR = Path.home() / ".claude" / "skills"
TOOLS_DIR = Path.home() / ".claude" / "tools"
CLAUDEMD = Path.home() / ".claude" / "CLAUDE.md"
SETTINGS = Path.home() / ".claude" / "settings.json"
WORKSTYLE = Path(__file__).with_name("harness-coach.workstyle.md")
SNAP_CAP = 12000


def _first_doc(path: Path) -> str:
    """One-line purpose of a hook/tool: first docstring or comment after shebang."""
    try:
        for ln in path.read_text(errors="replace").splitlines()[:12]:
            s = ln.strip().strip('"').strip("#").strip()
            if s and not s.startswith(("#!", '"""', "'''", "import", "from", "<?", "//")):
                return s[:100]
    except Exception:
        pass
    return ""


def harness_snapshot() -> str:
    """What the harness ALREADY has — so the model grounds advice instead of
    reinventing what exists. CLAUDE.md + wired hooks + skills + tools."""
    L = ["# CURRENT HARNESS (already installed — do NOT propose what exists here)"]
    if CLAUDEMD.exists():
        L.append("\n## global CLAUDE.md\n" + CLAUDEMD.read_text(errors="replace")[:3500])
    L.append("\n## hooks/ (installed)")
    for p in sorted(HOOKS_DIR.glob("*")):
        if p.suffix in (".py", ".sh", ".js"):
            L.append(f"- {p.name}: {_first_doc(p)}")
    L.append("\n## skills/ (installed)")
    L.append(", ".join(sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())) if SKILLS_DIR.exists() else "(none)")
    L.append("\n## tools/ (installed)")
    L.append(", ".join(sorted(p.name for p in TOOLS_DIR.iterdir())) if TOOLS_DIR.exists() else "(none)")
    if SETTINGS.exists():
        try:
            hk = json.loads(SETTINGS.read_text()).get("hooks", {})
            wired = {ev: [h.get("command", "").split("/")[-1].strip('"')
                          for grp in arr for h in grp.get("hooks", [])]
                     for ev, arr in hk.items()}
            L.append("\n## settings.json hook wiring\n" + json.dumps(wired, indent=0)[:1500])
        except Exception:
            pass
    return "\n".join(L)[:SNAP_CAP]


RUBRIC = """You are a senior harness engineer auditing an agentic Claude Code setup.
You are given the CURRENT HARNESS (what is already installed) and a DIGEST of real
sessions. CRITICAL: ground every finding in the current harness. For each finding,
tag it [NEW], [IMPROVE <existing file/skill>], or [ALREADY-COVERED-BY <x>] and do
NOT propose a hook/skill/rule that already exists — if it exists but isn't working,
say why and how to fix the existing one. Reference real filenames from the snapshot.
Known levers (ground your advice in these, add others you know):
TOKENS: targeted Reads with offset/limit over full re-reads; never re-read a file
you just edited; grep/rg over cat; truncate or avoid dumping huge tool_results;
parallelize independent tool calls; cache stable context; avoid redundant subagent
spawns; one-feature loops over hundreds of micro-prompts.
CODE QUALITY: decompose to spec'd units (CONTEXT/CHANGE/GOAL/VERIFY) for cheap
workers + an independent auditor; leave one runnable check per non-trivial unit;
prefer stdlib/native over new deps; shortest working diff.
Before calling a pattern "waste", CHECK IT AGAINST THE OPERATOR WORKSTYLE block.
Some high-volume patterns are deliberate technique: subagents that read/summarize
to keep the orchestrator lean are NOT waste (only flag redundant fanout — same
file re-fetched, unused outputs, a subagent for a trivial grep); session-start
re-reads of STATE.md/.handoff/.now are intended re-grounding; judge megasessions
by error rate + repeated identical failures, not raw call count. And never
propose a manually-invoked skill — he works conversationally, so fixes must be
ambient (hook / CLAUDE.md / injected context).
BIAS TO CUT, NOT ADD (empirical — arxiv 2602.11988: LLM-generated context files
REDUCED task success ~2% at +23% cost; more static context usually hurts). So:
prefer DELETING or SHRINKING a rule/doc/injection over adding one; every proposal
that ADDS tokens to the standing context must justify why the win beats the
per-turn cost it imposes; and actively hunt for stale/duplicated/never-obeyed
context already installed that should be removed. A shorter harness that is
actually obeyed beats a bigger one that is skimmed.
Your job: from the DIGEST of real sessions below, produce a PROPOSE-ONLY report.
Rank findings by token/quality impact. For each: the evidence in the digest, the
concrete fix, and a suggested diff to CLAUDE.md / a hook / a skill. Be specific and
lazy — no fluff. End with the single highest-leverage change to make this week."""


def _workstyle() -> str:
    try:
        return WORKSTYLE.read_text(errors="replace").strip()
    except Exception:
        return ""


def call_gpt55(digest: str, snapshot: str) -> str:
    ws = _workstyle()
    ws_block = f"\n\n=== OPERATOR WORKSTYLE (weigh before judging waste) ===\n{ws}\n" if ws else ""
    prompt = (f"{RUBRIC}{ws_block}\n\n=== {snapshot} ===\n\n=== DIGEST ===\n{digest}\n"
              f"\n=== END DIGEST ===\nWrite the report as markdown only.")
    try:
        r = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
             "-c", "approval_policy=never", "-"],
            input=prompt, capture_output=True, text=True, timeout=MODEL_TIMEOUT,
        )
        return r.stdout.strip()
    except Exception as e:
        return f"(model call failed: {e})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--deep", type=int, default=30)
    ap.add_argument("--no-model", action="store_true", help="digest only, skip GPT-5.5")
    a = ap.parse_args()

    digest = build_digest(a.days, a.deep)
    if not digest:
        print("no transcripts in window; nothing to do"); return

    if a.no_model:
        print(digest); return

    report = call_gpt55(digest, harness_snapshot())
    today = dt.date.today().isoformat()
    header = (f"# harness-coach — {today}\n"
              f"_propose-only. GPT-5.5 over the last {a.days} days of sessions. "
              f"Nothing was changed; you decide what to apply._\n\n")
    body = header + report + "\n\n---\n<details><summary>raw digest</summary>\n\n```\n" + digest + "\n```\n</details>\n"

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"{today}.md"
    tmp = out.with_suffix(".md.tmp")
    tmp.write_text(body)
    os.replace(tmp, out)      # atomic — no half-written report
    print(f"wrote {out}")
    try:
        subprocess.run(["osascript", "-e",
            f'display notification "harness-coach report ready: {today}" with title "harness-coach"'],
            timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()
