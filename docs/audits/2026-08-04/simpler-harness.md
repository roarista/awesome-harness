# Simpler harness — the smallest hook set worth keeping

2026-08-09. Proposal only. No hook, no `settings.json`, no code touched by
this doc. Every keep/cut below is justified from a measurement already on
disk under `docs/audits/**`, plus two bugs found today (cited as CONTEXT,
not yet filed as their own audit — reproduce with the commands in "Bugs
found today" below).

## Starting point

`~/.claude/settings.json` currently registers **47 hook entries** across 6
events (SessionStart, PreToolUse, PostToolUse, UserPromptSubmit, PreCompact,
Stop), calling ~30 distinct scripts. Verify count:

```
$ python3 -c "
import json; d=json.load(open('/Users/rodrigoarista/.claude/settings.json'))
print(sum(len(g['hooks']) for grp in d['hooks'].values() for g in grp))"
47
```

## The governing measurements

- `docs/audits/2026-08-04/component-impact.md`: of 7 components measured
  against user-correction-turn rate across 4,347 real transcripts, **zero**
  showed a positive effect. 4/7 (codemap, spawn-necessity, codex,
  codex-audit subagent) never reached n=15 fired sessions (UNDERPOWERED —
  no claim possible either way). The 3 that did clear n=15 (skill,
  understand-gate, check-all) all correlated with **worse** sessions, read
  as confound (they fire in already-messy sessions), not proof of harm.
- `docs/audits/2026-08-02/07-hook-effectiveness.md`: in the 103-transcript
  awesome-harness-specific corpus, **zero of 12 blocking-capable hooks ever
  produced an exit-2 block**. Explicit verdict section: CUT
  `phantom-edit-guard`, `caveman-discipline`, `coding-routing-guard`,
  `post-agent-guard`, `manifest-guard` (0 attributable value, real token/
  turn cost — e.g. caveman-discipline >=293 tokens/session-start, 64.3%
  non-compliance on its own rule). DEMOTE `builder-fence`, `understand-gate`,
  `northstar-inject` (advisory only, no causal evidence).
- `docs/audits/2026-08-02/11-harness-roi.md` line 217: evidenced-completion
  rate 33% with `/awesomeharness` vs 31% without — "no association
  whatsoever." The harness-as-a-whole has no measured completion effect.

## Bugs found today (2026-08-09, reproduce to verify)

- `irreversible-pause.py` lets `git stash` and `git checkout .` through
  (both silently destroy uncommitted work) while blocking on a mere mention
  of a trigger phrase in an unrelated command — false negative on the exact
  class it exists for, false positive elsewhere.
- `bash-write-fence.py` lets `python3 -c "open('x','w').write(...)"` through
  (a Bash-native file write, its entire reason to exist) while blocking a
  pure `.md` edit because a path string happened to appear in the script
  body — same pattern, wrong on both sides.

These two are exactly the guards this proposal keeps (irreversible damage is
the one real asymmetry) — kept, but flagged NEEDS-FIX, not trusted as-is.

## Category (a): guards against irreversible damage — KEEP, this is the only real asymmetry

A prose nudge that never fires costs a few hundred tokens. A missing guard
on `git checkout .` costs the user's actual work. Keep only hooks that
block (exit 2) on genuinely unrecoverable actions, even though 07 found
zero observed blocks for any of them yet — absence of a fire is not
evidence the trigger condition never occurs (n=103 transcripts, one repo).

| Hook | Guards against | Keep because |
|---|---|---|
| `irreversible-pause.py` (PreToolUse:Bash) | `git reset --hard`, `push --force`, `rm -rf`, etc. | Only hook targeting irreversible git/fs ops; NEEDS-FIX per bug above, but deleting it removes the only check on this class entirely |
| `bash-write-fence.py` (PreToolUse:Bash) | Bash-native file writes that bypass the Write/Edit sandbox | Only hook closing the Bash-as-write-bypass hole; NEEDS-FIX per bug above |
| `northstar-protect.py` (PreToolUse:Write/Edit/MultiEdit + Bash) | Deletion/corruption of `.northstar.md` (the one orientation file every other hook and this CLAUDE.md depends on) | Single cheap file-path check, 0 fires in 07 (not yet needed, not proof it's never needed), losing it silently breaks orientation for every future session |

## Category (b): context injectors — KEEP 1, cut the rest

| Hook | Verdict | Why |
|---|---|---|
| `codemap-inject.py` (SessionStart) | KEEP | component-impact.md: n=8 UNDERPOWERED (no correction-rate claim possible), but per `docs/audits/2026-08-03/codemap-compressed-repo-model.md` it injects the whole repo in 7.4KB and caught two fabricated signals pre-ship — the one injector with a documented positive catch, not just a correlation |
| `northstar-inject.py` (SessionStart AND UserPromptSubmit — registered twice) | CUT the UserPromptSubmit copy | Same content injected twice per turn for no measured benefit (07: DEMOTE, no causal evidence); SessionStart copy is redundant with `.northstar.md` being read directly by `northstar-protect` and CLAUDE.md already telling the model to check `.now.md`/STATE — fold the one essential line into codemap-inject's own header if still wanted, don't run a second script |
| `recall-inject.py` (UserPromptSubmit) | CUT | Zero fires recorded in 07; no independent measurement exists for it in any audit — no receipt to keep it |
| `manifest-guard.py` (SessionStart) | CUT | 07 explicit CUT: "11 noisy broad-drift alerts with no attributable remediation" |
| `graphify-gate.py` / `graphify-blindspot.py` (5 registrations: SessionStart, PostToolUse:Read/Bash, PreToolUse:Write/Edit/Read/Grep) | CUT all 5 | No hook-level measurement exists; CLAUDE.md already tells the model to use `graphify query`/`explain` directly (measured 288 calls/30d without the hook forcing it, per CLAUDE.md's own cited number) — the hook is redundant with a working habit, not the cause of it |

## Category (c): prose nudges telling the model what it already knows — CUT ALL

Every hook below either has an explicit CUT verdict in 07, or has never been
independently measured and duplicates something already stated once in
CLAUDE.md / the agent system prompts (which the model already reads every
turn — a hook re-stating it is pure token tax with no new information).

CUT, with 07's own receipt: `phantom-edit-guard.py`, `caveman-discipline.sh`,
`coding-routing-guard.sh`, `post-agent-guard.py`, `manifest-guard.py`
(counted above).

CUT, DEMOTED in 07 (advisory-only, zero causal evidence, and now also
correlate with worse sessions per component-impact.md): `builder-fence.py`
(PostToolUse:Bash and PreToolUse:Bash), `understand-gate.py` (PreToolUse:Task).

CUT, never independently measured in any audit under `docs/audits/**` —
absence of a receipt is itself the reason, per this doc's own rule "no
claim without a receipt" (the inverse: no receipt, no keep):
`now-gate.py`, `route-only-gate.py`, `main-edit-guard.py`,
`advertised-command-guard.py` (registered 3x: PostToolUse:Write/Edit,
PreToolUse:Bash, Stop), `reread-guard.py` (registered 3x: SessionStart,
PostToolUse:Read, PreToolUse:Read), `token-discipline.py`, `filesize-cap.py`,
`skill-reinject-guard.py`, `spawn-necessity.py`, `harness-enforce.py`,
`voice-dictation-nudge.sh`, `check-all-commit-gate.sh`,
`session-checkpoint.py`, `harness-usage-telemetry.py`,
`senduserfile-path-echo.js`, `post-agent-guard.py` (already counted),
`compact-prep-gate.py`, `abs-path-nudge.py` (registered 2x, a literal
duplicate registration bug), `speak.py`, `precompact-handoff.py`,
`pre_compact_global.sh`.

## Net result

| | Before | After |
|---|---:|---:|
| Total hook entries | 47 | 6 |
| Distinct scripts | ~30 | 4 (`irreversible-pause.py`, `bash-write-fence.py`, `northstar-protect.py`, `codemap-inject.py`) |
| Events touched | 6 | 2 (SessionStart, PreToolUse) |

What is lost: PreCompact handoff notes, Stop-time abs-path/advertised-command
nudges, telemetry, the graphify nudge hooks, the caveman-discipline
SessionStart reminder, routing/spawn advisories, recall-inject. None of
these have a measured positive effect anywhere in `docs/audits/**`; several
(caveman-discipline, coding-routing-guard, post-agent-guard, manifest-guard,
phantom-edit-guard) have an explicit measured-zero-value verdict already on
disk. If PreCompact/session-continuity turns out to matter, `.now.md` +
STATE (already required by CLAUDE.md's message-discipline section, no hook
needed) is the fallback the model is already instructed to maintain by hand.

## Exact `settings.json` diff

Not applied by this doc. To apply, replace the `"hooks"` object with:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [
        { "type": "command", "command": "python3 \"$HOME/.claude/hooks/codemap-inject.py\"", "timeout": 20 }
      ]}
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit|MultiEdit", "hooks": [
        { "type": "command", "command": "python3 \"$HOME/.claude/hooks/northstar-protect.py\"", "timeout": 5 }
      ]},
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "python3 \"$HOME/.claude/hooks/northstar-protect.py\"", "timeout": 5 },
        { "type": "command", "command": "python3 \"$HOME/.claude/hooks/irreversible-pause.py\"" },
        { "type": "command", "command": "python3 \"$HOME/.claude/hooks/bash-write-fence.py\"" }
      ]}
    ]
  }
}
```

(PostToolUse, UserPromptSubmit, PreCompact, Stop drop out entirely — no
hook survives in those events under this proposal.)

## Rollback (one command)

Before applying, snapshot:

```
cp ~/.claude/settings.json ~/.claude/settings.json.bak-2026-08-09
```

To revert after applying:

```
cp ~/.claude/settings.json.bak-2026-08-09 ~/.claude/settings.json
```

## What this doc does NOT do

It does not fix the two bugs in `irreversible-pause.py` / `bash-write-fence.py`
found today — those are load-bearing for category (a) and should be a
separate, small, verifiable unit before or alongside applying this diff. It
does not touch any hook file or `settings.json`. It does not re-run 07 or
component-impact.md's measurement scripts — all numbers above are quoted
from those files as they exist on disk today.
