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
import re

# process_event sentinels
BLOCK = "block"     # (BLOCK, reason)   -> Write oversized, DENY via exit 2
ADVISE = "advise"   # (ADVISE, json)    -> Edit/MultiEdit advisory additionalContext
NONE = "none"       # (NONE, "")        -> silent / pass

SLOT_HEADER = re.compile(r'^## \[(.+?)\]\s*$')


def _lines_chars(text):
    non_empty = sum(1 for line in text.splitlines() if line.strip())
    return non_empty, len(text)


def _split_slots(text):
    """Same shape as northstar-inject.parse_now: (preamble, {label: body}, order).
    No `## [` headers -> ({}, []) signals flat legacy file (caller checks by
    order being empty)."""
    if "## [" not in text:
        return "", {}, []
    lines = text.splitlines()
    preamble_lines, slots, order = [], {}, []
    cur, cur_lines = None, []
    for ln in lines:
        m = SLOT_HEADER.match(ln)
        if m:
            if cur is not None:
                slots[cur] = "\n".join(cur_lines)
            cur = m.group(1)
            order.append(cur)
            cur_lines = []
        elif cur is None:
            preamble_lines.append(ln)
        else:
            cur_lines.append(ln)
    if cur is not None:
        slots[cur] = "\n".join(cur_lines)
    return "\n".join(preamble_lines), slots, order


def _check_now_text(text):
    """Returns "" if OK, else a violation message naming the offending block."""
    preamble, slots, order = _split_slots(text)
    if not order:
        # flat legacy file — unchanged behavior: whole file capped at 5/800
        n, c = _lines_chars(text)
        if n > 5 or c > 800:
            return (".now.md oversized keep <=5 lines/<=800 chars: NOW/LAST_VERIFIED/NEXT. "
                    "injector truncates at 800, rest invisible. move detail -> .planning/STATE.md.")
        return ""
    pn, pc = _lines_chars(preamble)
    if pn > 3 or pc > 800:
        return (".now.md shared preamble oversized (keep <=3 lines). "
                "move detail -> .planning/STATE.md.")
    for label in order:
        n, c = _lines_chars(slots.get(label, ""))
        if n > 5 or c > 800:
            return (f".now.md slot [{label}] oversized keep <=5 lines/<=800 chars: "
                     "NOW/LAST_VERIFIED/NEXT. injector truncates at 800, rest invisible. "
                     "move detail -> .planning/STATE.md.")
    return ""


def process_event(event):
    try:
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if os.path.basename(file_path) != ".now.md":
            return (NONE, "")

        # Write carries the full resulting content -> we can KNOW it's oversized
        # and DENY. Edit/MultiEdit don't give final text cheaply -> advisory only,
        # never block on unknown content.
        if tool_name == "Write":
            text = tool_input.get("content", "")
            msg = _check_now_text(text)
            if msg:
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
        msg = _check_now_text(text)
        if msg:
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
