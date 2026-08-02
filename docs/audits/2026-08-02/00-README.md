# Harness self-audit — 2026-08-02

Nine read-only forensic audits over the real transcript corpus: **2,033 session JSONL
files + 852 subagent transcripts, ~826 MB, 103,750 records, 0 parse errors**, across
virality-pipeline (1,469), Vividlist (249), Consulting (155), awesome-harness (103),
intrn (57). Nothing here is inferred from the harness's own documentation — every number
comes from what the agents actually did.

## The five numbers that matter

| # | Finding | Report |
|---|---|---|
| 1 | **Recall injection is 88.7% noise** (11.3% precision), and even when relevant the agent re-derives the fact anyway **74.1%** of the time | 09 |
| 2 | **Completion claimed with no evidence in 66.7% of builder units**; full 5-field specs in **6.9%**; REUSE missing in **88.9%** | 08 |
| 3 | **Zero recorded blocking-hook fires** in the attributable corpus — guard effectiveness is unmeasured, not proven. Caveman compliance **35.7%** | 07 |
| 4 | **~75% of every subagent return is dropped on arrival** (2.49% quoted verbatim); median session absorbs **31 ktok** of returns, p90 **119 ktok** | 03 |
| 5 | **1 in 8 of Ro's messages exists only to stop a confidently-wrong trajectory**; he states a finish condition in **6.0%** of asks | 05 |

## The one-line diagnosis

The harness optimizes the **route** (which model, which skill, which hook) because the
route is the only checkable thing in a prompt. **DONE and PROOF are what's missing** —
so agents declare victory on a route they followed rather than an outcome they reached.

## Reports

- `01-search-behavior.md` — how agents actually locate code (4,918 Bash searches vs **1** native Grep)
- `02-wrong-answer-forensics.md` — 17 validated false-claim incidents + the tool that would have caught each
- `03-subagent-dump-economics.md` — what subagent returns cost and how little survives
- `04-context-composition.md` — what fills the main context window, at amplified cost
- `05-goal-vs-built.md` — how Ro asks vs what gets built; the drift taxonomy
- `06-tool-adoption.md` — do we ever actually use graphify / repowise / semgrep (mostly: no)
- `07-hook-effectiveness.md` — which of ~22 hooks demonstrably change behavior (none proven)
- `08-decomposition-quality.md` — spec completeness vs rework and invented APIs
- `09-memory-continuity.md` — recall precision, staleness, write-side compliance

## Honesty notes carried from the reports

- "Zero fires" for a hook means **no attributable execution record**, not proof it never ran.
- Parent-use of subagent returns (24%) is an **upper bound** built on vocabulary overlap.
- The wrong-answer corpus counts only **documented self-corrections** — a lower bound on
  the true error rate, since uncorrected false claims leave no marker.
- No causal claim that tool-using sessions ship better code; the logs are observational.
