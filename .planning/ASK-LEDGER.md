# ASK LEDGER — 2026-08-02 (dogfooding intervention #1)

Ro's message, decomposed. Nothing is reported as done that is not DONE or DEFERRED here.

| # | Ask (his words, compressed) | Status | Evidence |
|---|---|---|---|
| 1 | Measure the GOAL of each search, not the mechanics. "Puede que la manera en la que buscamos no sea la mejor y probablemente ese es el caso" | **DONE** | `docs/audits/2026-08-02/10-search-intent.md` — 1,456 episodes censused. Half of all episodes are the 3 expensive+failing intents (~46% of search spend, 3.3M tok wasted). Routing decision table delivered. |
| 2 | Test "por usar el harness estamos gastando MÁS y siendo MENOS eficientes" | **DONE** | `11-harness-roi.md` — CONFIRMED on cost (+23 ktok standing floor, +42% tok/turn), NOT established on efficiency. Killer null: evidenced-completion 31% vs 33% with/without. |
| 3 | Is THE PROCEDURE actually running? codex, decompose, codebase-first | **DONE** | `12-procedure-compliance.md` — codex builder has ZERO source writes ever; "main never writes" violated in 73%; check-all 32%; git-sync 9%. |
| 4 | Get hooks out of context. "No sé si se puede eso" | **DONE (built + measured)** | `13-context-diet.md` — answer is silence-by-default, not hiding. 30.2 → 8.5 ktok/session, −71.8%, measured. |
| 5 | Decompose and BUILD the findings — not more reports | **PARTIAL** | Built: the 5 hook changes in #4. NOT yet built: ASK LEDGER hook, RESTATE-AND-HOLD gate, 8-line return contract, the search routing rules, the CUT list. **This is the next session's job.** |
| 6 | "Itera tu proceso" if I think it's already done | **DONE** | Ask #1 was exactly this — my first search audit measured mechanics instead of purpose. Acknowledged and re-run. |
| 7 | GOAL: fewer tokens, more understanding. Maybe not hooks — maybe something else | **STANDING** | And the data reframed it: hooks are ~5.5% of DOLLARS (93.1% of input is cache_read at 0.1x). **The subagent fleet is 51.9% of all tokens.** The target was wrong. |

## What I got wrong and am correcting to Ro
- I reported "zero blocking-hook fires, guards are unproven." That was a **corpus artifact**:
  `irreversible-pause` fired and blocked a real destructive delete during this very wave, twice.
- I aimed the whole context-diet at hooks. Hooks are 14.7% of input tokens but only ~5.5% of
  cost. **One avoided subagent launch is worth ~22% of the entire hook prize.**

## DONE_WHEN (stated up front because Ro states one in only 6.0% of asks)
- A measured before/after on tokens, not an argument. → met for hooks (−71.8%).
- The PROCEDURE either verifiably runs or is cut. → measured; cut list produced, not yet applied.
- Hook context cost measurably lower, or a written proof it cannot be. → met.
