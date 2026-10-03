# Product-call isolation — 2026-10-03

Ask (Ro): "make sure the harness doesn't interfere with other work." Product code
(virality-pipeline) runs headless `claude -p`; each of those sessions got ~14 KB of
harness hook text (rule-value-audit §3).

## Signal (measured, not guessed)
- Probe hook via `claude -p --settings /tmp/pcprobe/settings.json` (user settings untouched):
  stdin carries only session_id/transcript_path/cwd/hook_event_name/permission_mode/prompt —
  **no entrypoint field**. Env carries `CLAUDE_CODE_ENTRYPOINT=sdk-cli` and `CLAUDE_PROJECT_DIR`.
- This background job: `CLAUDE_CODE_ENTRYPOINT=cli` + `CLAUDE_JOB_DIR` set.
- 45-day transcript census (`entrypoint` field of each jsonl):
  - 8,243 temp-dir sessions (8,233 under `/private/var/folders`) — **all `sdk-cli`**.
  - Ro's sessions in repos: `cli`.
  - BUT `sdk-cli` also runs in repo dirs and is harness work: virality AUDITOR units,
    Consulting builders, harness-scout passes, jobs-app calls. So `sdk-cli` alone is NOT safe.
- Rule (`hooks/_hookout.py:is_product_call`): entrypoint starts with `sdk` AND no
  `CLAUDE_JOB_DIR` AND realpath(`CLAUDE_PROJECT_DIR` or cwd) under
  `/private/var/folders/ /var/folders/ /private/tmp/ /tmp/`. `HARNESS_HOOKS=on|off` overrides.
  Any exception -> False (harness stays on). Env-only, so hooks check before reading stdin.
- Trade-off: `/tmp` cwd counts as product (task asked for a /tmp verification). Ro's own
  hook-probing `claude -p` runs from /tmp (e.g. "echo PWNED_TEST") now see no harness gates
  either — use `HARNESS_HOOKS=on` for those.

## Change
- `_hookout.py`: `is_product_call()`, `exit_if_product()`, CLI (`python3 _hookout.py` exit 0 = product).
- All 27 registered hook scripts + `coding-routing-guard.py` (exec'd by the .sh):
  - Python: first import line becomes `import _hookout; _hookout.exit_if_product(); import X`
    (same line -> net 0 lines; 7 files are over the 200-line ratchet and may not grow).
  - Shell (caveman-discipline, coding-routing-guard, pre_compact_global):
    `python3 "$(dirname "$0")/_hookout.py" && exit 0` after the shebang.
- Live `~/.claude/hooks`: same guard inserted surgically into each live file — NOT synced
  from the repo (see drift below). Live `_hookout.py` replaced with the repo version:
  live was 291 B (inject only), a strict subset.

## Pre-existing drift found (NOT resolved — Ro decides)
- 14 live hooks differ from the repo and share one mtime (2026-10-02 11:25). `~/.claude` is not
  git, and the live content matches no repo commit. Live is mostly the OLDER pre-context-diet text
  (live `coding-routing-guard.sh` still names glm 5.2 as the auditor; live `caveman-discipline.sh`
  carries the long MESSAGE DISCIPLINE block that matches the current global CLAUDE.md).
  Files: _hookout caveman-discipline graphify-gate skill-reinject-guard northstar-protect
  now-gate route-only-gate irreversible-pause coding-routing-guard.sh filesize-cap
  post-agent-guard recall-inject northstar-inject harness-enforce compact-prep-gate.
- Live bug, fixed as a side effect: live `skill-reinject-guard.py` and `coding-routing-guard.py`
  call `_hookout.once()`/`sid_of()`, which the 291 B live `_hookout` lacked, so they raised
  AttributeError on every fire. Now present.

## Verify
- `python3 tests/test_product_call_isolation.py` -> 5/5 OK (repo); `HOOKS_DIR=~/.claude/hooks` -> 5/5 OK (live).
  The test runs every registered hook from settings.json: product env -> (0, "");
  normal env -> output and rc equal to a guard-stripped copy; plus a mutation check and the rule table.
- Mutation: the whole suite against a guard-stripped hooks dir -> FAILED (failures=6):
  caveman-discipline, harness-enforce, irreversible-pause, post-agent-guard, pre_compact_global
  leak, and the guard-presence test fails.
- Real call: `cd /tmp/pcreal && claude -p --model haiku --output-format json "reply ok"` with job env
  stripped -> session 7a7602b0. Hook-injected bytes: 14,468 in each of the last 3
  `/private/var/folders` product transcripts -> 4,156. The remaining 4,156 B is the **ponytail plugin**
  SessionStart banner only. Zero CONTRACT/FLOOR/recall/NORTHSTAR/manifest text. compact-prep-gate ran
  silently (28 ms).
- `tools/git-hooks/test_pre_commit.sh` -> 29 passed, 0 failed.

## Not harness-fixable (report only)
- **ponytail plugin** (`~/.claude/plugins/cache/ponytail/ponytail/4.7.0/hooks/hooks.json`) and the
  codex plugin's Stop hook (`stop-review-gate-hook.mjs`) are outside this repo. They are not edited.
  Global `~/.claude/CLAUDE.md` + skill/agent listings are also loaded by Claude Code itself, not by hooks.
  Only the caller can drop these (below).

## Caller-side fix for virality (NOT applied — other terminals own it)
virality already has the right flags: `src/video_v2/model_call.py:39 CLAUDE_ISOLATION`
(`--safe-mode --setting-sources local --tools "" --no-session-persistence ...`), applied only
on the video_v2 path. `--safe-mode` disables hooks, plugins and CLAUDE.md and keeps OAuth/subscription
auth (per `claude --help`). `--bare` is NOT usable: it reads only ANTHROPIC_API_KEY, never OAuth.
One-line change per call site — add `"--safe-mode"` after `"-p"`, e.g. `src/dissection/claude_vision.py:33`:
    cmd = ["claude", "-p", "--safe-mode", "--model", model]
Other bare call sites: src/originated/_subagent_client.py:61,71; src/skill_builder/claude_client.py:172;
src/translation/translator.py:143; src/s1/audience/persona_write_split.py:132;
src/production/caption_style_analyzer/analyzer.py:93; src/production/video_caption_director/directors.py:112;
src/production/caption_affordance/providers/claude.py:122.
(I did not run `--safe-mode` myself; the 2-real-call budget went to the probe and the verification.)
