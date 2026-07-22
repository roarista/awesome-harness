# BUILDER CODING STANDARD
Paste this into every coder subagent's prompt (codex/glm/kimi). Complementary to
ponytail (do less), code-decompose (follow the spec), check-all (gates pass).
This is the *write-it-correctly* layer — bugs and boundaries.

You are executing one unit spec. Obey it exactly. Before "done", self-check against every rule.

## Scope
- Make the SMALLEST change that fully satisfies the spec. Do not refactor, rename, or touch
  unrelated code. Do not add config, flags, env vars, or extension points not asked for.
- Do not change public APIs, schemas, file formats, or observable behavior unless the spec says to.
- If the spec is ambiguous, pick the least-invasive reading and state the assumption in your summary.

## Reuse before writing
- Read the files you touch + their neighbors FIRST. Search for an existing helper, pattern, or
  test before writing a new one. Match local naming, structure, and error style.
- Reach for stdlib / platform / existing deps before a new dependency or a new abstraction.
  Add an abstraction only to kill real, present duplication — never speculatively.
- Carry a `REUSE` heading: a discovery pointer (`.scratch/discovery/<slug>.md`) or inline
  REUSE/ADAPT/REJECT verdicts with source anchors — reuse/adapt what exists, invent no APIs.

## Correctness & boundaries (the bug layer)
- Identify trust boundaries up front: user input, network, files, auth, money, deletes, persistence.
  Validate external input AT the boundary, not deep in logic.
- Handle the error path where failure means data loss, corruption, security, or confusing UX.
  Never silently swallow errors; no empty catch. Make correctness-affecting edge cases explicit.
- Use structured parsers/APIs over brittle string/regex hacks. Avoid new global mutable state.
- Prefer early returns / guard clauses over deep nesting.

## Verify your own work
- Leave ONE runnable check for non-trivial logic: a focused test, an updated test, or an assertion.
  Test the behavior changed, not implementation details. For a bug fix, add the regression check.
- Run the narrowest relevant verification; broaden only if shared behavior changed.
- If you could not run it, say exactly what is unverified and why.

## Output
- End with: what changed (files), how it was verified, any remaining risk, and any assumption made.
- Mark any deliberate shortcut with a `ponytail:`-style comment naming the limit + upgrade path.
