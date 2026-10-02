# Cross-audit U06: S1 audience handoff hang fix (privacy cleaners regex)

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show e39c17243590:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `e39c17243590dac5a21f16b4f38ce2261e5af7ea` (parent `72ea8a8c4537b1be5996561957c3ce1e8d3577f0`)
- Builder report (claim): `.artifacts/agent-reports/handoff-hang-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 72ea8a8c4537 e39c17243590 -- src/s1/person_synthesis/signals/handle_gate.py src/s1/person_synthesis/signals/humor_usage.py src/s1/person_synthesis/signals/model_call.py tests/s1/test_handoff_perf.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= e39c17243590 -- src/s1/person_synthesis/signals/handle_gate.py src/s1/person_synthesis/signals/humor_usage.py src/s1/person_synthesis/signals/model_call.py tests/s1/test_handoff_perf.py
```

Code stat (unit paths only):
```
src/s1/person_synthesis/signals/handle_gate.py |  42 ++++++++++
 src/s1/person_synthesis/signals/humor_usage.py |  28 ++++---
 src/s1/person_synthesis/signals/model_call.py  |  14 +++-
 tests/s1/test_handoff_perf.py                  | 103 +++++++++++++++++++++++++
 4 files changed, 173 insertions(+), 14 deletions(-)
```

## Unit spec as given to the builder (verbatim, 2026-09-23T18:47:21.643Z)

````text
You are the BUILDER for one unit in /Users/rodrigoarista/Downloads/virality-pipeline (use .venv/bin/python). Keep reads scoped, be concise. Write your full report to .artifacts/agent-reports/handoff-hang-builder.md and return <=8 lines (verdict, root cause, change, verification, risk, next) + report path.

HARD RULES: no git commands that change anything (no add/commit/stash/checkout/reset/restore/clean). Another builder is concurrently editing src/s1/audience/matrix*.py and tests/s1/test_matrix.py — do not touch those. You may edit src/s1/audience/handoff.py, handoff_adapt.py, handoff_voice.py and add a NEW test file tests/s1/test_handoff_perf.py. tests/s1/test_audience_handoff.py has uncommitted hunks from another terminal — do NOT edit it. Do NOT touch src/s1/person_synthesis/signals/question_ledger.py or collect.py. Every source file <=200 lines. No paid/API calls: if the handoff path calls an LLM, run with a fake/stub or confirm it doesn't. Never pkill; if you start a process, kill only its own PID. Never delete/overwrite .artifacts/person_synthesis/personas/intrn_handoff.json content produced by others (it currently does not exist); write any trial output to $CLAUDE_JOB_DIR/tmp or a tmp dir, not the real path.

CONTEXT: `PIPELINE_STATE_DIR=state/run2 PIPELINE_RUN_TAG=audience_creators_2026_09_21 .venv/bin/python -B -m src.s1.audience.handoff --brand intrn --run-tag audience_creators_2026_09_21` ran 88 min at ~98% CPU in pure Python, no API calls, wrote nothing, and was killed. Inputs: 19 fichas at .artifacts/person_synthesis/creators/<handle>.json (+ <handle>.comments.json), state/run2/s1/intrn/audience/{groups.json (19 singleton groups), matrix.json, merged_signals.json, comment_notes.jsonl (10,561 notes)}, and the sqlite DB used by the pipeline (read-only for you). Suspect a quadratic/exponential loop (e.g. per-comment x per-comment matching, repeated JSON parsing, regex over all comments per item, or the voice/evidence dedup).

TASK: reproduce with a hard wall-clock limit (run it in background with a PID you own, sample it with `py-spy dump --pid` if installed, or run under cProfile/faulthandler.dump_traceback_later with output redirected to a tmp dir and stop after ~2-3 min). Identify the exact hot loop (file:line), explain the complexity with real sizes, fix it with the minimum change that preserves output semantics (same keys/values for the same input), and prove: (1) the real handoff completes on the real inputs in seconds/minutes, writing to a tmp path (pass an out path/flag if one exists; if none, monkeypatch in a tiny driver script in $CLAUDE_JOB_DIR/tmp rather than adding CLI surface); (2) a new test in tests/s1/test_handoff_perf.py that scales inputs so the old code would take obviously long (e.g. >10x slower) and asserts a time bound or asserts the call count — mutation-check it against the old loop. Report the output file's cluster count and top-level keys.

VERIFY: `.venv/bin/python -m pytest -q tests/s1/test_audience_handoff.py tests/s1/test_handoff_perf.py` green; ruff on touched files; wc -l touched sources <=200.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest -q tests/s1/test_audience_handoff.py tests/s1/test_handoff_perf.py
.venv/bin/ruff check <touched files>
wc -l <touched sources>   # each <=200
```

## Risk area to weigh
privacy redaction correctness (regex/parsing of handles) + performance
