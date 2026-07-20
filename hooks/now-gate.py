#!/usr/bin/env python3
"""PreToolUse hook — keep `.now.md` tiny so the turn-injector can actually show it.

northstar-inject reads `.now.md` every turn but truncates at 800 chars, so a
`.now.md` that grew to 70 lines (Vividlist did) is 97% invisible — the live NOW
step is buried. For a Write to `.now.md` (where the resulting content is fully
known via tool_input.content) an oversized result now BLOCKS (exit 2, DENY) so
the bloat never lands. For Edit/MultiEdit the post-edit content isn't knowable
cheaply, so that case stays advisory. Built by GLM 5.2, reviewed + docstringed
here. Kill-switch NOW_GATE=0. Fail-open. (Delegated M1.)
"""
import sys
import json
import os

# process_event sentinels
BLOCK = "block"     # (BLOCK, reason)   -> Write oversized, DENY via exit 2
ADVISE = "advise"   # (ADVISE, json)    -> Edit/MultiEdit advisory additionalContext
NONE = "none"       # (NONE, "")        -> silent / pass


def process_event(event):
    try:
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if os.path.basename(file_path) != ".now.md":
            return (NONE, "")

        msg = (".now.md oversized keep <=5 lines/<=800 chars: NOW/LAST_VERIFIED/NEXT. "
               "injector truncates at 800, rest invisible. move detail -> .planning/STATE.md.")

        # Write carries the full resulting content -> we can KNOW it's oversized
        # and DENY. Edit/MultiEdit don't give final text cheaply -> advisory only,
        # never block on unknown content.
        if tool_name == "Write":
            text = tool_input.get("content", "")
            non_empty_lines = sum(1 for line in text.splitlines() if line.strip())
            if non_empty_lines > 5 or len(text) > 800:
                return (BLOCK, msg)
            return (NONE, "")

        # Edit / MultiEdit: fall back to current on-disk file, advise only.
        text = tool_input.get("content", "")
        if not text and file_path:
            try:
                with open(file_path, "r") as f:
                    text = f.read()
            except Exception:
                text = ""
        non_empty_lines = sum(1 for line in text.splitlines() if line.strip())
        if non_empty_lines > 5 or len(text) > 800:
            return (ADVISE, json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": msg
                }
            }))
        return (NONE, "")
    except Exception:
        return (NONE, "")


def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
            oversized = "\n".join([f"line{i}" for i in range(10)])
            action, payload = process_event({"tool_name": "Write",
                               "tool_input": {"file_path": ".now.md", "content": oversized}})
            assert action == BLOCK and "oversized" in payload, "oversized Write must BLOCK"
            action, payload = process_event({"tool_name": "Write",
                               "tool_input": {"file_path": ".now.md", "content": "line1\nline2"}})
            assert action == NONE, "small Write must pass"
            action, payload = process_event({"tool_name": "Edit",
                               "tool_input": {"file_path": ".now.md", "content": oversized}})
            assert action == ADVISE, "oversized Edit must advise (never block on unknown)"
            print("selftest passed")
            return
        if os.environ.get("NOW_GATE") == "0":
            sys.exit(0)
        data = sys.stdin.read()
        event = json.loads(data) if data else {}
        action, payload = process_event(event)
        if action == BLOCK:
            sys.stderr.write(payload + "\n")
            sys.exit(2)
        if action == ADVISE and payload:
            print(payload)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
