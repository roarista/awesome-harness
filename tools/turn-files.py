#!/usr/bin/env python3
"""Print de-duplicated absolute files from phantom-edit.jsonl."""
import argparse
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

LOG = Path.home() / ".claude" / "hooks" / "state" / "phantom-edit.jsonl"


def touched_files(session: str = "", since: float = 1440) -> list[str]:
    """Read the edit log fail-open, retaining matching absolute paths in log order."""
    try:
        cutoff = datetime.now() - timedelta(minutes=since)
        seen, paths = set(), []
        for line in LOG.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    continue
                when = datetime.fromisoformat(event.get("ts", ""))
            except (ValueError, TypeError):
                continue
            transcript = event.get("tp", "")
            path = event.get("file", "")
            if when < cutoff or (session and transcript != session and session not in transcript):
                continue
            if not Path(path).is_absolute() or path in seen:
                continue
            seen.add(path)
            paths.append(path)
        return paths
    except OSError:
        return []


def _selftest() -> int:
    global LOG
    original = LOG
    try:
        with tempfile.TemporaryDirectory() as tmp:
            LOG = Path(tmp) / "phantom-edit.jsonl"
            now = datetime.now().isoformat(timespec="seconds")
            LOG.write_text("\n".join((
                "null",
                json.dumps({"ts": now, "file": "/x/a.py", "tp": "/p/one.jsonl"}),
                json.dumps({"ts": now, "file": "/x/a.py", "tp": "/p/one.jsonl"}),
                json.dumps({"ts": now, "file": "/x/b.py", "tp": "/p/two.jsonl"}),
                json.dumps({"ts": now, "file": "relative.py", "tp": "/p/one.jsonl"}),
            )) + "\n")
            got = touched_files("one", 1)
            ok = got == ["/x/a.py"]
            print(f"null + session -> {got} (want ['/x/a.py'])")
            LOG = Path(tmp) / "missing.jsonl"
            empty = touched_files(since=1)
            ok &= empty == []
            print(f"missing -> {empty} (want [])")
            print("PASS" if ok else "FAIL")
            return 0 if ok else 1
    finally:
        LOG = original


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="", help="session id or transcript path")
    parser.add_argument("--since", type=float, default=1440, help="minutes (default: 1440)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.since < 0:
        parser.error("--since must be nonnegative")
    if args.selftest:
        return _selftest()
    print("\n".join(touched_files(args.session, args.since)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
