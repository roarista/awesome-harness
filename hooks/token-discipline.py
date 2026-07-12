"""PostToolUse(Read) — warn on the 3rd FULL re-read of the same file.

Trimmed per the council: a read with offset/limit is navigation (jumping to a
part of a big file) and is EXEMPT. Only a rangeless full re-read counts as churn
— re-slurping a whole file you already have. Fires once per file per session. If
that file is also large, the message says so (the narrowed oversize warning).

Warn only, never blocks. Fail-open, state per-session self-prunes.
"""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

REREAD_N = 3
BIG = 20000       # chars; a full read this large that's being repeated = expensive
STATE_DIR = Path.home() / ".claude" / "hooks" / "state" / "tokendisc"
TTL = 2 * 86400


def _emit(msg: str) -> None:
    _hookout.inject("PostToolUse", msg)


def _path(session: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session)[:80]
    return STATE_DIR / f"{safe or 'nosession'}.json"


def _resp_len(resp) -> int:
    try:
        if isinstance(resp, dict):
            c = resp.get("content", resp)
            return len(c if isinstance(c, str) else json.dumps(c))
        return len(resp if isinstance(resp, str) else json.dumps(resp))
    except Exception:
        return 0


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name") != "Read":
        return
    ti = data.get("tool_input", {}) or {}
    fp = str(ti.get("file_path", "") or "")
    if not fp:
        return
    if ti.get("offset") is not None or ti.get("limit") is not None:
        return  # targeted/navigation read — exempt

    session = str(data.get("session_id", "") or "")
    p = _path(session)
    try:
        st = json.loads(p.read_text())
    except Exception:
        st = {"counts": {}, "warned": []}
    counts, warned = st.get("counts", {}), set(st.get("warned", []))

    counts[fp] = counts.get(fp, 0) + 1
    st["counts"] = counts

    if counts[fp] >= REREAD_N and fp not in warned:
        warned.add(fp)
        big = _resp_len(data.get("tool_response", data.get("tool_result", {}))) >= BIG
        extra = (" It's a large file — read only the slice you need." if big else "")
        _emit(
            f"You've fully re-read {fp} {counts[fp]}× this session. If it's "
            "unchanged you already have it in context; if you need a specific "
            f"part, Read with offset/limit instead of the whole file.{extra}")
    st["warned"] = sorted(warned)

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st))
        now = time.time()
        for f in STATE_DIR.glob("*.json"):
            if now - f.stat().st_mtime > TTL:
                f.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
