#!/usr/bin/env python3
"""claudemd-trim — weekly, PROPOSE-ONLY CLAUDE.md diet, grounded in a real code map.

CLAUDE.md is read by every agent on every session, so a stale or duplicated line is
the most expensive text in the system (arxiv 2602.11988: LLM-generated context files
REDUCED task success ~2% at +23% cost). This classifies EVERY substantive line of a
repo's CLAUDE.md as KEEP / TRIM / DELETE / STALE-WRONG with evidence.

*** IT NEVER EDITS ANY REPO'S CLAUDE.md. ***
The only write path for its OUTPUT is `_write_report()`, which refuses any destination
outside OUTDIR (~/engineering-harness/reports/claudemd-trim by default). Proposal only:
Ro reads the report and applies by hand. By default it writes only its report; with
--refresh it ALSO runs `graphify update` in the target repo (which creates/updates
graphify-out/ there), so --refresh is opt-in and off by default.

Two stages, same shape as tools/harness-coach.py:
  1. DETERMINISTIC (no model, and the highest-value check): every path/command a line
     names is resolved on disk (reusing tools/check-all/claudemd_drift.py) -> a line
     naming something that no longer exists is STALE-WRONG. Lines duplicated by another
     always-loaded doc (global CLAUDE.md, AGENTS.md, .claude/CLAUDE.md) are TRIM,
     naming where the duplicate lives.
  2. MODEL (`codex exec`, absolute path — launchd PATH is minimal): judges the REMAINING
     lines for load-bearingness against a real map of the tree (graphify graph.json +
     git file list), not from imagination.

Run: python3 claudemd-trim.py [REPO ...] [--no-model] [--selftest] [--stdout]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "check-all"))
import claudemd_drift as drift  # noqa: E402  (reuse: path candidate + existence logic)

OUTDIR = Path.home() / "engineering-harness" / "reports" / "claudemd-trim"
CODEX = Path.home() / ".npm-global" / "bin" / "codex"   # absolute: launchd PATH lacks it
GRAPHIFY = Path.home() / ".local" / "bin" / "graphify"
DEFAULT_REPOS = [
    Path.home() / "Downloads" / "Vividlist",
    Path.home() / "Downloads" / "intrn",
    Path.home() / "Downloads" / "virality-pipeline",
    Path.home() / "Downloads" / "forclosurehomes",
    Path.home() / "Downloads" / "awesome-harness",
]
# Always-loaded docs a CLAUDE.md line may be duplicating.
OVERLAP_DOCS = [
    Path.home() / ".claude" / "CLAUDE.md",
    Path("AGENTS.md"),
    Path(".claude") / "CLAUDE.md",
    Path(".claude") / "AGENTS.md",
]
MODEL_TIMEOUT = 900
MAP_CAP = 6000
DOC_CAP = 30000
# Words that are prose, not shell commands, even in backticks.
_IMPERATIVE_RE = re.compile(r"\b(run|runs|running|exec|execute|invoke|call|use)\b[^`]{0,20}$", re.I)
_NOT_CMDS = {"true", "false", "none", "null", "n", "x", "y", "and", "or", "not"}
# Shell metacharacters: their presence marks an illustrative one-liner, not a reference.
_SHELL_META = '>|$"&;'
# A line that ASSERTS a file is gone must not be flagged for naming that file.
_ASSERTS_ABSENT_RE = re.compile(
    r"(does ?n[o']?t exist|no longer (exists?|on|in)|not on trunk|unmerged|"
    r"never (generated|created|committed|existed|written)|was (deleted|removed)|"
    r"\b(deleted|removed|absent|missing|gone|nonexistent)\b)", re.I)
# Auto-generated blocks (Repowise et al.) are machine-owned: classifying them is noise.
_GEN_START_RE = re.compile(r"<!--.*\b[A-Z][A-Z0-9_]*:START\b", re.I)
_GEN_END_RE = re.compile(r"<!--.*\b[A-Z][A-Z0-9_]*:END\b", re.I)


# ---------------------------------------------------------------- deterministic

def substantive_lines(text: str) -> list:
    """(lineno, line) for lines carrying a HUMAN claim.

    Skips blanks, fence markers, HTML comments, and everything inside an
    auto-generated `<!-- X:START -->`/`<!-- X:END -->` block. Generated blocks are
    owned by the generator (Repowise), so proposing trims for them is noise: the
    next regeneration would restore every line.
    """
    out, in_fence, in_gen = [], False, False
    for i, ln in enumerate(text.splitlines(), 1):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if _GEN_START_RE.search(ln):
            in_gen = True
            continue
        if _GEN_END_RE.search(ln):
            in_gen = False
            continue
        if in_fence or in_gen or not ln.strip():
            continue
        if ln.lstrip().startswith("<!--"):
            continue
        out.append((i, ln))
    return out


def _shell_snippet_tokens(line: str) -> set:
    """Tokens inside a backticked snippet that carries shell metacharacters.

    `cmd > out.txt 2>&1` is an illustrative one-liner; `out.txt` is a name the command
    CREATES, not a file that is supposed to exist. Same exclusion missing_commands()
    already applies.
    """
    out = set()
    for m in re.finditer(r"`([^`\n]+?)`", line):
        s = m.group(1)
        if any(ch in s for ch in _SHELL_META):
            out.update(p.strip("`,;:") for p in s.split())
    return out


def _clean_occurrence(tok: str, line: str) -> bool:
    """True if `tok` appears in `line` at real token boundaries.

    The bare-token extractor can chop a longer token: `graphify-out/graph.json` ->
    `graph.js` (extension alternation matched `.js` first), `~/awesome-harness/docs/x.md`
    -> `harness/docs/x.md`. Such a fragment is always glued to a word/path character on
    one side, so it never has a clean occurrence — and must not be resolved on disk.
    """
    for m in re.finditer(re.escape(tok), line):
        before = line[m.start() - 1] if m.start() else ""
        after = line[m.end():m.end() + 2]
        if before and before in "~./-" or (before and (before.isalnum() or before in "_/")):
            continue
        if after[:1].isalnum() or after[:1] == "_":
            continue
        if after[:1] == "." and after[1:2].isalnum():
            continue
        return True
    return False


def missing_refs(line: str, repo: Path) -> list:
    """Path tokens in this line that do NOT exist on disk. Deterministic, no model."""
    if _ASSERTS_ABSENT_RE.search(line):
        return []                                  # the line's CLAIM is the absence
    shelly = _shell_snippet_tokens(line)
    bad = []
    for tok in drift.extract_path_candidates(line):
        if not drift.looks_like_path(tok) or tok in shelly:
            continue
        if not _clean_occurrence(tok, line):
            # fragment: recover a `~`-rooted path the extractor truncated, else drop it
            m = re.search(r"(~[\w./-]*/%s)" % re.escape(tok), line)
            if not m:
                continue
            tok = m.group(1)
        if not drift.path_exists_anywhere(tok, repo):
            bad.append(tok)
    return bad


def missing_commands(line: str) -> list:
    """Backticked shell commands whose executable does not resolve on PATH.

    Deliberately high-precision: a false "this command is gone" is worse than a miss
    in a propose-only report. A snippet counts as a real command reference only when
    (a) an imperative verb introduces it and (b) it has no shell metacharacters —
    those mark an illustrative one-liner (`cmd > out.txt 2>&1`) rather than a
    reference to a tool that is supposed to exist.
    """
    bad = []
    for m in re.finditer(r"`([^`\n]+?)`", line):
        snippet = m.group(1).strip()
        if not _IMPERATIVE_RE.search(line[max(0, m.start() - 30):m.start()]):
            continue
        if any(ch in snippet for ch in '>|$"&;'):
            continue
        parts = snippet.split()
        if not parts:
            continue
        head = parts[0]
        if len(parts) < 2:                       # single token: probably a name, not a cmd
            continue
        if not re.fullmatch(r"[a-z][a-z0-9._-]*", head) or head in _NOT_CMDS:
            continue
        if "/" in head or head.startswith(("$", "-")):
            continue
        if shutil.which(head) is None:
            bad.append(head)
    return bad


def _norm(s: str) -> str:
    """Normalize a doc line for duplicate detection across docs."""
    s = re.sub(r"[`*_#>-]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def overlap_index(repo: Path, self_doc: Path) -> dict:
    """normalized line -> which always-loaded doc already says it.

    `self_doc` (the CLAUDE.md being audited) is excluded, or every line would report
    itself as its own duplicate.
    """
    idx = {}
    for d in OVERLAP_DOCS:
        p = d if d.is_absolute() else repo / d
        if not p.exists() or p.resolve() == self_doc.resolve():
            continue
        try:
            for ln in p.read_text(errors="replace").splitlines():
                n = _norm(ln)
                if len(n) >= 40:                 # short lines collide by accident
                    idx.setdefault(n, str(p))
        except OSError:
            continue
    return idx


def classify(repo: Path, text: str, self_doc: Path = None) -> list:
    """Deterministic verdicts. Lines with no mechanical verdict get verdict=None
    and are handed to the model stage."""
    dup = overlap_index(repo, self_doc or (repo / "CLAUDE.md"))
    rows = []
    for lineno, line in substantive_lines(text):
        paths, cmds = missing_refs(line, repo), missing_commands(line)
        if paths or cmds:
            ev = []
            if paths:
                ev.append("no referent found in tree: " + ", ".join(paths))
            if cmds:
                ev.append("command not resolvable: " + ", ".join(cmds))
            rows.append({"line": lineno, "text": line, "verdict": "STALE-WRONG",
                         "evidence": "; ".join(ev)})
            continue
        n = _norm(line)
        if len(n) >= 40 and n in dup:
            rows.append({"line": lineno, "text": line, "verdict": "TRIM",
                         "evidence": "duplicated by " + dup[n]})
            continue
        rows.append({"line": lineno, "text": line, "verdict": None, "evidence": ""})
    return rows


def projected_size(text: str, rows: list) -> int:
    """Bytes remaining after removing every TRIM/DELETE/STALE-WRONG line."""
    cut = {r["line"] for r in rows if r["verdict"] in ("TRIM", "DELETE", "STALE-WRONG")}
    lines = text.splitlines(keepends=True)
    return sum(len(ln.encode()) for i, ln in enumerate(lines, 1) if i not in cut)


# ---------------------------------------------------------------------- the map

def code_map(repo: Path, refresh: bool = False) -> str:
    """A REAL map of the repo: graphify graph (refreshed if present) + tracked files."""
    L = []
    graph = repo / "graphify-out" / "graph.json"
    if graph.exists():
        if refresh and GRAPHIFY.exists():
            try:
                subprocess.run([str(GRAPHIFY), "update", str(repo), "--no-cluster"],
                               capture_output=True, text=True, timeout=600)
            except Exception as e:
                L.append("(graphify update failed: %s)" % e)
        try:
            g = json.loads(graph.read_text(errors="replace"))
            nodes = g.get("nodes", [])
            L.append("## graphify map: %d nodes, %d edges" % (len(nodes), len(g.get("edges", []))))
            labels = [str(n.get("label") or n.get("id")) for n in nodes[:400]]
            L.append("nodes: " + ", ".join(labels))
        except Exception as e:
            L.append("(graph.json unreadable: %s)" % e)
    else:
        L.append("## graphify map: none (no graphify-out/graph.json)")
    try:
        files = subprocess.run(["git", "-C", str(repo), "ls-files"],
                               capture_output=True, text=True, timeout=60).stdout.split()
        L.append("\n## tracked files (%d)\n" % len(files) + "\n".join(files[:500]))
    except Exception as e:
        L.append("(git ls-files failed: %s)" % e)
    return "\n".join(L)[:MAP_CAP]


RUBRIC = """You are auditing a repo's CLAUDE.md — the file EVERY agent loads on EVERY
session. Empirically (arxiv 2602.11988) bloated context files REDUCE task success at
higher cost, so the bias is to CUT. You are given a real MAP of the repo (graphify
nodes + tracked files) and the UNRESOLVED lines of CLAUDE.md (lines already proven
stale or duplicated were removed before you saw them).

