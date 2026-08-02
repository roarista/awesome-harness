# 13 — Context diet: can we keep hook text out of the agent's context?

Answering Ro directly: *"hay que hacer que los hooks dejen de verlos los agentes… no sé
si se puede eso."* — **Sí se puede, y ya está hecho. 30.2 → 8.5 ktok/sesión medido
(−71.8%) en este repo.** But the mechanism is not "hide the hook"; it is "make the hook
shut up unless it has something specific to say".

---

## 1. FEASIBILITY — the precise answer

**Partly, and the part that matters is fully achievable.**

Evidence, measured not assumed. Claude Code persists every hook execution to the
transcript as a `type:"attachment"` record. Over the 5 awesome-harness sessions in
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/`:

| attachment type | what produces it | permanent in transcript? | token cost |
|---|---|---|---|
| `hook_success` with `content` | hook wrote to **stdout** (`cat`, `print`) | **yes** — re-sent every later call | full text |
| `hook_success` with **empty** content | hook exited 0 and printed **nothing** | record exists, **content empty** | **0** |
| `hook_additional_context` | `hookSpecificOutput.additionalContext` (our `_hookout.inject`) | **yes** | full text |
| `hook_system_message` | `systemMessage` field | shown to **Ro**, not the model | **0 model tokens** |
| `permissionDecision: deny` | PreToolUse exit-2 / deny JSON | yes, but ~80 tok, and it **prevents** the tool's payload | tiny, net negative |

Measured proof of the zero case, straight from the corpus:

```
hookName                fires    ktok  empty  tok/fire
PreToolUse:Agent          198    85.8      6       433   <- speaks every time
PostToolUse:Agent         186     0.0    186         0   <- prints nothing: 0 tokens
Stop                       13     0.0     13         0
PreToolUse:Bash             4     0.0      4         0
```

`PostToolUse:Agent` fired 186 times and contributed **zero** `hook_success` bytes,
because that hook routes its text through `additionalContext` instead — and the
186 empty records prove the mechanism: **a hook that prints nothing costs nothing.**

So, exactly:

- **You cannot make hook text invisible-but-present.** There is no "ephemeral"
  channel to the model. Anything the model reads is a transcript entry, and the
  transcript is append-only and re-sent on every subsequent API call (mean
  amplification **390×**, audit 04 §5). Text delivered once is paid ~255 times.
- **You do not need to.** The requirement is not invisibility, it is *silence*.
  A hook costs literally zero tokens when it exits 0 with no stdout and no
  `additionalContext`. That is the whole trick.
- **One channel is genuinely free to the model:** `systemMessage` — surfaced to Ro
  in the terminal, never sent to the model. Correct home for anything that is a
  *notification*, not an *instruction*.
- **Deny beats nag.** A PreToolUse `deny` costs ~80 tokens and *removes* the payload
  it blocks. Denying one re-invocation of the awesomeharness skill trades 85 tokens
  for 13,300.

---

## 2. PER-HOOK COST CLASSIFICATION

Measured over the 5 awesome-harness sessions (the only corpus with exact
per-hook attribution). "tok/session" = corpus total ÷ 5.

### ALWAYS-INJECTS — the prize

| hook | event | fires/sess | tok/fire | **tok/session** | verdict |
|---|---|---:|---:|---:|---|
| `coding-routing-guard` | PreToolUse:Task | 38.4 | 433 | **17,160** | REWRITTEN → violation-only |
| `post-agent-guard` | PostToolUse:Task | 37.2 | 85 | **3,140** | REWRITTEN → once/session |
| `harness-enforce` | UserPromptSubmit | 17.4 | 105 | 1,830 | kept (rotates, not duplicate) |
| `recall-inject` | UserPromptSubmit | 13.4 | 103 | 1,380 | kept (content varies per prompt) |
| `northstar-inject` | UserPromptSubmit + SessionStart | ~14 | ~92 | ~1,290 | kept (NOW changes every turn) |
| `caveman-discipline` | SessionStart | 1.0 startup + 1.4 compact | 439/351 | **620** | REWRITTEN → short form post-compact |
| `manifest-guard` | SessionStart | 2.2 | 219 | 480 | should be `systemMessage` (see §5) |

### INJECTS-ON-CONDITION (already cheap)

`understand-gate` (6 fires/corpus, only on code-writing spawns) · `builder-fence`
(4) · `session-checkpoint` (2, every 150 tool calls) · `abs-path-nudge` (8 fires,
24 tok) · `voice-dictation-nudge` (gated on `$CLAUDE_SPEAK`) · `now-gate` ·
`filesize-cap` · `token-discipline` · `graphify-blindspot`.

### SILENT-UNLESS-FIRING (0 tokens at rest — nothing to fix)

`northstar-protect` · `route-only-gate` · `reread-guard` · `graphify-gate` ·
`main-edit-guard` · `phantom-edit-guard` · `precompact-handoff` · `speak` ·
`pre_compact_global` · `check-all-commit-gate` · **`irreversible-pause`**.

> `irreversible-pause` blocked a real `rm -rf` **during this very audit** (I tried to
> clear the sentinel dir). Audit 07's "zero recorded blocking fires" is a corpus
> artefact, not proof the guard is dead. It stays, untouched, per the rules.

---

## 3. WHAT CHANGED

All edits in `hooks/`, mirrored to `~/.claude/hooks/`. Originals in
`hooks/.bak-contextdiet/`. `~/.claude/settings.json` backed up to
`~/.claude/settings.json.bak-contextdiet-20260802`. **Nothing committed.**

**a) New primitive — `_hookout.once(key, session_id, ttl=0)`**
Session-scoped sentinel under `~/.claude/hooks/state/once/`. Returns True the first
time, False forever after. **Fail-open** (returns True on any error) so a broken
sentinel can never silence a guard that had something real to say. Self-reaping
after 7 days. This is the idempotency primitive the whole diet rests on.

**b) `coding-routing-guard.sh` → thin wrapper + `coding-routing-guard.py`**
Was: `cat` a 421-token routing policy on **every** Task spawn.
Now: silent unless the spawn (i) actually writes code — build verb **and** a source
file extension in the prompt — **and** (ii) is routed to something that is not the
builder/auditor. Then one 100-token line, once per session.
The killer detail: **that policy is already in the static preamble**
(`~/.claude/CLAUDE.md`, "Delegation default"). Every one of the 192 fires was
re-paying for text the model already had.
*(Implementation note: the first attempt used `exec python3 - <<'PY'`. The heredoc
occupies stdin, so the hook payload was unreadable and the guard silently never
fired. Caught by the test harness, hence the separate `.py`.)*

**c) `post-agent-guard.py` → once per session**
186 fires of byte-identical text at 35.7% measured compliance. Saying a static
reminder 186 times cannot outperform saying it once.

**d) `caveman-discipline.sh` → source-aware**
SessionStart re-fires on every compaction/resume, re-pasting the full 439-token
contract. Cold start still gets the full text; `source=compact|resume` gets a
5-line condensed form carrying the same four rules. **Measured 1756 → 459 bytes.**

**e) NEW `skill-reinject-guard.py`** (PreToolUse matcher `Skill`, newly registered)
Denies re-invocation of `awesomeharness` when its 13.3 K body is already in the
transcript, with an 85-token explanation. TTL 2 h so a genuinely long session can
reload. Only skills in `BIG_SESSION_SKILLS` are guarded; everything else passes
through untouched; fail-open throughout.

All five pass `ast.parse` / `bash -n`; `harness-enforce --selftest` and
`coding-routing-guard --selftest` both PASS.

---

## 4. MEASURED BEFORE / AFTER

Not an estimate. `\.scratch/audit/measure.py` replays the real corpus — every real
`Task` spawn through the new `verdict()` predicate, every real SessionStart through
the new source branch, with the once-per-session sentinels replayed — and prices
the new outputs at their **measured** byte counts from `.scratch/audit/hooktest.sh`.

```
corpus: 5 awesome-harness sessions, 162 Task spawns

