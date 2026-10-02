# Cross-audit U10: D2 YouTube transcript disk cache

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 0155914771d4:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `0155914771d4e121cfce42ea205feba96e40331d` (parent `3049167b14a5001b0d8372542da3c79def8ad756`)
- Builder report (claim): `.artifacts/agent-reports/d2-transcript-cache-builder.md (uncommitted, in working tree)`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 3049167b14a5 0155914771d4 -- src/s1/youtube/_transcripts.py src/s1/youtube/gate.py tests/s1/test_youtube_gate_transcripts.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 0155914771d4 -- src/s1/youtube/_transcripts.py src/s1/youtube/gate.py tests/s1/test_youtube_gate_transcripts.py
```

Code stat (unit paths only):
```
src/s1/youtube/_transcripts.py            | 65 ++++++++++++++++++++
 src/s1/youtube/gate.py                    | 31 +++-------
 tests/s1/test_youtube_gate_transcripts.py | 98 ++++++++++++++++++++++++++++++-
 3 files changed, 169 insertions(+), 25 deletions(-)
```

Note: This commit also touches `.planning/CHANGE_LEDGER.md` (one line); not part of the code under audit.

## Unit spec as given to the builder (verbatim, 2026-10-01T05:11:07.432Z)

````text
Build ONE unit with codex exec, model gpt-5.6-luna (D-024 plan models only), reasoning effort medium, `-c multi_agent=false`, workspace-write sandbox, cwd /Users/rodrigoarista/Downloads/virality-pipeline. Pass the full content of /Users/rodrigoarista/.claude/jobs/b1947e1e/tmp/d2-spec.md to codex as the task. Hard rules: no git add/commit/stash/reset/checkout; never read .env; touch only src/s1/youtube/gate.py, optional src/s1/youtube/_transcripts.py, tests/s1/test_youtube_gate_transcripts.py; do not call ytintel for real (YouTube is rate-limiting this IP). Confirm changed files with `git status --short src/s1 tests/s1`. Report to .artifacts/agent-reports/d2-transcript-cache-builder.md; return ≤8 lines.
````

### Referenced spec file: /Users/rodrigoarista/.claude/jobs/b1947e1e/tmp/d2-spec.md

````text
# Unit D2 — YouTube transcripts are saved and never refetched (Terminal CIERRE)
Repo /Users/rodrigoarista/Downloads/virality-pipeline. Use .venv/bin/python.
## CONTEXT
src/s1/youtube/gate.py `ytintel_transcripts` fetches transcripts with `~/.local/bin/ytintel transcript -- <id>` and keeps them
only in memory. A free check fetched 58 transcripts, then the real judge run minutes later got 0: YouTube now answers
HTTP 429 / IpBlocked for this IP (ytintel prints "RATE_LIMITED: ..." and still exits 0 with no transcript on stdout — check
how it reports; a RATE_LIMITED line must never be stored as a transcript). Ro: save everything at every stage.
## CHANGE
1. Cache per video: `paths.s1_root(brand)/youtube/transcripts/<video_id>.txt` (atomic write, only non-empty real text).
   `ytintel_transcripts` reads the cache first and calls ytintel only for missing ids; it gets the cache dir as a parameter
   (gate.run passes it). Failures are NOT cached (a 429 retries next run).
2. If ytintel output says RATE_LIMITED / IpBlocked, stop calling ytintel for the rest of this run (no hammering); the
   channels without cached text go to pending_no_transcript.json as today.
3. Tests (extend tests/s1/test_youtube_gate_transcripts.py, ≤200 lines): cached id -> runner not called; fetched text is
   written; RATE_LIMITED output -> not cached and later ids not attempted. Mutation-check.
## DO NOT
Touch other files (keep gate.py ≤200 lines; if needed move the transcript helpers to new src/s1/youtube/_transcripts.py);
no git add/commit/stash/reset/checkout; never read .env; no network in tests; plan models only.
## VERIFY
pytest tests/s1 -q -k youtube; ruff; wc -l. Report .artifacts/agent-reports/d2-transcript-cache-builder.md; return ≤8 lines.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/s1 -q -k youtube
.venv/bin/ruff check src/s1/youtube tests/s1/test_youtube_gate_transcripts.py
wc -l src/s1/youtube/gate.py src/s1/youtube/_transcripts.py tests/s1/test_youtube_gate_transcripts.py
```

## Risk area to weigh
file I/O cache (atomic write, path safety from video id) + rate-limit handling (never cache failures)
