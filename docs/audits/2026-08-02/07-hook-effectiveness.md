# Claude Code hook-effectiveness audit

## Scope and method

Read-only forensic pass, 2026-08-02. The on-disk corpus contains 3,775 JSONL files, not the prompt's 2,868. Exact hook-command attribution is available only for the 103 transcripts (10 parent sessions plus subagents) under `~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/`; this is the corpus that actually ran this repository's hooks. The remaining global transcripts contain hook context but frequently omit the command that produced it, so assigning it to one of several hooks would be fabrication.

I streamed JSONL line-by-line. A fire is counted only when an attachment's `command` names the hook; a blocking fire requires its recorded `exitCode` to equal 2. Evidence anchors below are `basename.jsonl:line`. Source modes and registrations were read from `~/.claude/settings.json` and `hooks/` (mirrored in `~/.claude/hooks/`).

## 1. Fire-rate table

| Hook | Blocking fires | Advisory fires | Total fires |
|---|---:|---:|---:|
| main-edit-guard | 0 | 0 | 0 |
| builder-fence | 0 | 4 | 4 |
| understand-gate | 0 | 6 | 6 |
| graphify-gate | 0 | 0 | 0 |
| route-only-gate | 0 | 0 | 0 |
| now-gate | 0 | 0 | 0 |
| northstar-protect | 0 | 0 | 0 |
| northstar-inject | 0 | 10 | 10 |
| recall-inject | 0 | 0 | 0 |
| harness-enforce | 0 | 0 | 0 |
| irreversible-pause | 0 | 0 | 0 |
| reread-guard | 0 | 0 | 0 |
| filesize-cap | 0 | 0 | 0 |
| token-discipline | 0 | 0 | 0 |
| graphify-blindspot | 0 | 0 | 0 |
| session-checkpoint | 0 | 2 | 2 |
| precompact-handoff | 0 | 0 | 0 |
| caveman-discipline | 0 | 11 | 11 |
| coding-routing-guard | 0 | 186 | 186 |
| post-agent-guard | 0 | 180 | 180 |
| manifest-guard | 0 | 11 | 11 |
| phantom-edit-guard | 0 | 0 | 0 |

Direct-execution evidence: `caveman-discipline` 11 at `1a72c93c-c475-4806-8a4e-e6b6c44084cc.jsonl:5`; `northstar-inject` 10 at the same file:7; `manifest-guard` 11 at :8; `coding-routing-guard` 186 at :85; `understand-gate` 6 at :206; `post-agent-guard` 180 at :87; `builder-fence` 4 at `e19223f7-e327-41f0-8b6d-6107e2af394f.jsonl:652`; and `session-checkpoint` 2 at `94c6cfd1-0b82-40e6-a295-42e96be546c6.jsonl:1232`.

Zero means **no directly attributable execution record**, not that the settings matcher could not have invoked it. Claude commonly stores only the event-level context after multiple hooks have been composed. The source independently confirms that `main-edit-guard` defaults off and `phantom-edit-guard` never blocks; `understand-gate` defaults to `warn`.

## 2. Workaround rate for blocking guards

There were **zero recorded exit-2 hook results** in the attributable awesome-harness corpus. Consequently every blocking-guard workaround/complied/gave-up denominator is 0 and a percentage is not measurable. There is no evidence here for the claimed heredoc bypass pattern, nor evidence against it.

| Hook with blocking capability | Bypassed | Gave up | Complied | Rate |
|---|---:|---:|---:|---:|
| All 12 blocking-capable hooks | 0 | 0 | 0 | N/A (no observed block) |

This is the real finding: effectiveness cannot be inferred from a guard that did not fire. `main-edit-guard.py` itself documents Bash/heredoc bypass as a deliberate limitation, so it must not be promoted as enforcement without a separate observed-block study.

## 3. False positives

None could be verified in the attributable corpus: no recorded blocking fire means no defensible wasted-turn count. The known `understand-gate` case is corroborated by source documentation (`hooks/understand-gate.py`, header: global enforce was reverted after it denied read-only investigation spawns), but the corresponding transcript/line is not identifiable from the retained hook attachment metadata. Estimated wasted turns: **not measurable; do not substitute the source anecdote for a count.**

## 4. Advisory cost and downstream impact

Exact token cost is not recoverable from hook attachments: they contain text but no token usage. The transcript usage fields are request-level and include the entire cached prompt, so attributing cached input tokens to a particular injector would double-count. The only defensible estimate is a word-based lower bound: `caveman-discipline.sh` injects 220 words (about 293 tokens using 0.75 words/token), once per observed SessionStart; 11 observed starts therefore carry at least about 3,220 injected tokens total, or about 293/start.

| Always-on/advisory hook | Observed executions | Per-session token estimate | Changed next action? |
|---|---:|---:|---|
| caveman-discipline | 11 | >=293/start | No: 259 of 403 assistant text messages followed a tool event (64.3%), despite its zero-intermediate-prose rule. |
| northstar-inject | 10 | Not measurable from trace | Not demonstrated; no controlled injected/non-injected comparable turns. |
| coding-routing-guard | 186 | Not measurable from trace | Not demonstrated; 186 reminders did not create a traceable causal counterfactual. |
| post-agent-guard | 180 | Not measurable from trace | Not demonstrated; same 64.3% mid-tool prose proxy rejects a strong caveman-effect claim. |
| manifest-guard | 11 | Not measurable from trace | It repeatedly alerted on broad baseline drift; no downstream repair action is causally attributable. |

The remaining injector hooks have no directly attributable execution attachment in this corpus, so cost and impact are N/A. “No demonstrated impact” is deliberately not “no impact.”

## 5. Decay analysis

Not measurable per hook. Zero blocks provide no compliance trials; for advisory hooks, the transcript has no stable per-turn hook identity after context composition. The one measurable behavioral proxy (caveman) is already non-compliant overall, but lacks enough correctly segmented session turns to make an early/late causal comparison. Treat any claimed decay percentage as unsupported.

## 6. Caveman rule compliance

**35.7% compliant by the conservative transcript proxy (144/403); 64.3% non-compliant (259/403).** I counted assistant messages that contain text and immediately follow a tool-result/user tool continuation as mid-turn narrative candidates. This likely over-counts legitimate final answers, so it is a conservative proxy rather than a semantic adjudication. It nonetheless directly falsifies a claim of reliable zero-prose compliance. Evidence corpus: 103 files / 10 parent sessions; injected contract example `1a72c93c-c475-4806-8a4e-e6b6c44084cc.jsonl:5`.

## 7. Final verdict

### CUT

- `phantom-edit-guard` — source says it is observation-only and the trace shows no attributable execution/value.
- `caveman-discipline` — costs at least ~293 tokens/session-start while the behavioral proxy shows 64.3% non-compliance.
- `coding-routing-guard` and `post-agent-guard` — 366 directly observed reminders, no measurable causal effect; delete repetitive prompt tax.
- `manifest-guard` — 11 noisy broad-drift alerts with no attributable remediation; keep integrity checking only if it becomes actionable.

### DEMOTE

- `builder-fence` and `understand-gate` — advisory-only in the observed period (4 and 6 executions); retain as documentation/prompt guidance, not guards.
- `northstar-inject` — 10 starts but no causal evidence; fold its essential instruction into one concise session contract if retained.
- All zero-observation guards — do not promote or claim effectiveness until a traceable opt-in experiment produces blocks and next-action outcomes.

### PROMOTE

- None. No guard has an observed blocking fire, workaround-resistance measurement, or demonstrated downstream behavioral effect. Under delete-over-add, promotion would be evidence-free.
