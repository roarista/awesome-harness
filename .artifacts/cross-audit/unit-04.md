# Cross-audit U04: runner: Seedance video refs, ElevenLabs voice, phone finish

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show c2fd802ade0d:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `c2fd802ade0d5afea884ed4ac6302f3e65470a4f` (parent `e307af5a386f391f6732adf9a074ba93adffa90b`)
- Builder report (claim): `.artifacts/agent-reports/runner-video-elevenlabs-finish-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff e307af5a386f c2fd802ade0d -- scripts/production/phone_finish.py scripts/production/steps.py scripts/production/steps_extra.py src/production/seedance25.py tests/production/test_steps_extra.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= c2fd802ade0d -- scripts/production/phone_finish.py scripts/production/steps.py scripts/production/steps_extra.py src/production/seedance25.py tests/production/test_steps_extra.py
```

Code stat (unit paths only):
```
scripts/production/phone_finish.py   |  74 +++++++++++++
 scripts/production/steps.py          |  36 +++++--
 scripts/production/steps_extra.py    | 122 +++++++++++++++++++++
 src/production/seedance25.py         |  11 +-
 tests/production/test_steps_extra.py | 199 +++++++++++++++++++++++++++++++++++
 5 files changed, 431 insertions(+), 11 deletions(-)
```

Note: This commit also adds three research notes (`.artifacts/agent-reports/research3-*.md`) from a parallel task; they are not part of the unit.

## Unit spec as given to the builder (verbatim, 2026-09-23T02:12:50.637Z)

````text
You are a builder in /Users/rodrigoarista/Downloads/virality-pipeline (use .venv/bin/python). Keep reads scoped; be concise. Never git add/commit/stash/checkout/reset. No real/paid network calls (mock boundaries in tests). Hard cap: every touched or new source file ≤200 lines (steps.py is already 149 — put new logic in a NEW module, e.g. scripts/production/steps_extra.py, with only small hooks in steps.py). Read scripts/production/steps.py and run_test.py first; mirror their gate/record patterns (the `nano`/`voice` branches: costs check_budget before a paid call, costs.record right after, record-then-raise if the output file is missing).

Three units, in order, each with tests (mutation-check one assertion per unit: break it, see the test fail by name, restore):

UNIT A — seedance step `videos` field: a list of {"path": ...} (local files, hosted with the same `sd.hosted` as images) sent as `video_urls` in the body. Extend `src/production/seedance25.build_body` with `video_urls: list[str] | None` (validate ≤10 videos; mutually allowed with images/image_urls; NOT allowed together with first_frame/last_frame roles — reject with a clear ValueError, since reAPI treats frame tasks separately). Dry-run estimate: reAPI bills reference seconds + output seconds, so add optional per-video `seconds` in the spec and include them in estimate (estimate_usd(duration + sum(seconds), res)).

UNIT B — `voice` step `provider: "elevenlabs"` (default stays fish): call ElevenLabs text-to-speech directly with stdlib urllib: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128, header `xi-api-key` from env ELEVENLABS_API_KEY (never log it), JSON {"text", "model_id" (default "eleven_v3"), "voice_settings": {"stability": step.get("stability", 0.5)}}; write bytes to `out` (default voice.mp3 for elevenlabs) via .part + os.replace. voice_id from step or env ELEVENLABS_VOICE_ID; if neither, fail before paying. Cost: explicit_usd = len(text) * 100/1e6 (placeholder list price 100 USD per 1M chars for v3, price_confirmed=False), provider name "elevenlabs". Add a tiny helper to list premade voices (GET /v1/voices, filter category=="premade") usable from the CLI: `.venv/bin/python -m scripts.production.steps_extra voices` printing name|voice_id|labels only.

UNIT C — `finish` step (local, free): port /Users/rodrigoarista/.claude/jobs/4d5625f0/tmp/r2p/isp/phone_finish.py (read it fully; prototype "phone ISP" finish with presets night_indoor/daylight_outdoor/mirror_selfie) into scripts/production/phone_finish.py (≤200 lines), and a runner kind `finish` with fields `src` (relative path), `preset`, `seed`, `out` (.png). Cost 0, no gate. Test: output exists, same size as input, lossless PNG, differs from input, deterministic for the same seed.

VERIFY: `.venv/bin/python -m pytest tests/production -q` all green; `.venv/bin/ruff check` touched files; wc -l. Write the full report to .artifacts/agent-reports/runner-video-elevenlabs-finish-builder.md; return ≤8 lines: verdict, per-unit change, tests, mutation results, line counts, report path.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/production -q
.venv/bin/ruff check <touched files>
wc -l <touched files>
```

## Risk area to weigh
API key handling + money (charge recorded / not double-charged) + file I/O
