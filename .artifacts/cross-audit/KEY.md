# Cross-audit KEY (auditors must NOT open this file)

Selection: 10 opus48-audit PASS verdicts, none a re-audit of an earlier REJECT. opus48 audited the uncommitted working tree; the listed commit landed 0-22 min after the audit ended, with no code edits in between (checked against transcripts) except where noted.

| unit | repo | sha | builder session | builder agent | opus48 agent | opus48 audit window (UTC) |
|---|---|---|---|---|---|---|
| U01 | virality-pipeline | 1f9e9680de | 99bc5ad8-25a2-4fba-a5d5-04b80b093d8b | agent-a044de226233ead9d | agent-adc5c1f36d0908666 | 2026-09-22T19:01..19:02 |
| U02 | virality-pipeline | 870e8956cc | 4d5625f0-9212-44a7-8b77-f2defe648895 | agent-a974429c4543d8d61 | agent-aff7d0d1bf84e701c | 2026-09-22T23:24..23:25 |
| U03 | virality-pipeline | 10ccadd5f3 | 4d5625f0-9212-44a7-8b77-f2defe648895 | agent-a24ade92eec9ebc76 | agent-a0fb36734f430f2b4 | 2026-09-23T00:24..00:25 |
| U04 | virality-pipeline | c2fd802ade | 4d5625f0-9212-44a7-8b77-f2defe648895 | agent-a40bf9f700c557cb4 | agent-a28ffde675b46b724 | 2026-09-23T02:16..02:17 |
| U05 | virality-pipeline | e35e7ef06b | 99bc5ad8-25a2-4fba-a5d5-04b80b093d8b | agent-a91d544cbfa7c7506 | agent-a6ee66fc497158268 | 2026-09-23T17:27..17:29 |
| U06 | virality-pipeline | e39c172435 | d98073eb-4f60-4a0e-bfb2-ca25393e311f | agent-a3f12bcf3e65da30e | agent-ae29b7c65c6939b9b | 2026-09-23T20:39..20:41 |
| U07 | virality-pipeline | 396e9f1e9d | d98073eb-4f60-4a0e-bfb2-ca25393e311f | agent-aef258fd81c4e217c | agent-a91e4b21d7044daa3 | 2026-09-23T21:08..21:10 |
| U08 | virality-pipeline | 43b457dd90 | d98073eb-4f60-4a0e-bfb2-ca25393e311f | agent-a5fcd46bcddc9beff | agent-a494295ffadaaa302 | 2026-09-24T15:20..15:21 |
| U09 | virality-pipeline | 2d0b0cafd2 | 4d5625f0-9212-44a7-8b77-f2defe648895 | agent-af66a6680c73b6a04 | agent-a6700001ca5bfdb79 | 2026-09-30T00:02..00:04 |
| U10 | virality-pipeline | 0155914771 | b1947e1e-d8ff-4239-845d-bc53d2ac8df7 | agent-a9c8f136ddab9c77e | agent-a69164a8cd2ba76c3 | 2026-10-01T05:20..05:22 |

Notes:
- U09 (V4): after the opus48 audit the builder fixed one LOW (local provider cache key ignores the voices.json `model` field) before committing; the commit therefore includes a small post-audit edit. Codex audit.sh was out of quota, so opus48 was the first and only auditor.
- Every commit message contains the verdict ("audit opus4.8 PASS" etc.) and every commit also adds the opus48 auditor report under .artifacts/agent-reports/. The unit files forbid both.
- The original opus48 prompts also carried orchestrator-written attack lenses (not verdicts); they are in the transcripts above if you want a parity run.
- Candidate considered and dropped: V4c money path (agent ...151348572) because a GPT-6-Sol round 1 had 2 HIGH before opus48 audited the fixed code (re-audit after a reject-level finding).

## opus48 verdict summary (C/H/M/L as opus48 stated them)

