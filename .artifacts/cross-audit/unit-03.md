# Cross-audit U03: Seedance frame-role validation + runner voice step

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 10ccadd5f32e:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `10ccadd5f32e3b9259df86f35598cf11307ee80c` (parent `1c64d3419f9f38fd45845d84f579cc515bb34d8f`)
- Builder report (claim): `.artifacts/agent-reports/sd25-roles-voice-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 1c64d3419f9f 10ccadd5f32e -- scripts/production/steps.py src/production/seedance25.py tests/production/test_seedance25.py tests/production/test_steps_voice_roles.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 10ccadd5f32e -- scripts/production/steps.py src/production/seedance25.py tests/production/test_seedance25.py tests/production/test_steps_voice_roles.py
```

Code stat (unit paths only):
```
scripts/production/steps.py                |  60 ++++++++++---
 src/production/seedance25.py               |   3 +
 tests/production/test_seedance25.py        |   8 +-
 tests/production/test_steps_voice_roles.py | 131 +++++++++++++++++++++++++++++
 4 files changed, 191 insertions(+), 11 deletions(-)
```

## Unit spec as given to the builder (verbatim, 2026-09-23T00:21:40.339Z)

````text
You are a builder in /Users/rodrigoarista/Downloads/virality-pipeline (use .venv/bin/python). Keep reads scoped; be concise. Probe processes may be running `scripts/production/run_test.py` right now — do not run it with `--yes`, and do not touch `state/`.

Two small units, do them in order, each with tests. Hard cap: every touched source file ≤200 lines (check with wc -l). Never git add/commit/stash/checkout/reset. No real/paid network calls (mock the boundary in tests).

UNIT 1 — `src/production/seedance25.py` `build_body`: reAPI rejects (HTTP 400, code 20003) `image_with_roles` that mixes first_frame/last_frame with reference_image ("they are separate task types; send reference images in image_urls instead"). Add a pure `_req` check raising ValueError with that explanation before any call. Test in tests/production/test_seedance25.py (mutation-check: delete the check, test fails by name, restore).

UNIT 2 — `scripts/production/steps.py` (runner step kinds; read it and `scripts/production/run_test.py` first):
 (a) seedance step: an image entry without a "role" key means the plain `image_urls` mode (ordered list, no roles). All-with-role → image_with_roles (today's behaviour); mixing role/no-role in one step → ValueError at validate(). `build_body` already accepts `image_urls=`.
 (b) new kind `voice`: calls `src/common/fish_audio.synthesize(text, voice_id, model, out_path)` (read its skeleton/signature and how `src/video_v2/tts/synthesize.py` picks voice_id/model/defaults; reuse those defaults, env-overridable, no hard-coded names of people). Spec fields: `text` (required), optional `voice_id`, `model`, `out` (e.g. voice.mp3). Gate + record the cost like the `nano` branch does (check_budget before, costs.record after the call with explicit_usd from a small per-character list price constant marked price_confirmed=False; find Fish's price in the repo if it exists — rg "fish" in src/spine/costs.py — else use 15 USD per 1M chars and say so in a comment). If the call returns but the file is missing, record then raise. estimate() must return this cost for dry runs. A later seedance step already can reference the file via "audio": ["voice.mp3"].
 If steps.py would pass 200 lines, move the voice branch into a new `scripts/production/voice_step.py`.
 Tests in tests/production/test_steps.py (or a new test file) with fish_audio mocked; mutation-check one.

VERIFY: `.venv/bin/python -m pytest tests/production -q` all green; `.venv/bin/ruff check` on touched files; wc -l.
Write the full report to .artifacts/agent-reports/sd25-roles-voice-builder.md; return ≤8 lines: verdict, changes per unit, test counts, mutation results, line counts, report path.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/production -q
.venv/bin/ruff check <touched files>
wc -l <touched files>
```

## Risk area to weigh
money (paid voice: budget gate before, ledger after, re-run double charge) + request validation
