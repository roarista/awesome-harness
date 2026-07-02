#!/usr/bin/env python3
"""PreCompact hook — cheap, recency-corrected handoff (anti-drift item #2).

Right before Claude Code auto-summarizes (which is recency-biased and drops
early-but-load-bearing decisions), this writes a fixed-size typed handoff so a
cold next-terminal can resume without re-reading the transcript.

Design (settled + council-hardened 2026-07-02):
  * Opt-in per repo: only runs where `.northstar.md` exists.
  * Reads only the transcript SLICE since the last handoff (fast, cheap).
  * Deterministically pre-filters that slice: drop thinking, truncate
    tool_results to ~200 chars, keep user/assistant text + tool names.
  * ONE model call via `claude -p --model haiku` (the only auth path that
    works from a hook — no raw API key reachable here). Input is our slim
    slice only, so the summarizer sees no tool noise regardless.
  * THE RATCHET (the fix for silent transitive forgetting): claims INHERITED
    from the prior handoff are trusted-carry — kept verbatim unless the new
    slice positively CONTRADICTS them. Only FRESH claims must be evidence-backed.
    A negative decision ("we chose NOT to do X") leaves no git artifact, so
    "verify against diff" must never delete it on mere absence of evidence.
  * FAIL-SAFE: temp-file + atomic rename ONLY on a validated result. Any
    timeout/error/empty leaves the prior handoff untouched (stale > none >
    clobbered) and does NOT advance the slice pointer, so it retries next time.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

STATE = Path.home() / ".claude" / "hooks" / "state" / "handoff_pos.json"
HANDOFF = ".handoff.md"
MODEL = "claude-haiku-4-5"
SLICE_CAP = 30000        # chars of pre-filtered slice fed to the model
TOOLRES_CAP = 200        # chars per tool_result (truncate, never drop)
CALL_TIMEOUT = 45        # seconds for the model call (hook timeout is 55)
REQUIRED = ("## 1. OBJECTIVE", "## 6. NEXT STEP")  # validation markers


def repo_root() -> Path:
    start = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    for d in [start, *start.parents]:
        if (d / ".northstar.md").exists() or (d / ".git").exists():
            return d
    return start


def load_pos() -> dict:
    try:
        return json.loads(STATE.read_text()) if STATE.exists() else {}
    except Exception:
        return {}


def save_pos(d: dict) -> None:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(d))
    except Exception:
        pass


def extract_text(line: str) -> str:
    """One transcript JSONL line -> compact text (thinking dropped, results
    truncated). Returns '' for lines with nothing worth carrying."""
    try:
        obj = json.loads(line)
    except Exception:
        return ""
    msg = obj.get("message") or obj
    role = obj.get("type") or msg.get("role") or ""
    content = msg.get("content")
    if isinstance(content, str):
        return f"{role.upper()}: {content}".strip()
    if not isinstance(content, list):
        return ""
    out = []
    for it in content:
        if not isinstance(it, dict):
            continue
        t = it.get("type")
        if t == "thinking":
            continue                                   # recency-irrelevant noise
        if t == "text":
            out.append(it.get("text", ""))
        elif t == "tool_use":
            out.append(f"[tool_use: {it.get('name', '?')}]")
        elif t == "tool_result":
            c = it.get("content", "")
            if isinstance(c, list):
                c = " ".join(
                    x.get("text", "") for x in c if isinstance(x, dict)
                )
            c = str(c).replace("\n", " ")
            out.append(f"[tool_result: {c[:TOOLRES_CAP]}]")
    body = " ".join(s for s in out if s).strip()
    return f"{role.upper()}: {body}" if body else ""


def prefilter(lines: list) -> str:
    kept, prev = [], None
    for ln in lines:
        txt = extract_text(ln)
        if txt and txt != prev:          # dedupe consecutive identical snapshots
            kept.append(txt)
            prev = txt
    blob = "\n".join(kept)
    if len(blob) > SLICE_CAP:            # keep head + tail if oversized
        half = SLICE_CAP // 2
        blob = blob[:half] + "\n…[slice truncated]…\n" + blob[-half:]
    return blob


def git_diff(root: Path) -> str:
    if not (root / ".git").exists():
        return ""
    try:
        stat = subprocess.run(
            ["git", "-C", str(root), "diff", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        log = subprocess.run(
            ["git", "-C", str(root), "log", "-5", "--pretty=%s"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        return f"recent commits:\n{log}\nuncommitted:\n{stat}"[:2000]
    except Exception:
        return ""


def build_prompt(slice_txt: str, prior: str, diff: str) -> str:
    return f"""You write a RESUME HANDOFF for a fresh terminal that will have ZERO prior context. Output ONLY the handoff in the exact 7-section format below — no preamble.