| unit | verdict | C/H/M/L | top finding |
|---|---|---|---|
| U01 E5a embed client | PASS | 0/0/0/3 | LOW embed_client.py:96 httpx.Client never closed (also: no sqlite busy_timeout; uncapped Retry-After) |
| U02 treg 403 headers | PASS | none listed | (no findings; header parity + token masking judged sound) |
| U03 seedance roles + voice | PASS | 0/0/1/1 | MEDIUM steps.py:59 WAV bytes saved as voice.mp3, may waste a paid Seedance call |
| U04 runner video/ElevenLabs/finish | PASS | 0/0/0/2 | LOW steps_extra.py:105 no `..` traversal guard on finish src |
| U05 E6b live re-embed | PASS | 0/0/0/2 | LOWs only; crash mid-run leaves mixed embedding space (judged healable) |
| U06 handoff hang regex | PASS | 0/0/0/0 | none; one-regex gate judged a superset of old loop |
| U07 R1 AI Mode stage | PASS | 0/0/1/3 | MEDIUM ai_mode.py:31 prose cache defaults under .artifacts/agent-reports; LOW possible gemini parse double-charge on retry |
| U08 treg 503 retryable | PASS | none listed | (no findings; budget re-gate per call judged sufficient) |
| U09 V4 local voice | PASS | 0/0/1/1 | MEDIUM run_chain.py:199-201 any voiceover exception becomes silent "dry-run, no audio" advisory (out of scope) |
| U10 D2 transcript cache | PASS | 0/0/0/2 | LOWs only (informational) |

Units with MEDIUM passed: U03, U07, U09. Units with no findings listed: U02, U06, U08.