For EACH line given, output exactly one row:
  <lineno> | KEEP|TRIM|DELETE | <evidence>

KEEP  = load-bearing and true: a non-obvious fact about THIS repo an agent needs and
        cannot cheaply derive. Evidence must name a file/symbol from the MAP.
TRIM  = true but bloated — say what the one-line version is.
DELETE= not load-bearing: generic LLM advice, restated defaults, history/changelog,
        aspiration, or something the agent would do anyway.
Never invent a file. If the MAP does not support a claim, say "unsupported by map"
and DELETE or TRIM. No preamble, no summary — rows only."""


def call_model(repo: Path, rows: list, mapping: str) -> str:
    pend = [r for r in rows if r["verdict"] is None]
    if not pend:
        return ""
    body = "\n".join("%d | %s" % (r["line"], r["text"]) for r in pend)[:DOC_CAP]
    prompt = ("%s\n\n=== MAP of %s ===\n%s\n\n=== CLAUDE.md LINES ===\n%s\n=== END ===\nRows only."
              % (RUBRIC, repo, mapping, body))
    if not CODEX.exists():
        return "(model stage skipped: %s not found)" % CODEX
    try:
        r = subprocess.run([str(CODEX), "exec", "--skip-git-repo-check", "--sandbox",
                            "read-only", "-c", "approval_policy=never", "-"],
                           input=prompt, capture_output=True, text=True,
                           timeout=MODEL_TIMEOUT)
        if r.returncode != 0:
            return "(model stage failed: codex exit %d: %s)" % (r.returncode, (r.stderr or "")[:300])
        return r.stdout.strip() or "(model stage produced no output)"
    except Exception as e:
        return "(model stage failed: %s)" % e


def merge_model(rows: list, model_out: str) -> None:
    """Fold `lineno | VERDICT | evidence` rows into the pending lines."""
    for m in re.finditer(r"^\s*(\d+)\s*\|\s*(KEEP|TRIM|DELETE)\s*\|\s*(.*)$",
                         model_out, re.M):
        lineno, verdict, ev = int(m.group(1)), m.group(2), m.group(3).strip()
        for r in rows:
            if r["line"] == lineno and r["verdict"] is None:
                r["verdict"], r["evidence"] = verdict, ev or "(model, no evidence given)"


# ------------------------------------------------------------------ report i/o

def _write_report(name: str, body: str) -> Path:
    """The ONLY write path in this program.

    Hard guard: the destination must resolve INSIDE OUTDIR. A CLAUDE.md — in a target
    repo or anywhere else — can never be reached from here, so the tool is structurally
    incapable of editing a repo.
    """
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = (OUTDIR / name).resolve()
    if out.parent != OUTDIR.resolve() or out.name.upper() == "CLAUDE.MD":
        raise RuntimeError("refusing to write outside the report dir: %s" % out)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(body)
    os.replace(tmp, out)          # atomic — never a half-written report
    return out


def render(repo: Path, md: Path, text: str, rows: list, model_note: str) -> str:
    cur = len(text.encode())
    proj = projected_size(text, rows)
    counts = {v: sum(1 for r in rows if r["verdict"] == v)
              for v in ("KEEP", "TRIM", "DELETE", "STALE-WRONG", None)}
    L = ["# CLAUDE.md trim proposal — %s — %s" % (repo.name, dt.date.today().isoformat()),
         "",
         "_PROPOSE ONLY. No CLAUDE.md was edited. This run writes only its report; "
         "with `--refresh` it also runs `graphify update` in the target repo._",
         "",
         "- file: `%s`" % md,
         "- CURRENT size: **%s bytes** (%d lines)" % (format(cur, ","), len(text.splitlines())),
         "- PROJECTED after all TRIM+DELETE+STALE-WRONG: **%s bytes** (%d%% smaller)"
         % (format(proj, ","), 100 - proj * 100 // max(cur, 1)),
         "- verdicts: KEEP %d · TRIM %d · DELETE %d · STALE-WRONG %d · unclassified %d"
         % (counts["KEEP"], counts["TRIM"], counts["DELETE"], counts["STALE-WRONG"], counts[None]),
         ""]
    for v in ("STALE-WRONG", "DELETE", "TRIM", "KEEP", None):
        sel = [r for r in rows if r["verdict"] == v]
        if not sel:
            continue
        L += ["## %s (%d)" % (v or "UNCLASSIFIED (model stage gave no verdict)", len(sel)),
              "", "| line | claim | evidence |", "|---|---|---|"]
        for r in sel:
            t = r["text"].strip().replace("|", "\\|")[:180]
            e = (r["evidence"] or "").replace("|", "\\|")[:180]
            L.append("| %d | %s | %s |" % (r["line"], t, e))
        L.append("")
    if model_note:
        L += ["<details><summary>raw model output</summary>", "", "```",
              model_note[:20000], "```", "</details>"]
    return "\n".join(L) + "\n"


def audit(repo: Path, use_model: bool, refresh: bool, to_stdout: bool):
    md = repo / "CLAUDE.md"
    if not md.exists():
        md = repo / ".claude" / "CLAUDE.md"
    if not md.exists():
        print("%s: no CLAUDE.md, skipping" % repo.name)
        return None
    text = md.read_text(errors="replace")
    rows = classify(repo, text, md)
    note = ""
    if use_model:
        note = call_model(repo, rows, code_map(repo, refresh))
        merge_model(rows, note)
    body = render(repo, md, text, rows, note)
    if to_stdout:
        print(body)
        return None
    return _write_report("%s-%s.md" % (dt.date.today().isoformat(), repo.name), body)


# -------------------------------------------------------------------- selftest

def _selftest() -> int:
    """Prove the deterministic stale-path classifier: one real path, one dead path."""
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "real_file.py").write_text("x = 1\n")
        (repo / "CLAUDE.md").write_text(
            "# T\n"
            "- The entry point is `real_file.py` and it works.\n"
            "- The pipeline lives in `does_not_exist/ghost.py` and runs nightly.\n"
        )
        rows = classify(repo, (repo / "CLAUDE.md").read_text())
        by = {r["line"]: r for r in rows}
        good, dead = by.get(2), by.get(3)
        ok &= good is not None and good["verdict"] is None
        print("existing path  -> verdict=%r (want None/not stale)" % (good and good["verdict"]))
        ok &= dead is not None and dead["verdict"] == "STALE-WRONG" \
            and "does_not_exist/ghost.py" in dead["evidence"]
        print("missing path   -> verdict=%r evidence=%r (want STALE-WRONG)"
              % (dead and dead["verdict"], dead and dead["evidence"]))

        # regressions: the three proven STALE-WRONG false positives (auditor, 2026-08-01)
        for label, line in (
            ("tilde-truncation",
             "See ~/awesome-harness/docs/CODING_AGENT_PROMPTING.md for how to prompt."),
            ("ext-truncation",
             "The code map lives at graphify-out/graph.json and is rebuilt weekly."),
            ("shell-one-liner",
             'Run `cmd > out.txt 2>&1; echo rc=$? >> out.txt`, then read the rc.'),
            ("asserts-absent",
             "DOCS THAT ARE NOT ON TRUNK: `PRODUCT_LOCK_2026-05-14.md` was never committed."),
        ):
            got = missing_refs(line, repo)
            ok &= not got
            print("%-17s-> missing_refs=%r (want [])" % (label, got))

        # generated blocks are not classified at all
        gen = ("# T\n"
               "<!-- REPOWISE:START -->\n"
               "- generated claim about `ghost_a.py`\n"
               "- generated claim about `ghost_b.py`\n"
               "<!-- REPOWISE:END -->\n"
               "- human claim about `real_file.py`\n")
        n = len(substantive_lines(gen))
        ok &= n == 2                       # heading + the one human line
        print("generated block  -> %d substantive lines (want 2)" % n)

        # the write guard cannot be talked into touching a CLAUDE.md
        try:
            _write_report("../../Downloads/Vividlist/CLAUDE.md", "pwned")
            ok = False
            print("write guard    -> ESCAPED (BAD)")
        except RuntimeError as e:
            print("write guard    -> refused: %s" % e)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(description="propose-only CLAUDE.md trim audit")
    ap.add_argument("repos", nargs="*", help="repo paths (default: the 4 live repos + pilot)")
    ap.add_argument("--no-model", action="store_true", help="deterministic stage only")
    ap.add_argument("--refresh", action="store_true",
                    help="ALSO run `graphify update` inside the target repo (writes there)")
    ap.add_argument("--no-refresh", action="store_true",
                    help="deprecated no-op: not refreshing is now the default")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing a report")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    repos = [Path(r).expanduser().resolve() for r in a.repos] or DEFAULT_REPOS
    written = []
    for repo in repos:
        if not repo.exists():
            print("%s: missing, skipping" % repo, file=sys.stderr)
            continue
        try:
            p = audit(repo, not a.no_model, a.refresh and not a.no_refresh, a.stdout)
            if p:
                written.append(p)
                print("wrote %s" % p)
        except Exception as e:                     # one bad repo must not kill the run
            print("%s: FAILED: %s" % (repo.name, e), file=sys.stderr)
    if written:
        try:
            subprocess.run(["osascript", "-e",
                            'display notification "%d CLAUDE.md trim proposals" '
                            'with title "claudemd-trim"' % len(written)], timeout=10)
        except Exception:
            pass


if __name__ == "__main__":
    main()
