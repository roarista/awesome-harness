# 14 — Difficulty-based model router: research + lazy proposal (NOT deployed)

Date: 2026-08-02. Status: **proposal only. Nothing wired.**

## Ask

Ro: "podemos hacer que el modelo de estos sub agentes 1. sea de otro proveedor
(codex o gemini u otro), y 2. sea un modelo pequeño si el task no es muy difícil.
Con que no alucine. Creo que hay github repos de model routers."

## The honest finding first

**Every maintained open-source router routes API CALLS at a proxy/gateway layer.
None of them can set the Agent-tool `model` parameter at spawn time.** To use one
you route the whole session through `ANTHROPIC_BASE_URL` — which Ro's global
CLAUDE.md explicitly forbids for the main session. So the existing repos are
*inspiration*, not *installables*, for this harness.

| Project | Routes on | Needs training? | Can it set Agent `model=`? |
|---|---|---|---|
| **RouteLLM** (LMSYS) | trained win-rate classifier (matrix-factorization / BERT) over the prompt | **yes**, trained on preference data; retrain when models change | No — OpenAI-compatible proxy |
| **LiteLLM Auto Router v2** | heuristic *or* LLM classifier *or* lexical/semantic keyword rules → tiered pools | no (heuristic mode) | No — proxy `/chat/completions` |
| **vLLM Semantic Router** | embedding-based semantic category → model pool; serving-layer | no (embeddings) | No — inference gateway |
| **NotDiamond / OpenRouter Auto** | hosted quality-predictor | n/a (hosted, closed) | No — hosted API, per-call fee |
| **Morph Router** | prompt-difficulty classifier, ~430ms, Anthropic-only Haiku/Sonnet/Opus | no | No — hosted, $0.001/classification |
| **LLMRouter** (ulab-uiuc) | research library, pluggable routers | varies | No — library over API calls |

Best conceptual match is Morph Router (explainable difficulty class, Anthropic-only
tiers) — but it is hosted, paid per classification, and still an API-call router.

## The bigger honest finding: the router is mostly a distraction

Measured: the subagent fleet is **51.9% of ALL tokens**. Hooks are ~5.5% of dollars.
A router changes the *unit price* of a launch. The measured lever is the *number* of
launches. Halving launches beats downgrading every worker to Haiku, and carries no
hallucination risk. **Do the launch-count work first; the router is a second-order
optimization.**

Also measured, and a hard constraint on any router: **auditor subagents are the one
component with positive evidence** — 12% of the fleet, 39/55 rejects, 36 caught
invented APIs. A router must never downgrade an auditor. If it does, it converts our
only working quality gate into cheap noise and the net effect is negative.

## The lazy version (<=40 lines, no deps, no training)

Heuristic over features we already have at spawn time. Advisory: it prints a
recommendation the orchestrator may follow; it does not intercept anything.

```python
#!/usr/bin/env python3
"""route.py — advisory model pick for a subagent spawn. No deps, no training."""
import re, sys

WRITES  = re.compile(r'\b(implement|build|refactor|fix|patch|write|migrate|add)\b', re.I)
JUDGES  = re.compile(r'\b(audit|review|verify|design|decide|architect|red.?team|plan)\b', re.I)
LOOKUP  = re.compile(r'\b(list|count|grep|find|locate|rename|extract|format|inventory)\b', re.I)

def pick(prompt: str, files: int = 0, is_auditor: bool = False) -> tuple[str, str]:
    # HARD RULE: auditors are the only component with positive evidence. Never downgrade.
    if is_auditor or JUDGES.search(prompt):
        return "opus", "judgment/audit task — never downgraded"
    if WRITES.search(prompt):
        # code writes go to a non-Anthropic builder; big context -> gemini
        return ("gemini", "code write, wide blast radius") if files > 15 \
               else ("codex", "code write, bounded")
    if LOOKUP.search(prompt) and files <= 5 and len(prompt) < 600:
        return "haiku", "bounded lookup/mechanical edit"
    return "sonnet", "default: unclassified"

if __name__ == "__main__":
    p = sys.stdin.read()
    m, why = pick(p, files=int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    print(f"{m}\t{why}")
```

Signals used, all free at spawn time: task verb class, file count in the unit spec,
whether the unit writes source, whether it needs judgment. No classifier, no
embedding, no network call, no retraining when a model ships.

## Recommendation

1. **Cut launches.** Highest measured ROI. Do this before anything below.
2. If a router ships at all, ship it as `tools/route.py` in **advisory** mode and log
   `(picked, actually_used, outcome)` for 2 weeks before letting it decide anything.
3. Never auto-route auditors.
4. Do not adopt RouteLLM/LiteLLM/NotDiamond: wrong layer (API calls, not agent
   spawns) and adopting them means proxying the session, which is forbidden.

## Deterministic routing — actually built (2026-08-02)

Shipped `tools/route-model.sh`, not the Python heuristic sketched above: a plain
bash case/grep table, no deps, no network, no LLM call, hardcoded and readable
at the top so Ro can edit a row by hand in 10 seconds — this is the version of
"lazy heuristic" Ro actually asked for ("que se haga hard code").

Differences from the sketch: (1) prints a **NECESSITY** verdict first
(LAUNCH / DO-NOT-LAUNCH) — the sketch had no such gate, and launch *count* is
the measured lever, not model price; (2) `ROUTE_MODEL=<x>` / `--model <x>`
override short-circuits everything for a single run, **except** it is denied
for audit/judgment tasks (auditor hard-lock wins over override — the one
component with positive measured evidence is never downgradable, not even by
Ro's own override, on the theory that an accidental `ROUTE_MODEL=haiku` in env
shouldn't silently defang the only working quality gate).

Honest caveat, unchanged from above: this is advisory and second-order. It was
built and verified (13 test cases, zero network calls) but nothing currently
calls it — no hook or orchestrator invokes `route-model.sh` before a spawn.
Cutting launch count is still the higher-ROI, unshipped fix.

## Codex-first table rewrite (2026-08-02, second pass)

Ro's explicit directive: *"no me gusta Opus... queremos usar Codex más porque
nos dan más créditos"* — global CLAUDE.md's own override clause ("if Ro names
a model, use that instead") applies. New table: builds → `codex` (was already
codex for bounded targets; now also for money/auth-class builds); audits/
reviews/verify → `codex-audit` (was hard-locked `opus`, now the default,
`ROUTE_MODEL` honored with no exceptions); mechanical/enumeration → `codex`
(was `haiku`); wide-blast-radius builds and large-context/vision → `gemini`
(unchanged). Exactly ONE opus row survives, commented-in but narrow: a
second audit pass after a codex audit already PASSed something irreversible
(money/auth/credential/data-loss), triggered only by explicit phrasing
("second pass", "after codex passed", "escalate"). The old opus-default row
is kept commented out in `tools/route-model.sh` for cheap revert.

**Open risk, not buried:** opus-as-auditor was the one component with positive
*measured* evidence (12% of fleet, 39/55 rejects, 36 invented-API catches).
codex-as-auditor is now the default and is UNMEASURED. Settle it by running
both an opus audit and a codex audit against the same known-bad diff and
comparing reject rate — if codex's reject rate is materially lower, restore
the commented-out opus row.
