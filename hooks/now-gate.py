#!/usr/bin/env python3
"""PreToolUse hook — keep `.now.md` tiny so the turn-injector can actually show it.

northstar-inject reads `.now.md` every turn but truncates at 800 chars, so a
`.now.md` that grew to 70 lines (Vividlist did) is 97% invisible — the live NOW
step is buried. This nudges (non-blocking) whenever a Write/Edit to `.now.md`
would leave it >5 non-empty lines or >800 chars. Built by GLM 5.2, reviewed +
docstringed here. Advisory only, fail-open. (Delegated M1.)
"""
import sys
import json
import os


def process_event(event):
    try:
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if os.path.basename(file_path) != ".now.md":
            return ""

        # Determine resulting text: Write carries content; Edit/MultiEdit don't
        # give final text cheaply, so fall back to the current on-disk file.
        if tool_name == "Write":
            text = tool_input.get("content", "")
        else:
            text = tool_input.get("content", "")
            if not text and file_path:
                try:
                    with open(file_path, "r") as f:
                        text = f.read()
                except Exception:
                    text = ""

        non_empty_lines = sum(1 for line in text.splitlines() if line.strip())
        chars = len(text)

        if non_empty_lines > 5 or chars > 800:
            msg = (".now.md is oversized (keep it <=5 lines / <=800 chars: NOW / "
                   "LAST_VERIFIED / NEXT). The turn-injector truncates it at 800 "
                   "chars, so anything beyond is invisible — move detail into "
                   ".planning/STATE.md.")
            return json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": msg
                }
            })
        return ""
    except Exception:
        return ""


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
            oversized = "\n".join([f"line{i}" for i in range(10)])
            r = process_event({"tool_name": "Write",
                               "tool_input": {"file_path": ".now.md", "content": oversized}})
            assert r and " oversized " in json.loads(r)["hookSpecificOutput"]["additionalContext"]
            r = process_event({"tool_name": "Write",
                               "tool_input": {"file_path": ".now.md", "content": "line1\nline2"}})
            assert r == ""
            print("selftest passed")
            return
        data = sys.stdin.read()
        event = json.loads(data) if data else {}
        out = process_event(event)
        if out:
            print(out)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
