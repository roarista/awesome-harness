# Cross-audit U09: V4 local (Kokoro) voice provider by default

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 2d0b0cafd2d1:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `2d0b0cafd2d1b87c5de90c6260689675a8e126e7` (parent `54d7c1d267b1ec9555e4d4c2345fc086cf2749f1`)
- Builder report (claim): `.artifacts/agent-reports/pilot-V4-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 54d7c1d267b1 2d0b0cafd2d1 -- pyproject.toml uv.lock src/video_v2/tts/synthesize.py tests/video_v2/test_run_chain_voiceover.py tests/video_v2/test_tts_local_provider.py tests/video_v2/test_tts_voices.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 2d0b0cafd2d1 -- pyproject.toml uv.lock src/video_v2/tts/synthesize.py tests/video_v2/test_run_chain_voiceover.py tests/video_v2/test_tts_local_provider.py tests/video_v2/test_tts_voices.py
```

Code stat (unit paths only):
```
pyproject.toml                             |   4 ++
 src/video_v2/tts/synthesize.py             |  68 +++++++++++++-----
 tests/video_v2/test_run_chain_voiceover.py |  19 ++++++
 tests/video_v2/test_tts_local_provider.py  | 106 +++++++++++++++++++++++++++++
 tests/video_v2/test_tts_voices.py          |   9 +++
 uv.lock                                    |  10 +++
 6 files changed, 198 insertions(+), 18 deletions(-)
```

Note: The builder rules mention an audit loop; ignore that part, it is process, not spec. Note the orchestrator override in the prompt: `brands/intrn/voices.json` must NOT be edited.

## Unit spec as given to the builder (verbatim, 2026-09-29T23:58:37.126Z)

