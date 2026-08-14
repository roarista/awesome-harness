---
name: codebase-first
description: Prove what an existing repository already provides before adding a feature, module, integration, dependency, helper, or material refactor. Return evidence-backed REUSE/ADAPT/REJECT decisions and a STOP/PLAN/BUILD gate before code-decompose.
---

# codebase-first

Run before non-trivial code changes. The output is a compact proof of the smallest missing piece, not a broad repository tour.

## Discovery ladder

Stop at the first rung that fully satisfies the goal:

1. Need: does current behavior already satisfy the request?
2. Front door: read the compact project router, current resume card, and relevant authority.
3. Map: use the injected code map and Graphify for structure/reach; use Semgrep for complete AST occurrences and `rg` for literals/history.
4. Native/platform: check whether the runtime or framework already provides it.
5. Installed dependency: inspect the manifest and live API.
6. Nearby workflow: inspect the closest active implementation and its callers.
7. Boundary/blast radius: identify consumers, errors, persistence, permissions, and files affected.
8. Probe: run the smallest read-only check that distinguishes competing assumptions.
9. Gap: name only what remains missing.

For every plausible candidate, record `REUSE`, `ADAPT`, or `REJECT` with a `file:line` or command-output anchor. Do not claim absence from a map alone.

## Gate

- `STOP`: current/native/dependency behavior covers the goal, or implementation would require an unresolved authority decision.
- `PLAN`: integration crosses multiple boundaries or changes a schema, public API, dependency, destructive migration, or authority.
- `BUILD`: candidates, consumers, boundaries, residual gap, and pre-code verification are all explicit.

For localized work, carry the evidence inline. Otherwise write `.scratch/discovery/<slug>.md` with goal, constraints, source anchors, candidate verdicts, boundary map, empirical probe, residual gap, gate, and verification.

On `BUILD`, pass only the residual gap and evidence anchors to `code-decompose`. On `STOP` or `PLAN`, write no production code.
