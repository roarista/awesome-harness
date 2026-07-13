#!/usr/bin/env python3
"""Filesize-cap PreToolUse Read guard — proactive nudge before a full slurp.

Reading a huge file WHOLE dumps the entire thing into context and burns
headroom for zero targeting. The reread-guard catches the *second* full read of
a file you already have; this one fires on the *first* — before you slurp a big
file at all — nudging you to read a range, grep, or use graphify instead.

Fires only when ALL hold:
  * tool is Read, tool_input.file_path resolves to an existing, TEXT file
  * the file is LARGE: >= 2000 lines OR >= 200 KB
  * the Read is a FULL slurp: no `offset` and no `limit` in tool_input

Advisory only: emits additionalContext via the standard hook JSON shape and
exits 0. NEVER blocks, NEVER denies. Partial read (offset OR limit) → silent.
Non-text / binary / missing / small → silent. Kill-switch FILESIZE_CAP=0 →
no-op. Fail-open on any error.
"""
import json
import os
import sys

MIN_LINES = 2000
MIN_BYTES = 200 * 1024   # 200 KB


def _is_text(path: str) -> bool:
    """Cheap binary sniff: NUL byte in the first 8 KB → treat as binary."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" not in chunk
    except OSError:
        return False


def _count_lines(path: str) -> int:
    try:
        n = 0
        with open(path, "rb") as f:
            for _ in f:
                n += 1
        return n
    except OSError:
        return 0


def _full_read(ti: dict) -> bool:
    return not ti.get("offset") and not ti.get("limit")


def evaluate(ti: dict) -> str:
    """Return the nudge string, or '' when the hook should stay silent."""
    fp = str(ti.get("file_path", "") or "")
    if not fp:
        return ""
    if not _full_read(ti):
        return ""
    ap = fp if os.path.isabs(fp) else os.path.join(os.getcwd(), fp)
    try:
        st = os.stat(ap)
    except OSError:
        return ""
    if not os.path.isfile(ap):
        return ""
    if not _is_text(ap):
        return ""
    size = st.st_size
    lines = _count_lines(ap)
    if lines < MIN_LINES and size < MIN_BYTES:
        return ""
    rel = os.path.relpath(ap, os.getcwd()) if ap.startswith(os.getcwd()) else ap
    return (
        f"LARGE FILE ({lines:,} lines, {size // 1024:,} KB): {rel}. slurping whole file. "
        f"prefer targeted: offset/limit span, grep the symbol, or graphify — not all {lines:,} lines."
    )


def main() -> None:
    if os.environ.get("FILESIZE_CAP") == "0":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") != "Read":
        return
    ti = data.get("tool_input", {}) or {}
    msg = evaluate(ti)
    if not msg:
        return
    print(json.dumps({
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": msg,
        },
    }))


def _selftest() -> None:
    import tempfile
    d = tempfile.mkdtemp()
    big = os.path.join(d, "big.txt")
    with open(big, "w") as f:
        f.write("\n".join(f"line {i}" for i in range(3000)))
    small = os.path.join(d, "small.txt")
    with open(small, "w") as f:
        f.write("\n".join(f"line {i}" for i in range(50)))
    missing = os.path.join(d, "nope.txt")

    # (a) big file, no offset → nudge
    assert evaluate({"file_path": big}), "a: big full read should nudge"
    # (b) same big file WITH offset → silent
    assert not evaluate({"file_path": big, "offset": 1}), "b: offset should silence"
    assert not evaluate({"file_path": big, "limit": 100}), "b2: limit should silence"
    # (c) small file → silent
    assert not evaluate({"file_path": small}), "c: small file should be silent"
    # (d) missing file → silent
    assert not evaluate({"file_path": missing}), "d: missing file should be silent"
    print("PASS")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        try:
            _selftest()
        except AssertionError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
    else:
        try:
            main()
        except Exception:
            sys.exit(0)  # fail-open