## U01: E5a paid embedding client
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/99bc5ad8-25a2-4fba-a5d5-04b80b093d8b/subagents/agent-adc5c1f36d0908666.jsonl
- opus48 description: Audit E5a embed client (Opus 4.8)
- Verdict line: VERDICT: PASS — no HIGH/CRITICAL. Tests: 9 passed (ran `.venv/bin/python -m pytest tests/creative_rag/test_embed_client.py -q`).
- Final report (verbatim, opus48's return):

````text
VERDICT: PASS — no HIGH/CRITICAL. Tests: 9 passed (ran `.venv/bin/python -m pytest tests/creative_rag/test_embed_client.py -q`).
Counts: CRITICAL 0, HIGH 0, MEDIUM 0, LOW 3.
Top finding (LOW): `src/creative_rag/embed_client.py:96` — httpx.Client opened, never closed; fix: add close()/context-manager.
Other LOWs: line 60 no sqlite busy_timeout (concurrent-writer lock); line 218 uncapped `float(Retry-After)` defeats the total-wait cap.
Verified sound: no key leak — Gemini key is in the `x-goog-api-key` header, not a `?key=` URL param, and error strings log only status+body[:200]; cache order/partial-hits/input_type keying; batch_size 64 under all provider caps; retry only on 429/5xx honouring Retry-After; cache hit records $0; normalization matches local bge (both L2-normalize); tests are mutation-proof, not green-by-construction.
Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/e5a-auditor.md
````


## U02: production treg client 403 header fix
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/4d5625f0-9212-44a7-8b77-f2defe648895/subagents/agent-aff7d0d1bf84e701c.jsonl
- opus48 description: Audit treg 403 header fix
- Verdict line: VERDICT: PASS
- Final report (verbatim, opus48's return):

````text
VERDICT: PASS

- Header parity sound: DEFAULT_USER_AGENT imported (not duplicated) from s1 client; sends UA (TREG_USER_AGENT env or default) + `ngrok-skip-browser-warning: 1`, matching src/s1/scrapers/treg_client.py.
- Token leakage: 403 body truncated to 300 chars then exact token str.replace'd to `***`; `_gate_error` (402/503) omits token; `from exc` chain carries only the HTTPError response, no token.
- Tests real, not green-by-construction: error test seeds "test-token" into the fake body and asserts it is absent + len<400; UA test asserts value and rejects Python-urllib prefix.
- Sibling sweep clean: treg_client.py is the only treg.to caller in src/production and src/video_v2; other urllib callers hit non-treg hosts.
- Verified: `.venv/bin/python -m pytest tests/production -q` → 428 passed, 2 skipped.
- LOW (non-blocking): masking is exact-substring only (no encoded/case-shifted echo); treg bodies do not echo the token, so no exposure.
- Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/tg1-fix-403-auditor.md
````


## U03: Seedance frame-role validation + runner voice step
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/4d5625f0-9212-44a7-8b77-f2defe648895/subagents/agent-a0fb36734f430f2b4.jsonl
- opus48 description: Audit seedance roles + voice step
- Verdict line: PASS. Counts: 0 CRITICAL, 0 HIGH, 1 MEDIUM, 1 LOW.
- Final report (verbatim, opus48's return):

````text
PASS. Counts: 0 CRITICAL, 0 HIGH, 1 MEDIUM, 1 LOW.

Top finding (MEDIUM): fish_audio.synthesize always requests `format:"wav"` but voice `out` defaults to `voice.mp3` (steps.py:59); WAV bytes named .mp3 are hosted as seedance audio and may be rejected downstream, wasting a paid seedance call. Fix: default `out:"voice.wav"`. Builder flagged this honestly.

LOW: voice price 15 USD/1M chars is an unverified placeholder (steps.py:26), correctly recorded price_confirmed=False.

Verified: 440 passed / 2 skipped reproduced; re-run skips existing output so no double-charge (idempotent); cost is recorded even on missing-file (records then raises); no voice_id/api_key leakage into ledger or stdout; new tests fail on mutated code (not green-by-construction); build_body never sets both roles and image_urls; file caps 153/149 <=200.

Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/sd25-roles-voice-auditor.md
````


## U04: runner: Seedance video refs, ElevenLabs voice, phone finish
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/4d5625f0-9212-44a7-8b77-f2defe648895/subagents/agent-a28ffde675b46b724.jsonl
- opus48 description: Audit runner video/ElevenLabs/finish
- Verdict line: PASS. Findings: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 2 LOW.
- Final report (verbatim, opus48's return):

````text
PASS. Findings: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 2 LOW.

Top finding: LOW - `run_finish` reads `folder / step["src"]` with no `..` traversal guard (steps_extra.py:105); local read, matches existing `_refs`; fix by rejecting `..` in `validate_finish`. Second LOW: `seedance25.generate`'s internal budget gate counts only output seconds (seedance25.py:115), so direct callers with video refs under-gate — but the runner covers it via `_gate` for video steps (steps.py:160).

Verified (all sound): key never printed/logged and absent from HTTPError str + results.jsonl; ElevenLabs order gate->call->record->record-then-raise; no double-charge (run loop skips existing outputs via `done()`); MAX_VIDEOS=10 enforced in build_body; frame-role rejection at both build_body and validate; atomic `.part`+replace writes leave no partial; tests reproduced 461 passed / 2 skipped.

Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/runner-video-elevenlabs-finish-auditor.md
````


## U05: E6b live re-embed script
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/99bc5ad8-25a2-4fba-a5d5-04b80b093d8b/subagents/agent-a6ee66fc497158268.jsonl
- opus48 description: Audit E6b live re-embed script
- Verdict line: VERDICT: PASS. Severity counts — CRITICAL 0, HIGH 0, MEDIUM 0, LOW 2.
- Final report (verbatim, opus48's return):

````text
Verified the spec, script, tests, store.reembed_stale (atomicity), active_model query path, embed_client cache/ledger, and ran the suite + dry-run.

VERDICT: PASS. Severity counts — CRITICAL 0, HIGH 0, MEDIUM 0, LOW 2.

- Tests: 272 passed; ruff clean on both E6b files (the 3 remaining ruff errors are pre-existing I001 in test_ingest_practitioner_techniques.py, not this unit). reembed_live.py = 148 lines (≤150). Live --dry-run is read-only: 3438 stale rows, est $0.0947, no backup created.
- Lens 1 (data loss): backup VACUUM INTO (reembed_live.py:90-92) runs from a read-only conn BEFORE any write; reembed_stale is atomic (store.py:270-299, single _connection/one commit). Crash anywhere leaves at worst active=gemini+bge vectors (mixed space) but re-run heals since reembed_stale re-selects by embed_model!=active. No permanent loss.
- Lens 2 (cost): cap is a pre-write estimate; real spend ≤ estimate (cache at embed_client.py:23 default absolute path reuses bake-off texts; cost recorded to state/costs.jsonl). Worst-case bounded ~$0.09 « $1 cap.
- Lens 3 (query): after set_active_model, store.search:330→active_model.query_embedder uses PaidEmbedder(model,"query") with NO env var; eval runs as subprocess but reads active model from rag_meta (persisted), so it does NOT miss it.
- Lens 4: reembed_stale rebuilds rag_vec_aspect via replace_aspect_vectors (store.py:296-298) with the same gemini embedder — no mixed space.
- LOW-1: after a crash, re-run needs --allow-existing-backup (same-date backup blocks resume) — friction, message tells operator. LOW-2: plan stale-count query (embed_model IS NULL) differs from reembed_stale's key_version clause — estimate-only drift, cache-covered. Per global policy I return findings inline rather than writing e6b-auditor.md.
````


## U06: S1 audience handoff hang fix (privacy cleaners regex)
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/d98073eb-4f60-4a0e-bfb2-ca25393e311f/subagents/agent-ae29b7c65c6939b9b.jsonl
- opus48 description: Audit handoff hang fix
- Verdict line: PASS. Findings: CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0.
- Final report (verbatim, opus48's return):

````text
PASS. Findings: CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0.

Top finding: none — the privacy-critical invariant holds. The one-regex gate matches a superset of the old per-handle loop (same escaped literals, same IGNORECASE, boundary assertions distribute over the trie alternation; greedy `(?:x)?` backtracks). My independent fuzz of 20k handle sets with regex metachars/unicode/whitespace over 60k+ texts in both boundary modes produced 0 false negatives, so the fast-path never skips a text the old code would redact.

Verified: 8 passed (test_audience_handoff + test_handoff_perf), 42 passed across 5 signals test files, ruff clean on all 4 files, line counts 200/52/42 (<=200). Perf tests are count-based (monkeypatched `re._compile`), not timing-flaky. Cache is a per-invocation closure -> no cross-brand leak, bounded 65536. Builder's "11 unrelated failures" claim confirmed: test_person_attribute_registry.py and test_dissection_read.py import registry/dissection_read, not the changed modules (they belong to other terminals' dirty files).

Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/handoff-hang-auditor.md
````


## U07: R1 Google AI Mode research stage per creator
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/d98073eb-4f60-4a0e-bfb2-ca25393e311f/subagents/agent-a91e4b21d7044daa3.jsonl
- opus48 description: Audit AI Mode stage R1
- Verdict line: (none matched)
- Final report (verbatim, opus48's return):

````text
R1 AI Mode stage: PASS (no high/critical). 33 tests pass (test_ai_mode_stage, test_ficha, test_treg_client, test_creator_audience_ai); ruff clean.

Counts: MEDIUM 1, LOW 3.
- MEDIUM src/s1/audience/ai_mode.py:31 — DEFAULT_PROSE_DIR is `.artifacts/agent-reports/ai-mode`; pipeline cache in an agent-reports namespace is wrong for a hosted pipeline. Fix: default under `$PIPELINE_STATE_DIR/research/ai_mode_prose`.
- LOW ai_mode.py:40-46 — creator_specific=false record is "valid" and skipped forever (distinguishable via flag, but never re-fetched). LOW creator_audience_ai.py:65-69 — extraction retried identically once → can double-charge gemini parse. LOW treg_client.py:118-124 — cache replay with missing cost header over-bills estimate (conservative).

Verified sound: budget checked before / real USD recorded after under run_tag; CostGateError stops+re-raises pool; dataforseo fallback fails closed; provider/parse failures never cached, writes atomic; GET callers keep historical idempotency key and tests pass; token never logged; extraction prompt treats web text as DATA not instructions; all files <=200 lines.

Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/r1-ai-mode-auditor.md
````


## U08: S1 treg client: HTTP 503 no longer treated as spend gate
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/d98073eb-4f60-4a0e-bfb2-ca25393e311f/subagents/agent-a494295ffadaaa302.jsonl
- opus48 description: Audit treg 503 fix
- Verdict line: VERDICT: PASS. No high/critical findings.
- Final report (verbatim, opus48's return):

````text
VERDICT: PASS. No high/critical findings.

Verified (all sound):
- Money: `check_budget` + hard run-cap run before every treg call (`treg_client.py:95-101`), so even a mis-classified retryable 503 cannot spend past the cap — each loop re-gates.
- Failed 402/503 calls raise before `costs.record` (line 137+): nothing billed, no ledger row (test asserts `not ledger.exists()`).
- No unbounded retry: `comment_harvest.py` inner loop is `range(pages)` + per-post `except Exception`; `ai_mode_fu_chat` restarts at most once (`restarted` flag); `ai_mode_fetch.fetch` is PRIMARY→FALLBACK then raises.
- ValueError never cached as success: turn files written only after answer; `CostGateError` never in `_ERRORS`, always propagates.
- 11 tests pass; ruff clean.

LOW: `_is_treg_gate` over-triggers on upstream text with quota/budget words → fail-safe (stops run, no overspend). `src/production/treg_client.py` still maps all 503→gate (out of scope; builder flagged). Report: `/Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/treg-503-fix-auditor.md`
````


## U09: V4 local (Kokoro) voice provider by default
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/4d5625f0-9212-44a7-8b77-f2defe648895/subagents/agent-a6700001ca5bfdb79.jsonl
- opus48 description: Audit V4 local voice unit
- Verdict line: VERDICT: PASS (no CRITICAL/HIGH; MEDIUM is a run_chain follow-up outside V4's edited paths).
- Final report (verbatim, opus48's return):

````text
All 25 tests pass. I read synthesize.py (whole diff), the new test file, run_chain.py:190-210, voices.py, local_tts.py, local_align.py, and both lock/pyproject diffs.

Findings

MEDIUM — src/video_v2/run_chain.py:199-201 (out of CHANGE scope, but V4 makes it newly wrong). The stage-boundary handler converts ANY voiceover exception into a silent `"09b_voiceover: dry-run, no audio"` advisory when `--tts-live` is absent. Under V4 the ordinary (no-flag) run is exactly when local is *supposed* to speak, so a real local failure (LocalTTSError = mlx/Kokoro missing, or LocalAlignError = whisper mismatch) is now masked as "dry-run" and the pilot silently ships a video with no voiceover. Invariant is technically intact (nothing is cached as success), but the failure is hidden. Fix: gate the advisory on `provider != "local"` (or on DryRunResult, not on exceptions) — belongs in a V4 follow-up, not this unit, since the file is out of scope; flag to Ro.

LOW — src/video_v2/tts/synthesize.py:77-78. For local, `model = voice.get("model") or MODEL_REPO` is folded into the cache key and stored in the artifact, but `_speak_local`/`local_tts.synthesize` take no repo arg and always use `MODEL_REPO`; a custom `voice.model` would silently diverge from the audio actually produced. Fix: `model = local_tts.MODEL_REPO` for local, ignore `voice.get("model")`.

What I verified sound: spec met (provider `local` → V2+V3, `live is not False` gate: None/absent runs, explicit False dry-runs — tests confirm); paid live gate unchanged (`test_paid_provider_keeps_the_live_gate`); paid cache key byte-identical (`sha(text, voice_id, model)`), speed in local key only; failure isolation/idempotency (align mismatch raises before `save_artifact`, nothing cached, retry re-synths); env override `VIDEO_V2_TTS_PROVIDER=local`; callers (`run_chain.py:49,192`, `PROVIDERS`, `_provider`) intact; synthesize.py 127 lines (<200); uv.lock moves only `en-core-web-sm` 3.8.0 (url-pinned wheel, arm64+darwin marker), no other package version changed; pyproject pin matches. Tests are genuine (would fail on a broken impl), not green-by-construction.

VERDICT: PASS (no CRITICAL/HIGH; MEDIUM is a run_chain follow-up outside V4's edited paths).
````


## U10: D2 YouTube transcript disk cache
- opus48 transcript: ~/.claude/projects/-Users-rodrigoarista-Downloads-virality-pipeline/b1947e1e-d8ff-4239-845d-bc53d2ac8df7/subagents/agent-a69164a8cd2ba76c3.jsonl
- opus48 description: Audit D2 transcript cache
- Verdict line: Verdict: PASS. No CRITICAL/HIGH/MEDIUM; 2 LOW (informational).
- Final report (verbatim, opus48's return):

````text
Verdict: PASS. No CRITICAL/HIGH/MEDIUM; 2 LOW (informational).

Verified: 69 youtube tests pass, ruff clean, line counts all ≤200 (gate 138, _transcripts 65, test 143). In-memory mutation checks (no repo writes) confirm the throttle flag and cache-read `_ERROR` guard are load-bearing and tests catch their removal.

Lens 1 (poison never cached/judged): SOUND — `_THROTTLED` intercepts at _transcripts.py:57 before save; save/append gated by `returncode==0 and text and not _ERROR` at :61; cache reads filtered by `_ERROR` at :47 (stale RATE_LIMITED refetched).
Lens 2 (path/atomic/crash): SOUND — 11-char `VIDEO_ID.fullmatch` allowlist at :38 precedes path build at :40 (no traversal); `_save` tempfile + `os.replace` + finally unlink leaves no partial file.
Lens 3 (throttle scope + pending): SOUND — single `run_state` shared across creators (gate.py:84); first throttle halts all further subprocess calls, uncached channels go to pending; fresh dict per run so it retries.
Lens 4: tests assert call-lists/file contents/dir listings, not green-by-construction.

LOW (non-blocking): `inspect.signature` cache_dir shim always-true; `_ERROR` substring could false-reject a transcript literally containing "NO_CAPTIONS:" (fails safe).

Report: /Users/rodrigoarista/Downloads/virality-pipeline/.artifacts/agent-reports/d2-transcript-cache-auditor.md
````