````text
Read and follow the builder rules in /Users/rodrigoarista/.claude/jobs/4d5625f0/tmp/builder_rules.txt (Codex out of quota — use the opus48-audit fallback). Keep tool calls short. Your unit: V4 (local voice) in .planning/PILOT_01B_07_UNITS_2026-09-28.md, WITH ONE ORCHESTRATOR CHANGE: do NOT edit brands/intrn/voices.json (brand files need Ro's OK and the voice pick is open question G10). Build everything else: tts/synthesize.py adds provider `local` → src/common/local_tts.synthesize (V2) + src/video_v2/tts/local_align (V3); local is free, so it synthesizes on every chain run without the paid live gate (the gate stays for paid providers); voices.resolve_voice must honour a voices entry with provider `local`. Tests: an ordinary run_chain call with no env vars and no --tts-live, using a tmp voices.json whose default is a local Kokoro entry, yields a 09b_voiceover artifact with provider local and aligned words (Kokoro/whisper stubbed). Also write, in the report, the exact voices.json diff you WOULD apply (Kokoro default af_heart speed 1.0, Laura kept as a named ElevenLabs entry) so Ro can approve it in one line. Also pin en-core-web-sm in uv.lock/pyproject if V2's report says it was auto-installed unpinned (follow V1's lock method: no version of anything else may move). Read pilot-V1/V2/V3-builder.md first. Report .artifacts/agent-reports/pilot-V4-builder.md; return ≤8 lines incl. audit verdict.
````

### Referenced spec file: /Users/rodrigoarista/.claude/jobs/4d5625f0/tmp/builder_rules.txt (builder rules referenced by the prompt) + the V4 line of .planning/PILOT_01B_07_UNITS_2026-09-28.md as of commit 37d5b34f

````text
You are the BUILDER for one unit in /Users/rodrigoarista/Downloads/virality-pipeline (branch codex-procedure-parity; other terminals share this checkout). Keep reads scoped, be concise.
Spec source: .planning/PILOT_01B_07_UNITS_2026-09-28.md (find your unit ID; its CONTEXT/REUSE/CHANGE/GOAL/VERIFY are binding; the design cards it cites live in .artifacts/agent-reports/P-*-cards-2026-09-28.md). Earlier units' reports: .artifacts/agent-reports/pilot-<ID>-builder.md.
Rules: touch ONLY the unit's CHANGE files plus new tests for it. Every file you create/edit ≤200 lines; files already >200 may only shrink. Write src files with the Write/Edit tools (Bash writes into src are hook-blocked). Use .venv/bin/python. NEVER run git add/commit/stash/checkout/reset/restore/clean; never touch STATE/.now.md/.mulch or other lanes' files; leave no background processes. Tests must be able to fail: for each new test, make the breaking change, see it fail, revert (note this in the report). No model/paid API calls.
Finish with: the unit's VERIFY command(s), plus `.venv/bin/python -m pytest -p no:randomly -q tests/video_v2` tail, `.venv/bin/python -m pytest -p no:randomly -q tests/creative_rag` tail (it reads video_v2 source), `ruff check` on touched files, `wc -l` on touched files.
Write the report to .artifacts/agent-reports/pilot-<ID>-builder.md. Return ≤8 lines: verdict, files+line counts, tests, risk, any spec ambiguity you resolved (and how).
AUDIT LOOP (after your VERIFY is green): run `/Users/rodrigoarista/.claude/jobs/4d5625f0/tmp/audit.sh <ID> "<space-separated paths you touched>"` (Bash, timeout 600000; it calls an independent GPT-6-Sol auditor, read-only, and writes .artifacts/agent-reports/pilot-<ID>-audit.md). If audit.sh output shows Codex is out of quota/unavailable, audit instead with the Agent tool, subagent_type opus48-audit, giving it the same auditor prompt (spec, paths, lenses) and saving its answer to the audit report path. Fix every CRITICAL/HIGH/MEDIUM finding (LOW: fix if cheap, else give a reason in the report), rerun VERIFY, then re-run audit.sh once if you fixed any HIGH/CRITICAL. Never dismiss a finding without reproducing it; write why in the report. At most 3 audit rounds: if a 3rd round still finds HIGH of the same kind (e.g. new phrasings past a word-pattern check), stop, list them in the report as a known limit, and return. Your ≤8-line return must include the final audit verdict.


--- .planning/PILOT_01B_07_UNITS_2026-09-28.md @37d5b34f, line 15 ---
Test command prefix: `T=".venv/bin/python -m pytest -p no:randomly -q"`.

--- same file, lines 99-103 (V1-V5) ---
**V1 — install.** CHANGE: `pyproject.toml` adds `mlx-audio` (Apple Silicon marker); `.venv/bin/pip install mlx-audio`; first run downloads Kokoro-82M weights (free, HF). VERIFY: `.venv/bin/python -c "import mlx_audio"`. DEPENDS: —.
**V2 — Kokoro wrapper.** CHANGE: new `src/common/local_tts.py` (`synthesize(text, voice, speed, out_path) -> Path`, lazy import). VERIFY: `$T tests/common/test_local_tts.py` (mocked) + manual one-sentence WAV. DEPENDS: V1.
**V3 — whisper alignment.** REUSE `caption_timing._tokens:11`, `check_voice_words`. CHANGE: new `src/video_v2/tts/local_align.py` (whisper `word_timestamps=True` → `tuple[WordStamp]`, token-match against the script, raise on mismatch). VERIFY: `$T tests/video_v2/test_local_align.py` (canned whisper output, mismatch raises). DEPENDS: —.
**V4 — local voice by default.** CONTEXT: `voices.resolve_voice:45` picks `default`/rotation; a separate `local` entry would be ignored without an env override. CHANGE: `tts/synthesize.py:17,25-30,70-80` adds provider `local` → V2 + V3; local is free, so it synthesizes on every chain run (the live gate stays for paid providers only); `brands/intrn/voices.json` `default` becomes the Kokoro voice (provider `local`, voice id + speed, G10), Laura kept as a named ElevenLabs entry for the later swap. VERIFY: `$T tests/video_v2/test_tts_synthesize.py tests/video_v2/test_run_chain_voiceover.py tests/video_v2/test_tts_voices.py` (new case: an ordinary `run_chain` call with no env vars and no `--tts-live` yields a `09b_voiceover` artifact with provider `local` and aligned words; Kokoro/whisper stubbed). DEPENDS: V2, V3.
**V5 — local smoke (free, real).** Manual: with no TTS env vars set, `run_voiceover` on a saved run whose 09 exists (or a fixed 30-word text) → WAV + words matching the text token for token, provider `local`. DEPENDS: V4.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
T=".venv/bin/python -m pytest -p no:randomly -q"
$T tests/video_v2/test_tts_synthesize.py tests/video_v2/test_run_chain_voiceover.py tests/video_v2/test_tts_voices.py tests/video_v2/test_tts_local_provider.py
.venv/bin/ruff check <touched files>
wc -l <touched files>
```

## Risk area to weigh
paid-gate bypass (money) + TTS cache correctness + dependency pin (uv.lock)