item                                        fires B  fires A   ktok B   ktok A
routing-guard (PreToolUse:Agent stdout)         192        3     85.8      0.3
other inject:UserPromptSubmit                                    16.0     16.0
post-agent-guard                                186        3     15.7      0.3
awesomeharness skill body                                        13.8      7.0
other hook_success:SessionStart:compact                           6.9      6.9
other hook_success:SessionStart:startup                           6.0      6.0
caveman(compact)                                                  0.9      0.2
...
TOTAL (corpus)                                                  150.9     42.6
PER SESSION                                                      30.2      8.5

reduction: 71.8%   saved 21.7 ktok/session
```

Behavioral verification (`sh .scratch/audit/hooktest.sh`, bytes of model-visible output):

```
routing-guard  research spawn                        0 bytes   <- silent
routing-guard  code spawn wrong agent #1           402 bytes   <- speaks
routing-guard  code spawn wrong agent #2             0 bytes   <- once only
routing-guard  already routed to codex               0 bytes   <- silent
post-agent-guard #1 / #2 / #3              422 / 0 / 0 bytes
caveman startup / compact                  1756 / 459 bytes
skill-guard awesomeharness #1 / #2           0 / 342 bytes   <- allow, then deny
skill-guard other skill                              0 bytes   <- passthrough
harness-enforce selftest: PASS
```

**Amplified:** at audit 04's mean 390× re-send factor, 21.7 ktok/session of raw text
removed ≈ **8.5 Mtok·calls/session** of amplified cost.

**Projection to the global 61.4 ktok/session figure** (labelled as projection, not
measurement — the other projects lack per-hook attribution): the two rewritten hooks
are 20.2 K + a large share of the 31.7 K `hook_additional_context` line in audit 04
§4, plus 5.0 K of SessionStart:compact. Expected landing: **~61 K → ~30 K
tok/session**, with the skill-deny adding a further ~12 K in projects that reload
`/awesomeharness` (worst observed: 15× / 97.9 K in one virality session).

---

## 5. THE RE-INJECTION — what we control and what we do not

~48.4 ktok/session of byte-identical repeats. Honest split:

| repeat | ×/sess | tok/sess | ours? | action |
|---|---:|---:|---|---|
| awesomeharness skill body | 3.0 | 18,378 | **yes** | **fixed** — deny re-invocation (85 tok instead of 13.3 K) |
| skill_listing | 5.5 | 14,496 | **no** | Claude Code re-attaches the catalogue on every SessionStart, including post-compact. No hook event intercepts it. The **only** lever is having fewer skills — ~20 custom skills inflate it to 2.6 K/copy. |
| compact summary | 2.5 | 15,575 | **no** | Emitted by `/compact` itself. Not hook-reachable. Indirect lever: compact less often — 20 of 22 sessions compacted, **all 54 triggers `manual`**, i.e. we did it to ourselves. |
| `PreToolUse:Agent` policy | 48 | 20,235 | **yes** | **fixed** (§3b) |
| post-agent reminder | 37 | 3,140 | **yes** | **fixed** (§3c) |
| SessionStart contract on compact | 1.4 | 620 | **yes** | **fixed** (§3d) |

Two of the three big repeats are Claude Code internals. Claiming otherwise would be
fabrication. What *is* ours is now idempotent.

---

## 6. WHAT REPLACES THE HOOKS — Ro's real question

*"Tal vez no hacemos hooks, tal vez hacemos otra cosa."* Correct instinct. Ranked by
cost per unit of enforcement:

| mechanism | model tokens | enforcement | use it for |
|---|---:|---|---|
| **`deny` permission rule** in settings.json | **0** | hard, free, no prompt text | "never `git push --force`", "never edit STATE.md from main". Pure win over a guard hook that *asks*. |
| **git `pre-commit` hook** | **0** | hard, outside the context entirely | file-size caps, no-TODO scan, `check-all`. These do not belong in the model's window at all. |
| **`systemMessage`** | **0** to model | none (Ro sees it) | `manifest-guard`'s integrity alerts, telemetry, checkpoints. Notifications ≠ instructions. |
| **static preamble** (CLAUDE.md) | paid once at call 0 | advisory | anything true for the whole session. Already holds the routing policy — which is exactly why the routing hook was redundant. |
| **one-time SessionStart contract** | ~440 once | advisory | the caveman contract. Correct shape; the bug was re-firing it. |
| **checklist file read on demand** | 0 until read | advisory | `docs/CODING_AGENT_PROMPTING.md`. Link it, do not paste it. |
| **per-turn nag hook** | 400–20,000 | **35.7% compliance, 0 blocks** | almost nothing. This was the default and it was the wrong default. |
| **delete the rule** | 0 | — | legitimate, and the delete-over-add answer for anything with no measured effect. |

### Must be CUT, not rewritten

These cannot be made silent-by-default because they have no violation to detect —
they are pure standing advice, and standing advice belongs in the preamble:

1. **`manifest-guard`** — 11 broad-drift alerts, no attributable remediation. Switch
   its output from `additionalContext` to `systemMessage`: Ro sees the alert, the
   model pays 0. *(Not applied — it is Ro's integrity tripwire and changing its
   audience is his call.)*
2. **`harness-enforce`'s `[caveman]` half** — identical every turn, restating the
   preamble. The rotating half earns its keep; the caveman half does not.
3. **`phantom-edit-guard`** — self-documented as observation-only, zero attributable
   executions. Delete-over-add.
4. **The 15 zero-observation guards** — not cuttable on this evidence (absence of an
   attributable record ≠ absence of a fire; `irreversible-pause` just proved that),
   but they must not be *promoted* or claimed as enforcement either.

### Not a hook problem

The hook budget was 15.7% of raw context. The **static preamble is 13.2% and has the
worst possible amplification** (present from call 0, ×255). Audit 04 CUT 1 stands and
is bigger than everything here: a session starts at 43 K (this repo) to 103 K
(virality) tokens with zero work done, and that ~40 K spread is **per-project MCP
configuration**, not work. Enabling MCP servers per-project instead of globally is
worth more than every hook change in this document combined.

---

## 7. REVERT

```
cp ~/.claude/settings.json.bak-contextdiet-20260802 ~/.claude/settings.json
cp hooks/.bak-contextdiet/* hooks/ && cp hooks/.bak-contextdiet/* ~/.claude/hooks/
```
(then remove `coding-routing-guard.py` and `skill-reinject-guard.py`.)
`irreversible-pause` and every data-loss guard were left untouched.
