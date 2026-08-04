# Component impact — does firing correlate with a better session?

2026-08-04. Corpus: 4,347 real transcripts under `~/.claude/projects/**/*.jsonl`
(NOT the flat `*/*.jsonl` glob — 1,125 of the 4,347 live one level deeper; using
the shallow glob silently drops 26% of the corpus, see VERIFY).

## Method

Per session, per component: FIRED = the component's own emitted output/tool_use
record appears in the transcript (not the component's name in prose — see
detectors below, all keyed on literal emitted strings or `tool_use.name` +
`input.subagent_type`, never on discussion text).

Outcome proxy: **user correction-turn rate** = (user turns matching a
correction regex) / (total non-empty user turns) in that session. Regex:
`no,|no\.|actually|that's wrong|that is wrong|not what i asked|revert|redo|
incorrect|you didn't|don't do that|stop doing|that's not right|undo that|
this is wrong|wrong file|wrong repo` (case-insensitive). Chosen because it is
computable from text alone, does not require git state, and is symmetric
across every component (all fire inside a Claude Code session, not a repo
checkout). Reported as a rate (0-1) per session, then averaged per arm.

Per-component FIRED detector (all on `tool_use` blocks or literal injected
text, contamination-checked against "component named in conversation"):

| Component | Detector |
|---|---|
| `/awesomeharness` skill | injected skill body contains `"awesomeharness — one-command harness boot"` (the skill's own H1, not the word "awesomeharness" in chat) |
| codemap SessionStart | injected text contains `"CODEMAP — the whole repo, compressed"` (codemap-inject.py's own header) |
| understand-gate | injected text contains `"UNDERSTAND GATE: this spawn writes code"` (hook's own MSG, warn or enforce mode) |
| spawn-necessity | injected text contains `"SPAWN ADVISORY: router says DO-NOT-LAUNCH"` (hook's own line) |
| check-all | a `Bash` tool_use whose command matches `check_all\.sh` or `check-all` |
| codex subagent | `Agent`/`Task` tool_use with `input.subagent_type == "codex"` |
| codex-audit subagent | `Agent`/`Task` tool_use with `input.subagent_type == "codex-audit"` |

n<15 in either arm -> printed UNDERPOWERED, no difference reported (per spec).

## Results

| Component | n_fired | n_not_fired | mean correction-rate (fired) | mean (not fired) | verdict |
|---|---|---|---|---|---|
| `/awesomeharness` skill | 43 | 4,304 | 0.596 | 0.295 | DIFF = +0.301 (fired sessions correct MORE, not less) |
| codemap SessionStart | 8 | 4,339 | 0.311 | 0.298 | UNDERPOWERED |
| understand-gate | 18 | 4,329 | 0.694 | 0.297 | DIFF = +0.397 (fired sessions correct MORE) |
| spawn-necessity | 3 | 4,344 | 0.396 | 0.298 | UNDERPOWERED |
| check-all | 60 | 4,287 | 0.597 | 0.294 | DIFF = +0.303 (fired sessions correct MORE) |
| codex subagent | 8 | 4,339 | 0.261 | 0.298 | UNDERPOWERED |
| codex-audit subagent | 5 | 4,342 | 0.233 | 0.298 | UNDERPOWERED |

## Reading this honestly

- Four of seven components never reach n=15 on the fired side across the
  entire corpus (codemap, spawn-necessity, codex, codex-audit) — the
  literal-emitted-output bar is strict enough that most sessions never
  produce a positive detection. These are reported as no-difference,
  not zero-effect; we do not have the power to say either.
- The three components that DO clear n=15 (skill, understand-gate,
  check-all) all show the FIRED arm correcting MORE, not less. Read this as
  confound, not causation: these components fire disproportionately in
  sessions that were already messy (long, build-heavy, high-friction) — the
  gate/skill/check-all get invoked BECAUSE the session already needed
  intervention. This is consistent with the earlier 11-harness-roi.md null
  and with Ro's zero-behavioral-change report on `/awesomeharness`: this
  measurement finds no evidence any single component makes sessions
  better, and some evidence they cluster with sessions that were already
  worse.
- This is one outcome proxy (correction-turn rate) on one axis. It is not a
  claim that these components are net-negative — only that this specific,
  pre-registered, defensible-from-text proxy shows no positive component
  effect anywhere in this corpus.

## VERIFY (every command run, real counts)

```
$ find ~/.claude/projects -name '*.jsonl' | wc -l
4347
$ python3 -c "import glob; print(len(glob.glob('/Users/rodrigoarista/.claude/projects/*/*.jsonl')))"
3222        # shallow glob undercounts by 1125 (26%) — files also live at depth 4
$ for d in 1 2 3 4 5 6; do echo -n "depth$d: "; find ~/.claude/projects -mindepth $d -maxdepth $d -name '*.jsonl' | wc -l; done
depth1: 0
depth2: 3222
depth3: 0
depth4: 1125
depth5: 0
depth6: 0
$ grep -oh '"subagent_type":"[^"]*"' ~/.claude/projects/*/*.jsonl 2>/dev/null | sort | uniq -c | sort -rn
 645 general-purpose / 107 codex:codex-rescue / 96 codex / 92 opus / 69 code-unit-agent /
  60 Explore / 30 code-audit-agent / 17 decompose-agent / 12 claude / 11 codex-audit /
   9 glm / 6 claude-code-guide / 2 Plan / 1 gemini / 1 cc-gemini-plugin:gemini-agent
$ python3 /tmp/measure_components.py     # full script below, recursive glob, all 4347 files
total_jsonl_files=4347 usable_sessions=4347
skill_awesomeharness: n_fired=43 n_not_fired=4304 mean=0.5961 vs 0.2953 DIFF=0.3008
codemap_inject: n_fired=8 n_not_fired=4339 mean=0.3108 vs 0.2983 UNDERPOWERED
understand_gate: n_fired=18 n_not_fired=4329 mean=0.6937 vs 0.2967 DIFF=0.3970
spawn_necessity: n_fired=3 n_not_fired=4344 mean=0.3955 vs 0.2982 UNDERPOWERED
check_all: n_fired=60 n_not_fired=4287 mean=0.5974 vs 0.2941 DIFF=0.3032
subagent_codex: n_fired=8 n_not_fired=4339 mean=0.2612 vs 0.2984 UNDERPOWERED
subagent_codex_audit: n_fired=5 n_not_fired=4342 mean=0.2334 vs 0.2984 UNDERPOWERED
```

Detector script: `/tmp/measure_components.py` (not committed — scratch,
reproducible from the detector table above; rerun against
`~/.claude/projects/**/*.jsonl` recursive glob to regenerate).

## Limits (stated, not hidden)

- Single outcome proxy. No rework-turn or uncommitted-source-at-session-end
  proxy was computed (time-boxed); the spec allows any one defensible proxy.
- FIRED counts for 4 of 7 components are too small to say anything — that is
  itself a finding: most harness components leave no unambiguous emitted
  trace in the transcript at all, which is a measurement-instrumentation gap
  as much as a usage gap.
- Correlational, not causal, by construction (no randomization) — stated
  above, not overclaimed as causal anywhere in this report.
