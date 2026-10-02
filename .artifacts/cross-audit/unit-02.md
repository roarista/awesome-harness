# Cross-audit U02: production treg client 403 header fix

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 870e8956cc95:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `870e8956cc95300064b0984e6097ba59e54b00ed` (parent `e63221a89e949c70ccbb722f23f955451f8050ed`)
- Builder report (claim): `.artifacts/agent-reports/tg1-fix-403-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff e63221a89e94 870e8956cc95 -- src/production/treg_client.py tests/production/test_treg_client.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 870e8956cc95 -- src/production/treg_client.py tests/production/test_treg_client.py
```

Code stat (unit paths only):
```
src/production/treg_client.py        | 11 ++++++++---
 tests/production/test_treg_client.py | 25 +++++++++++++++++++++++++
 2 files changed, 33 insertions(+), 3 deletions(-)
```

## Unit spec as given to the builder (verbatim, 2026-09-22T23:20:17.480Z)

````text
You are a builder in /Users/rodrigoarista/Downloads/virality-pipeline (use .venv/bin/python). Keep reads scoped; be concise.

CONTEXT: The first real call through `src/production/treg_client.py` (`treg_call`) failed with `ValueError: treg HTTP 403 for reapi.video-gen.seedance-2-5.unrestricted`. The sibling client `src/s1/scrapers/treg_client.py` (lines ~86-96, DO NOT edit it) sends two extra headers because treg's ingress rejects the default urllib User-Agent with 403: `"User-Agent": os.environ.get("TREG_USER_AGENT", "").strip() or DEFAULT_USER_AGENT` and `"ngrok-skip-browser-warning": "1"`. The production client (headers dict near line 44) sends neither. It already imports helpers from the s1 client (`_token`, `_gate_error`, `_idempotency_key`).
CHANGE: In `src/production/treg_client.py` add those two headers, reusing `DEFAULT_USER_AGENT` from the s1 client (import it; do not duplicate the string). Also include the first 300 chars of the error body (decoded, errors="replace") in the non-402/503 ValueError message so the next failure is readable — but never include the token. Add one test in `tests/production/test_treg_client.py` asserting the outgoing request carries the non-default User-Agent and the ngrok header (capture the urllib Request the existing tests' fake urlopen receives; follow the file's existing mocking pattern). Mutation-check it: remove the header, see the test fail by name, restore.
GOAL: treg_call sends the same identifying headers as the working s1 client. File stays ≤200 lines.
VERIFY: `.venv/bin/python -m pytest tests/production -q` all green; `wc -l src/production/treg_client.py`.
Do NOT make any real/paid network call. Do NOT touch any other file, do not git add/commit, never git stash/checkout/reset.
Write the full report to .artifacts/agent-reports/tg1-fix-403-builder.md; return ≤8 lines: verdict, change, test output counts, mutation result, report path.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/production -q
wc -l src/production/treg_client.py
```

## Risk area to weigh
auth headers + token leakage in HTTP error text
