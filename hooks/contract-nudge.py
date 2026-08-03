#!/usr/bin/env python3
"""PreToolUse(Task|Agent) — enforce the subagent RETURN CONTRACT at the only point
that has leverage: the SPAWN, not the return. Measured 2026-08-02: median subagent
return is 3,448 chars / 24 lines, 64.3% exceed a 15-line contract, p90 98 lines,
max 48,703 chars, and the parent reuses ~2.49% of it verbatim — a PostToolUse hook
fires only after the bloat is already in the transcript, so it cannot shrink
anything. This hook inspects the OUTGOING prompt/description and, if it does not
already state a return contract, injects ONE short line requiring one
(verdict/headline/evidence/next/risks, max 8 lines).

Cost rule: 0 bytes when the prompt already carries a contract. The generic nudge
fires at most ONCE per session (hooks/_hookout.once) — a chatty hook is a
regression after the 2026-08-02 cut from 30.2 -> 8.5 ktok/session.
Kill-switch: CONTRACT_NUDGE=off. Fail-open on any error.
"""
import json
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import _hookout

# Any of these already-present signals count as "states a return contract":
# an explicit line budget, or >=2 of the named fields (verdict/headline/summary/
# evidence/findings/next/risks/status/etc), or a literal "RETURN"/"return format"
# heading — matches the shape every unit-spec / audit prompt in this repo already uses.
LINE_BUDGET_RE = re.compile(r"\b(max|at most|no more than|<=|exactly)\s*\d+\s*lines\b", re.I)
CONTRACT_HEADING_RE = re.compile(r"\b(return contract|return format|return exactly|RETURN:)\b", re.I)
FIELD_RE = re.compile(
    r"\b(verdict|headline|status|summary|evidence|findings|risks?|next|"
    r"deviations|files?|diffstat|verify)\s*:", re.I)

NUDGE = (
    "RETURN CONTRACT: end this spawn's prompt with an explicit short return "
    "shape (e.g. verdict/headline/evidence/next/risks), max 8 lines — the parent "
    "reuses ~2.5% of an unstructured return verbatim, the rest is wasted tokens."
)


def states_contract(text: str) -> bool:
    if not text:
        return False
    if LINE_BUDGET_RE.search(text) or CONTRACT_HEADING_RE.search(text):
        return True
    return len(FIELD_RE.findall(text)) >= 2


def main():
    if os.environ.get("CONTRACT_NUDGE", "").strip().lower() == "off":
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    ti = data.get("tool_input", {}) or {}
    text = f"{ti.get('prompt', '') or ''}\n{ti.get('description', '') or ''}"
    if states_contract(text):
        return  # 0 bytes — already compliant
    if not _hookout.once("contract-nudge", _hookout.sid_of(data)):
        return  # already nudged once this session
    _hookout.inject("PreToolUse", NUDGE)


def _selftest():
    assert states_contract("VERIFY: run tests\nBUILT-BY: codex\nRETURN exactly 8 lines")
    assert states_contract("respond with verdict: ... and next: ...")
    assert states_contract("max 8 lines, headline + evidence")
    assert not states_contract("go build the retry loop and tell me when done")
    assert not states_contract("")
    print("PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        _selftest()
        sys.exit(0)
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open
