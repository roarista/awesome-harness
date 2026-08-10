# Burn-rate audit — why usage rose

REJECTS `docs/audits/2026-08-02/13-context-diet.md` as the explanation: that
audit measured static hook injection size (a snapshot, now 2 days stale) and
says nothing about a rate change over time.

## Method

Scanned **all** `~/.claude/projects/**/*.jsonl` (recursive glob — a shallow
one undercounts by 26% per prior finding), across all 2,912 project dirs /
6,211 session files, not just this repo. Every `type=="assistant"` record's
`message.usage` in the last 30 days (2026-07-11 → 2026-08-10, machine clock)
was cost-weighted:

```
weight = input_tokens*1.0 + cache_read_input_tokens*0.1
       + cache_creation_input_tokens*1.25 + output_tokens*5.0
```

Split point: last 7 days (2026-08-03 → 2026-08-10) vs prior 23 days
(2026-07-11 → 2026-08-02). `isSidechain: true` on any message in a session
file = that session counted as subagent traffic.

Raw totals (sanity check before weighting), 30d, all projects:
`assistant usage messages=85,085`, `cache_read=6,036,649,749`,
`cache_creation=723,286,588`, `input=13,727,170`, `output=46,057,845`.

## Finding: burn rate roughly doubled

- 23-day period: weighted total **1,089,403,905.7**, daily avg **47.37M/day**
- 7-day period: weighted total **662,695,063.2**, daily avg **94.67M/day**
- **7d/23d daily ratio ≈ 2.00x**
- Per-day series (weighted, last 30d) shows the step-up is real, not one
  spike: 2026-07-20 15.3M → 2026-07-29 184.6M → 2026-08-01 195.9M →
  2026-08-05 126.8M → 2026-08-09 42.6M → 2026-08-10 43.5M (partial day).
  Peak days cluster 07-29 through 08-06.

## Attribution: main vs subagent

| period | total | main | sub | sub share |
|---|---|---|---|---|
| 23d | 1,089.4M | 634.1M | 455.3M | 41.8% |
| 7d | 662.7M | 358.8M | 303.9M | 45.9% |

Daily rates: main 27.6M/day (23d) → 51.3M/day (7d) = **1.86x**. Sub 19.8M/day
(23d) → 43.4M/day (7d) = **2.19x**. Subagents grew faster than main and share
rose 41.8%→45.9%, but subagent growth alone does **not** explain a 2x total
rise — main-session growth (1.86x) is nearly as large in absolute daily
terms (+23.7M/day main vs +23.6M/day sub, almost a dead heat).

## Attribution: by project (7d actual vs 23d daily-avg×7, i.e. "expected if flat")

| project | 7d actual | 23d flat-rate×7 | ratio |
|---|---|---|---|
| intrn | 166.8M | 19.5M | **8.6x** |
| Vividlist | 158.9M | 61.6M | **2.6x** |
| virality-pipeline | 116.9M | 111.6M | 1.05x (flat) |
| awesome-harness | 55.4M | 25.9M | 2.1x |
| Consulting | 23.7M | 34.0M | 0.7x (down) |

intrn is the single largest driver of the spike in relative terms — its
week went from near-idle to the #2 spot in raw 7-day volume. Vividlist and
awesome-harness roughly doubled too. virality-pipeline, previously the
heaviest repo, held flat — it is not what changed.

## Attribution: by model

| model | 7d actual | 23d flat-rate×7 | ratio |
|---|---|---|---|
| claude-opus-5 | 392.6M | 215.3M | 1.82x |
| claude-sonnet-5 | 162.5M | 23.5M | **6.9x** |
| claude-opus-4-8 | 102.7M | 76.9M | 1.34x |
| claude-haiku-4-5 | 4.9M | 6.4M | 0.76x |
| claude-fable-5 | 0 | 9.4M | dropped to 0 |

opus-5 remains the largest absolute cost, growing 1.82x. sonnet-5 grew
**6.9x** week over week — consistent with CLAUDE.md's "delegate builds to
codex/sonnet" policy pushing more sonnet-routed subagent work; this lines up
with the sub-share increase above.

## Top 5 individual sessions by weighted cost (30d)

1. `10096718-230…` Vividlist, opus-5, 1,817 msgs, weight 69.7M, 2026-07-27→08-04
2. `3b55b661-b1e…` intrn, opus-5, 2,145 msgs, weight 60.8M, 2026-08-04→08-10
3. `559b3d2a-443…` Vividlist, opus-5, 1,909 msgs, weight 56.7M, 2026-08-04→08-10
4. `c64a4006-e2f…` virality-pipeline, opus-5, 1,379 msgs, weight 51.9M, 2026-07-27→08-07
5. `12bbb61a-1c6…` virality-pipeline, opus-5, 1,252 msgs, weight 46.0M, 2026-07-29→08-04

These 5 sessions alone = 285.1M weighted (≈16% of the full 30-day total).
All 5 are long-running **main-session** opus-5 conversations (1,200-2,145
assistant turns each), not subagent sidechains — long single sessions are a
real, separate cost driver from the subagent-fleet theory.

## Verdict

The rise is **not** explained primarily by "more/larger subagent launches."
That effect is real (sub daily rate 2.19x vs main 1.86x, share 41.8%→45.9%)
but roughly matches main-session growth in absolute daily terms. The
dominant, better-supported explanations are: (1) the `intrn` project going
from near-idle to 8.6x its flat-rate share in one week, (2) `claude-sonnet-5`
usage jumping 6.9x week-over-week (consistent with delegated-build routing
sending more work to sonnet), and (3) several very long-running main-session
opus-5 conversations (1,200-2,100+ turns) that individually cost 46-70M
weighted tokens each.

## Re-derivation

```
30d weighted total = 1,089,403,905.7 + 662,695,063.2 = 1,752,098,968.9
23d daily avg = 1,089,403,905.7 / 23 = 47,365,387/day
7d daily avg  = 662,695,063.2 / 7  = 94,670,723/day
7d/23d ratio  = 94,670,723 / 47,365,387 = 1.999 ≈ 2.00x
```