THE RATCHET RULE (critical):
- Claims in the PRIOR HANDOFF are trusted-carry. Copy them forward VERBATIM unless the NEW SLICE explicitly CONTRADICTS them.
- NEVER delete a prior claim just because the new slice or git diff doesn't mention it. Settled/negative decisions ("we decided NOT to do X", "X is a trap") leave no artifact — losing them is the main failure to avoid.
- Only claims you ADD from the new slice need support from the slice or git diff. Do not invent.

Emit EXACTLY these sections (keep each tight, bullet points):
# HANDOFF (auto — overwritten each compaction; hand-edit survives only until next compaction)
## 1. OBJECTIVE
## 2. DECISIONS + RATIONALE
## 3. OPEN QUESTIONS + BUGS
## 4. CONSTRAINTS + TRAPS
## 5. FILES + COMMANDS
## 6. NEXT STEP
## 7. SOURCE POINTERS

=== PRIOR HANDOFF (trusted-carry) ===
{prior or '(none — first handoff)'}

=== GIT (ground truth) ===
{diff or '(no git)'}

=== NEW CONVERSATION SLICE (since last handoff) ===
{slice_txt}
"""


def call_model(prompt: str) -> str:
    claude = shutil.which("claude") or str(
        Path.home() / ".npm-global" / "bin" / "claude"
    )
    env = {**os.environ, "CLAUDE_HANDOFF_CHILD": "1"}  # recursion guard
    try:
        r = subprocess.run(
            [claude, "-p", "--model", MODEL],
            input=prompt, capture_output=True, text=True,
            timeout=CALL_TIMEOUT, env=env,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def stable_files(lines: list) -> str:
    """Files Read this session but never Edited/Written — safe to NOT re-read
    next session (they're already-seen and unchanged by us). Cheap: scans only
    tool_use names + file_path, not content. This is the anti-re-read-churn note."""
    read, edited = [], set()
    for ln in lines:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        msg = obj.get("message", obj)
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict) or it.get("type") != "tool_use":
                continue
            fp = (it.get("input") or {}).get("file_path")
            if not fp:
                continue
            name = it.get("name", "")
            if name in ("Edit", "Write", "MultiEdit"):
                edited.add(fp)
            elif name == "Read" and fp not in read:
                read.append(fp)
    stable = [f for f in read if f not in edited]
    if not stable:
        return ""
    shown = stable[-12:]                      # most-recent dozen
    return ("\n\nSTABLE FILES (read this session, not changed by us — do NOT "
            "re-read unless you're about to edit them):\n"
            + "\n".join("  - " + f for f in shown))


def _do_handoff(tpath: str, root: Path) -> None:
    """The slow half (a ~30-60s model call). Runs in a DETACHED worker, never
    in the hook itself — so /compact is never blocked on it."""
    lines = Path(tpath).read_text(errors="replace").splitlines()
    pos = load_pos()
    start = int(pos.get(tpath, 0))
    slice_lines = lines[start:]
    if not slice_lines:
        return

    slice_txt = prefilter(slice_lines)
    if not slice_txt.strip():
        return

    prior_path = root / HANDOFF
    prior = prior_path.read_text(errors="replace") if prior_path.exists() else ""
    out = call_model(build_prompt(slice_txt, prior, git_diff(root)))

    if not out or not all(m in out for m in REQUIRED):
        return  # FAIL-SAFE: don't touch handoff, don't advance pointer → retry

    out += stable_files(lines)           # append the anti-re-read-churn note

    tmp = prior_path.with_suffix(".md.tmp")
    tmp.write_text(out)
    os.replace(tmp, prior_path)          # atomic; only after validation
    pos[tpath] = len(lines)
    save_pos(pos)


def main() -> None:
    if os.environ.get("CLAUDE_HANDOFF_CHILD"):
        return  # never recurse into ourselves from the child claude call

    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    tpath = data.get("transcript_path", "")
    if not tpath or not Path(tpath).exists():
        return

    root = repo_root()
    if not (root / ".northstar.md").exists():
        return  # opt-in

    # The handoff needs a ~30-60s model call, but it only has to exist by the
    # NEXT session start — NOT before compaction finishes. So fork a fully
    # detached worker (its own session, no controlling terminal, std streams to
    # /dev/null) and return instantly. This is the fix for "/compact stalls if I
    # background the terminal": the hook no longer blocks, so nothing to stall.
    try:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--worker", tpath, str(root)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True, cwd=str(root),
        )
    except Exception:
        pass  # if we can't spawn, better to let compaction proceed unhanded-off


if __name__ == "__main__":
    try:
        if len(sys.argv) > 3 and sys.argv[1] == "--worker":
            _do_handoff(sys.argv[2], Path(sys.argv[3]))
        else:
            main()
    except Exception:
        sys.exit(0)  # never block compaction over the handoff
