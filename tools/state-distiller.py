#!/usr/bin/env python3
"""STATE.md distiller — cap the GSD orientation log without losing history.

GSD's `.planning/STATE.md` is append-only and bloats to 40k–122k tokens, then is
re-read every session. This caps it DETERMINISTICALLY (no LLM, no network):
  HEAD = leading metadata (before the first heading) + the LAST top-level section
         (the newest resume-point), capped ~2000 tokens.
  ARCHIVE = the FULL original appended to `.planning/STATE-ARCHIVE.md` (nothing
            is ever lost — drill back there).
STATE.md is rewritten to HEAD + a drill-back footer. Idempotent: no-op below the
threshold. Not a hook — a CLI I run manually (dry-run default) in an idle window,
because it edits repo trees the live sessions own.

Usage:
  python3 state-distiller.py <repo_dir>            # DRY RUN (prints, writes nothing)
  python3 state-distiller.py <repo_dir> --apply    # perform the distill
  python3 state-distiller.py --selftest
"""
import os
import subprocess
import sys
from pathlib import Path

THRESHOLD_TOK = 12000      # below this, leave it alone
HEAD_CAP_CHARS = 8000      # ~2000 tokens


def toks(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text) // 4


def split_head(text: str) -> str:
    """Leading metadata (before first heading) + the last top-level (#/##) section."""
    lines = text.splitlines(keepends=True)
    head_idxs = [i for i, ln in enumerate(lines)
                 if ln.startswith("# ") or ln.startswith("## ")]
    if head_idxs:
        first, last = head_idxs[0], head_idxs[-1]
        lead = "".join(lines[:first])          # metadata block, may be empty
        newest = "".join(lines[last:])         # last section → EOF
        head = (lead + newest) if lead.strip() else newest
    else:
        head = text                            # no headings → whole thing is head
    if len(head) > HEAD_CAP_CHARS:
        head = "…[head truncated to newest content]…\n" + head[-HEAD_CAP_CHARS:]
    return head.rstrip()


def git_date(repo: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%cI"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown-date"
    except Exception:
        return "unknown-date"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def distill(repo_dir: str, apply: bool) -> str:
    repo = Path(repo_dir)
    state = repo / ".planning" / "STATE.md"
    if not state.exists():
        return f"no {state} — nothing to do."
    original = state.read_text(errors="replace")
    t0 = toks(original)
    if t0 < THRESHOLD_TOK:
        return f"{state}: ~{t0:,} tok < {THRESHOLD_TOK:,} threshold — already small, no-op."

    head = split_head(original)
    archive = repo / ".planning" / "STATE-ARCHIVE.md"
    footer = (f"\n\n---\nFull history archived → .planning/STATE-ARCHIVE.md "
              f"(was {len(original.splitlines()):,} lines / ~{t0:,} tokens). "
              f"Drill back there for older decisions.")
    new_state = head + footer
    t1 = toks(new_state)
    plan = (f"{state}: ~{t0:,} → ~{t1:,} tok "
            f"({100*(t0-t1)//max(t0,1)}% smaller). Archive += {len(original.splitlines()):,} lines.")

    if not apply:
        return "DRY RUN — " + plan + "\n(run with --apply to write)"

    sep = f"\n\n===== archived {git_date(repo)} =====\n\n"
    prior = archive.read_text(errors="replace") if archive.exists() else ""
    _atomic_write(archive, prior + sep + original)
    _atomic_write(state, new_state)
    # verify archive holds the original before declaring success
    assert original in archive.read_text(errors="replace"), "archive missing original!"
    return "APPLIED — " + plan


def _selftest() -> None:
    import tempfile
    d = tempfile.mkdtemp()
    repo = Path(d)
    (repo / ".planning").mkdir()
    state = repo / ".planning" / "STATE.md"
    big = ("---\nmeta: header\n---\n"
           + "# Old Section\n" + ("old log line\n" * 5000)
           + "\n## Newest Resume Point\nNOW: do X\nNEXT: do Y\n")
    state.write_text(big)
    orig = state.read_text()
    # dry run writes nothing
    out = distill(str(repo), apply=False)
    assert out.startswith("DRY RUN"), out
    assert state.read_text() == orig
    assert not (repo / ".planning" / "STATE-ARCHIVE.md").exists()
    # apply shrinks + preserves everything
    out = distill(str(repo), apply=True)
    assert out.startswith("APPLIED"), out
    new = state.read_text()
    assert len(new) < len(orig)
    assert "Newest Resume Point" in new           # kept the newest section
    assert "STATE-ARCHIVE.md" in new              # drill-back footer
    arch = (repo / ".planning" / "STATE-ARCHIVE.md").read_text()
    assert orig in arch                            # 100% preserved
    # idempotent-ish: re-running on the now-small file is a no-op
    assert "no-op" in distill(str(repo), apply=True)
    print("selftest passed")


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        _selftest()
        return
    if not args:
        print(__doc__)
        sys.exit(0)
    repo_dir = args[0]
    apply = "--apply" in args[1:]
    print(distill(repo_dir, apply))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"error (fail-safe, nothing written): {e}")
        sys.exit(0)
