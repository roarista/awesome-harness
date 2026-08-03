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
