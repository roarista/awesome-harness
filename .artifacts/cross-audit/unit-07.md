# Cross-audit U07: R1 Google AI Mode research stage per creator

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 396e9f1e9d66:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `396e9f1e9d66caca380a136e7495e638a43ac702` (parent `51b64aae031039292fbbd11a292e826ec1485c0a`)
- Builder report (claim): `.artifacts/agent-reports/r1-ai-mode-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 51b64aae0310 396e9f1e9d66 -- src/s1/audience/ai_mode.py src/s1/audience/ai_mode_fetch.py src/s1/scrapers/treg_client.py tests/s1/test_ai_mode_stage.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 396e9f1e9d66 -- src/s1/audience/ai_mode.py src/s1/audience/ai_mode_fetch.py src/s1/scrapers/treg_client.py tests/s1/test_ai_mode_stage.py
```

Code stat (unit paths only):
```
src/s1/audience/ai_mode.py       | 158 +++++++++++++++++++++++++++++++++++++++
 src/s1/audience/ai_mode_fetch.py |  80 ++++++++++++++++++++
 src/s1/scrapers/treg_client.py   |  25 ++++---
 tests/s1/test_ai_mode_stage.py   | 109 +++++++++++++++++++++++++++
 4 files changed, 363 insertions(+), 9 deletions(-)
```

## Unit spec as given to the builder (verbatim, 2026-09-23T21:03:00.415Z)

````text
You are the BUILDER for unit R1 in /Users/rodrigoarista/Downloads/virality-pipeline (.venv/bin/python). Keep reads scoped, be concise. Full report → .artifacts/agent-reports/r1-ai-mode-builder.md; return <=8 lines (verdict, change, verification, cost, risk, next) + report path.

HARD RULES: no git that changes anything (no add/commit/stash/checkout/reset/restore/clean). Another builder is editing src/s1/audience/handoff*.py concurrently — don't touch those. Don't touch src/s1/person_synthesis/signals/question_ledger.py or collect.py, or src/dissection/* files other terminals own unless strictly needed (prefer importing). Every source file <=200 lines. Never print tokens/keys. Never pkill.

GOAL (Ro, 23-sep): Google AI Mode research about each creator must be a PIPELINE STAGE that always runs for every creator of the brand before fichas/conclusions — not a manual Chrome step. Today 0 of the 19 intrn creators have a file; the ficha loader reads `$PIPELINE_STATE_DIR/research/creator_audience/tiktok_<handle>.json` (see src/s1/audience/ficha.py:76-81 load_creator `ai_mode`, and ficha_fields._ai reading `ai_mode.audience.{age_range,gender_skew,geo}`).

REUSE: the manual flow = prose .md files (+ `.daily.md`, `.script.md` siblings) converted by scripts/research/ai_mode_to_audience.py → src/dissection/creator_audience_ai.py (audience_record / write_audience, LLM extraction). Find the exact prompts/questions the Chrome flow asked Google (look in scripts/research/creator_audience_probe*.py, src/dissection/creator_audience.py, creator_lookup.py, and existing prose .md files under state/research/creator_audience or similar) and reuse them verbatim. Provider: treg endpoint `cloro.google.serp.ai_mode` (POST /v1/monitor/aimode, body {"prompt": "...", "gl": "US", "include": {"markdown": true}}; 0.0024 USD/call, 99.8% ok, p50 11 s); fallback sibling `dataforseo.x.serp-google-ai-mode-live-advanced` (0.004). Reuse the repo's existing treg client (src/s1/scrapers/treg_client.py — check how it authenticates; the token lives at ~/.claude/jobs/d98073eb/tmp/treg_token and/or env; follow whatever the client already does) and the cost ledger/budget gate in src/spine/costs.py (record real USD per call under PIPELINE_RUN_TAG; check budget before each call, same pattern as src/s1/post_graph/gemini_video.py). The LLM extraction step must use the text backend that call_text already routes (VIRALITY_TEXT_BACKEND=gemini works).

CHANGE: new module (e.g. src/s1/audience/ai_mode.py, <=200 lines, split if needed) with `run(brand, *, workers=...)`: list the brand's creator handles the same way ficha.run does (s1_posts DISTINCT handle), and for each handle WITHOUT a valid existing record (idempotent/resumable; a failed/empty provider answer is never cached as success) fetch the AI Mode answers, write the prose files where ai_mode_to_audience expects them, and write the audience JSON at the exact path ficha reads. Parallel with the repo's `map_gated` (src/s1/audience/_pool.py), stop on CostGateError. Add a `__main__`/CLI `--brand`. Wire it into the audience stage sequence wherever the stages are orchestrated (grep for how comment_notes/comment_categories/ficha are invoked from a runner/CLI/pipeline; if there is no orchestrator, document the order in the module docstring and in the command list in .artifacts/agent-reports/audience-parallel-voice-builder.md is NOT yours to edit — just report it).

TESTS: tests/s1/test_ai_mode_stage.py with a fake provider: writes to the path ficha.load_creator reads (use the real load_creator to prove it, not a hand-planted path); idempotent second run makes 0 calls; provider failure writes nothing and is retried next run; CostGateError stops the pool. Mutation-check one test.

LIVE PROOF (authorized by Ro, cap 0.05 USD for this proof): run for ONE real intrn creator with env PIPELINE_STATE_DIR=state/run2 PIPELINE_RUN_TAG=audience_creators_2026_09_21 AUDIENCE_ROUND_CAP_USD=9.7 VIRALITY_TEXT_BACKEND=gemini; show the resulting JSON fields (age_range/gender_skew/geo/interests/confidence) in the report and confirm ficha.load_creator(...)['ai_mode'] is non-empty for that handle. Do NOT run all 19 — the orchestrator will after audit.

VERIFY: pytest the new test + tests/s1/test_ficha.py; ruff; wc -l.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest -q tests/s1/test_ai_mode_stage.py tests/s1/test_ficha.py
.venv/bin/ruff check <touched files>
wc -l <touched files>
```

## Risk area to weigh
money (budget gate, cost recording, retries) + cache persistence (failures never cached as success) + response parsing
