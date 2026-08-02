# Forensic audit: economics of subagent final-message dumps

Audit date: 2026-08-02. This is a read-only analysis of Claude Code JSONL logs; no
application/source files were inspected or changed. The requested inventory said 843
subagent logs, but the live five-repository corpus had **852**: virality-pipeline 326,
Vividlist 229, Consulting 149, awesome-harness 98 (nine more than the stated 89), and
intrn 50. This report uses the live corpus, not the stale headline count.

## Method and definitions

- Every `*/subagents/*.jsonl` in those five project directories was streamed one JSON
  object at a time with Python (`open(..., errors="replace")`; malformed JSON records
  skipped). No whole JSONL was loaded or printed. All 852 had a non-empty final
  assistant text message, so the distribution sample is **n=852**.
- A return is that final assistant text block. Characters are Unicode Python character
  counts; tokens are `characters / 4`, an explicitly rough but consistently applied
  estimate. Lines are `text.count("\\n") + 1`.
- “Internal” is the sum of textual `message.content` characters across every user and
  assistant record in that subagent transcript, including its final return. It is a
  transcript-content proxy, not billed API tokens (tool payloads and hidden reasoning
  are not counted). Compression is internal text / returned text.
- For parent use, the parent JSONL is the sibling named by the subagent directory's
  shared session UUID. For each completed subagent, I selected the first *textual*
  parent assistant message timestamped after the return. This linked **850/852**;
  the other two lacked a subsequent textual parent message. The deterministic sample
  is **40** evenly spaced linked returns after sorting by subagent path (at least 30).
- Parent-use measures normalize to lowercase words of 3+ letters, remove a small
  English/Spanish stop-word set, then compare return vocabulary and return word
  3-grams with the next parent message. Vocabulary overlap is an intentionally broad
  *echo* proxy (it can include paraphrase/action terms and false positives); 3-gram
  reuse is the conservative direct-quotation proxy. It cannot prove causal use or
  semantic paraphrase, so this report does not overclaim either.
- Duplicate returns are within the same parent session only: normalized word 5-gram
  Jaccard similarity >=20%. This detects substantially repeated prose, not two
  independently worded reports reaching the same conclusion.

## 1. Return size and internal-vs-return economics

| Metric (n=852) | Median | p90 | Maximum | Total |
|---|---:|---:|---:|---:|
| Final return characters | 3,448.5 | 12,162 | 48,703 | 4,374,378 |
| Estimated final-return tokens | 862.1 | 3,040.5 | 12,175.8 | 1,093,594.5 |
| Final-return lines | 24 | 98 | 299 | 34,050 |
| Internal transcript characters | 9,339 | 16,797 | 130,523 | 8,921,953 |
| Internal / returned compression ratio | 2.17x | 38.44x | 4,345x | 2.04x aggregate |

**548/852 (64.3%)** exceed the stated 15-line report contract. The median return is
already 1.6x that ceiling, and the p90 is 6.5x it. The median agent spends about 2.17
times as much visible transcript text internally as it sends back; the high p90 ratio
also shows that some short final status messages correctly compress a long work trace.
The problem is not that every detailed investigation is wrong; it is that the return
channel regularly carries the investigation rather than a decision-ready result.

## 2. What the parent actually used

In the 40-return linked sample, the next parent message retained **24.0%** of the
return's normalized unique vocabulary on average (median 26.5%, p90 43.1%). That is a
generous upper-bound “echo” number: generic task nouns and shared paths count too.
Only **2.49%** of return word 3-grams appeared in the next parent message on average;
**23/40 (57.5%)** had any direct 3-gram reuse. By the broad >=10% vocabulary-echo
threshold, **27/40 (67.5%)** show some visible pickup; the rest had little/no textual
trace, often because the parent was waiting on other agents, synthesized several
results, or hit an API error.

