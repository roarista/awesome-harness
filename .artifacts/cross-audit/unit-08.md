# Cross-audit U08: S1 treg client: HTTP 503 no longer treated as spend gate

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 43b457dd90a9:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `43b457dd90a9d073bf00dc1f84c8445fbfdca002` (parent `2bb91b3804e69cbf188d28c9a08c425315807915`)
- Builder report (claim): `.artifacts/agent-reports/treg-503-fix-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 2bb91b3804e6 43b457dd90a9 -- src/s1/scrapers/treg_client.py tests/s1/test_treg_client.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 43b457dd90a9 -- src/s1/scrapers/treg_client.py tests/s1/test_treg_client.py
```

Code stat (unit paths only):
```
src/s1/scrapers/treg_client.py | 23 +++++++++++++++++++++--
 tests/s1/test_treg_client.py   | 22 ++++++++++++++++++++++
 2 files changed, 43 insertions(+), 2 deletions(-)
```

## Unit spec as given to the builder (verbatim, 2026-09-24T15:18:29.219Z)

````text
You are the BUILDER for a small FIX unit in /Users/rodrigoarista/Downloads/virality-pipeline (branch codex-procedure-parity; huge shared dirty checkout — never whole-repo `git status`/`git diff`; explicit paths only).

Bug (reproduced live today, paid run R1 pilot, log `/Users/rodrigoarista/.claude/jobs/d98073eb/tmp/r1_pilot.log`): `src/s1/scrapers/treg_client.py:111-112` maps every HTTP 402 and 503 to `costs.CostGateError`. treg returned 503 with body `{"error": "We couldn't get valid results for this search. Please try again later."}` — an upstream (SerpApi) transient failure, not a spend gate. CostGateError is designed to stop the whole run (never caught), so one flaky search killed the pilot for both creators instead of failing that creator and retrying next run.

CHANGE: a 503 is a spend gate only when the body shows it is treg's own gate (e.g. has `resets_at`, or an error text about budget/limit/quota/credits/balance — read `_gate_error` and any treg docs/tests in the repo to find the real gate shape; `ml search treg` may help); otherwise raise `ValueError` (the retryable provider failure the callers already catch: see `src/s1/audience/ai_mode_fu_chat.py:34` `_ERRORS`, `ai_mode_fetch.py:123`). 402 stays a gate. Find the existing treg client tests (rg `treg_client` in tests/) and add one test: 503 with the upstream body → ValueError; 503 with a gate body (resets_at) → CostGateError. Mutation-proof it. Also check all callers of treg_get (rg) still behave: a ValueError from a follow-up turn must NOT be cached as success.

Rules: only `src/s1/scrapers/treg_client.py` + its test file. ≤200 lines (report current size). No network/paid calls. Never git add/commit/stash/checkout/reset/clean/rm. Never read .env or print keys/tokens. Don't touch .now.md, STATE.md, .mulch, src/s1/comment_bait.py, src/s1/comments.py. Hook blocks shell writes under src/ → Edit/Write. `.venv/bin/python`; run the treg tests + `tests/s1 -k "ai_mode"` + ruff.

Write the report to `.artifacts/agent-reports/treg-503-fix-builder.md`. Return ≤6 lines: verdict, change, tests/mutation, callers, risks, report path.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest -q tests/s1/test_treg_client.py
.venv/bin/python -m pytest -q tests/s1 -k ai_mode
.venv/bin/ruff check src/s1/scrapers/treg_client.py tests/s1/test_treg_client.py
(builder spec gives no explicit VERIFY line; these are the tests it names)
```

## Risk area to weigh
retries + money (spend gate must still stop spending)
