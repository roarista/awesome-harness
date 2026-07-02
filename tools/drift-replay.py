#!/usr/bin/env python3
"""Drift-judge REPLAY harness (anti-drift item #4 — instrument before you build).

Before committing an LLM drift-judge as a LIVE layer, measure how often it fires
on REAL past sessions. A judge that cries wolf on normal work (research detours,
debugging, tool spelunking) is worse than none. This replays a transcript,
samples checkpoints, asks a cheap model "on-track or drift?", and reports the
FIRING RATE + dumps every firing with context so a human can judge true vs false.

Usage:
  drift-replay.py <transcript.jsonl> [--max-checks N] [--every K] [--out FILE]

Not a hook, not wired anywhere — a one-shot measurement tool. Bounded by
--max-checks (default 15) so cost/CPU stay capped (each check = one haiku call).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLRES_CAP = 200
WINDOW = 8            # recent extracted entries shown to the judge as "activity"
MODEL = "claude-haiku-4-5"
CALL_TIMEOUT = 40


def extract(obj: dict) -> str:
    msg = obj.get("message") or obj
    role = obj.get("type") or msg.get("role") or ""
    content = msg.get("content")
    if isinstance(content, str):
        return f"{role}: {content}".strip()
    if not isinstance(content, list):
        return ""
    out = []
    for it in content:
        if not isinstance(it, dict):
            continue
        t = it.get("type")
        if t == "thinking":
            continue
        if t == "text":
            out.append(it.get("text", ""))
        elif t == "tool_use":
            inp = it.get("input", {})
            hint = inp.get("command") or inp.get("file_path") or inp.get("description") or ""
            out.append(f"[tool_use {it.get('name','?')}: {str(hint)[:80]}]")
        elif t == "tool_result":
            c = it.get("content", "")
            if isinstance(c, list):
                c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
            out.append(f"[tool_result: {str(c).replace(chr(10),' ')[:TOOLRES_CAP]}]")
    body = " ".join(s for s in out if s).strip()
    return f"{role}: {body}" if body else ""


def first_user_objective(entries: list) -> str:
    """The session's de-facto objective = first substantial user message that
    isn't a hook/command/system-reminder injection."""
    for e in entries:
        if not e.startswith("user:"):
            continue
        body = e[5:].strip()
        if len(body) < 25:
            continue
        if body.startswith(("<", "Caveat:", "[")) or "system-reminder" in body[:60]:
            continue
        return body[:600]
    return "(no clear objective found)"


def judge(objective: str, activity: str) -> tuple:
    claude = shutil.which("claude") or str(Path.home() / ".npm-global" / "bin" / "claude")
    prompt = (
        "You are a strict drift auditor. Given a session OBJECTIVE and the agent's "
        "RECENT ACTIVITY, decide if the activity still serves the objective or has "
        "DRIFTED to unrelated work. Normal sub-steps (research, debugging, reading "
        "files, tool use, tangents that still serve the goal) are ON_TRACK — only "
        "genuinely off-goal work is DRIFT.\n"
        "Reply on ONE line, exactly: `ON_TRACK: <=12 words` or `DRIFT: <=12 words`.\n\n"
        f"OBJECTIVE:\n{objective}\n\nRECENT ACTIVITY:\n{activity}"
    )
    try:
        r = subprocess.run(
            [claude, "-p", "--model", MODEL], input=prompt,
            capture_output=True, text=True, timeout=CALL_TIMEOUT,
            env={**os.environ, "CLAUDE_HANDOFF_CHILD": "1"},
        )
        v = r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        v = ""
    vs = v.lstrip("`*_ \t\n").upper()   # strip markdown/quote noise before matching
    verdict = "DRIFT" if vs.startswith("DRIFT") else (
        "ON_TRACK" if vs.startswith("ON_TRACK") else "ERROR")
    return verdict, v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--max-checks", type=int, default=15)
    ap.add_argument("--every", type=int, default=0, help="0 = auto-spread")
    ap.add_argument("--out", default="")
    ap.add_argument("--objective", default="", help="override the auto-detected objective")
    a = ap.parse_args()

    raw = Path(a.transcript).read_text(errors="replace").splitlines()
    entries = []
    for ln in raw:
        try:
            e = extract(json.loads(ln))
        except Exception:
            e = ""
        if e:
            entries.append(e)

    objective = a.objective or first_user_objective(entries)
    # checkpoints = assistant entries that took an action or spoke
    idxs = [i for i, e in enumerate(entries) if e.startswith("assistant:")]
    if not idxs:
        print("no assistant turns found"); return
    every = a.every or max(1, len(idxs) // a.max_checks)
    checkpoints = idxs[::every][: a.max_checks]

    results = []
    for n, i in enumerate(checkpoints, 1):
        activity = "\n".join(entries[max(0, i - WINDOW): i + 1])[:4000]
        verdict, line = judge(objective, activity)
        results.append((i, verdict, line, activity))
        print(f"[{n}/{len(checkpoints)}] turn~{i}: {verdict}  {line[:70]}", file=sys.stderr)

    fires = [r for r in results if r[1] == "DRIFT"]
    errs = [r for r in results if r[1] == "ERROR"]
    scored = len(results) - len(errs)
    rate = (len(fires) / scored * 100) if scored else 0
    print(f"\n=== FIRING RATE: {len(fires)}/{scored} = {rate:.0f}% DRIFT "
          f"({len(errs)} errors) ===")
    print(f"OBJECTIVE: {objective[:120]}")

    if a.out:
        with open(a.out, "w") as fh:
            fh.write(f"OBJECTIVE:\n{objective}\n\nFIRING RATE: {len(fires)}/{scored} = {rate:.0f}%\n\n")
            for i, verdict, line, activity in fires:
                fh.write(f"\n{'='*60}\n[DRIFT @ turn~{i}] {line}\nCONTEXT:\n{activity[:1500]}\n")
        print(f"firings written to {a.out}")


if __name__ == "__main__":
    main()