The actionable conservative reading is therefore: roughly **75% of detailed wording
is dropped immediately** (and about **97.5% is not quoted verbatim**). Do not interpret
the remaining 24% as all “used”: it is an upper bound that includes coincidental shared
vocabulary. A true semantic/acted-on attribution would require an LLM/manual blinded
coding pass and should be added only if that precision is worth the cost.

## 3. Duplication and where detail went

Across 35,979 same-session return pairs, **108 (0.30%)** crossed the 20% normalized
5-gram-Jaccard threshold. At the session level, **7/20 (35.0%)** multi-subagent
sessions had at least one such duplicate pair. Exact/prose duplication is rare, but a
third of parallel sessions still has one collision—enough to justify a shared ledger
and a synthesizer that can collapse repeated findings.

**673/852 (79.0%)** returns named at least one file path or a `detail`/`finding`/
`dump`/`ledger` id (regex: path with a common artifact extension or explicit detail-id
label); **179 (21.0%)** had no such pointer and therefore inlined their only durable
detail. This is an optimistic count: a named deliverable is not necessarily a long
research dump. The desired pattern is specifically a retrievable finding id, not just
“I wrote a file.”

## 4. Cost to the main agent

Summing final-return tokens by parent session yields **21 sessions** with one or more
returns: median **31,315** estimated tokens/session, p90 **119,299.5**, maximum
**203,611.5**, total **1,093,594.5**. This is context delivered to the parent before
any repeated re-send across later turns; the effective context tax can be higher.

## 5. Fix: a ledger-first return contract

Keep `tools/finding.sh` as the single durable ledger: its append-only `record`,
`get`, `list`, and `search` semantics already provide the necessary dump storage,
retrieval, and no-deletion guarantee. Do **not** introduce a parallel database,
mulch store, or new source subsystem.

### Subagent contract

1. Stream the full investigation, commands, evidence, alternatives, and raw output to
   `tools/finding.sh record "<short task title>"`; retain the returned finding id.
   Put all citations, tables, logs, and long explanations there. Dumps are append-only
   and never deleted by the agent.
2. Return **at most 8 lines / 500 characters** to the parent:

   ```text
   verdict: PASS | FAIL | BLOCKED | FINDING
   headline: <one decision-relevant sentence>
   evidence: <up to two concrete facts, file:line / command -> exit>
   decision/next: <one action or explicit choice needed>
   risks: none | <one material caveat>
   finding: <id>  (retrieve: tools/finding.sh get <id>)
   ```

   `PASS` is permitted only with a literal verification command and exit code;
   `BLOCKED` names the missing authority/input. No greetings, process narrative,
   exhaustive file list, raw test output, or “everything I found” belongs in the
   parent return. A one-word completion is also invalid: the headline plus finding id
   is the irreducible handoff.
3. If several agents share a parent session, each records independently; the parent
   fetches only ids relevant to the decision. Repeated evidence stays in dumps rather
   than being repeated in every final.

At the 500-character cap, the observed median return falls from 3,448.5 characters to
at most 500 (about **85% less** parent input); the p90 falls by at least **96%**. The
ledger preserves the lost detail without asking the parent to carry it every turn.

### Cheap summarizer input and output

Use a cheap summarizer only after the finding is recorded. Give it: (a) the fixed
six-line contract above, (b) task objective and parent decision being served, (c) the
literal finding id plus full `finding.sh get <id>` dump, and (d) mechanical metadata
the worker captured—changed files, verification commands/exit codes, and explicit
blocked status. Tell it to emit only the capped return and never invent evidence.

It must preserve: the verdict; the single decision-changing finding; up to two cited
facts; a material failure/risk; and the retrieval id. It should drop chronology,
tool chatter, copied prompts, raw logs, all but decision-relevant alternatives, and
tables whose rows do not alter the immediate choice. If the dump has conflicting
evidence or no verification, it emits `BLOCKED`/`UNVERIFIED`, not a polished `PASS`.

This directly addresses the measured economics: the parent gets a small, inspectable
decision packet, while `finding.sh` remains the durable, append-only escape hatch for
the ~75% of wording that the next parent message does not visibly reuse.
