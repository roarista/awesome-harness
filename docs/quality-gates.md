# Quality gates (full text)

Moved verbatim from skills/awesomeharness/SKILL.md (2026-10-03, context diet U6). The skill carries a 5-line compression; this is the long form.


Every green is a claim — a passing test, an empty review, a design that "looks right". Make each earn
itself (the gates below, from Glitch Cat Club, Aug 16; each is a defect that got past someone).

- **Before a fix:** reproduce through the exact door the user used. Treat the report as a symptom and
  re-check what it claims is fine. Find the introducing commit, how long it was live, what a user sees.
  Before a rework, list every promised behaviour as proven-by-test / proven-by-history / assumed. Sweep
  for siblings — a fix closes the class or it isn't closed.
- **Attack the design first:** walk it as if built (first run, re-run, resume, retry after failure). List
  every caller by search, not judgment. Grep docs for sentences the change makes untrue. Ask what a
  death between two writes leaves and whether the next run heals it. Try disk-full, no network, slow
  machine, synced folders; real inputs (spaces, quotes, CRLF). The right rework deletes more than it adds.
- **Tests that can't lie:** one test produces the failure the way the machine does — no mocking the
  broken part. Mutation-proof: break it, watch it fail by name, revert. Explain a red before touching it.
- **Review that finds things:** no memory of writing it, then a different model, one lens each (data
  loss / races / green by construction / simpler rewrite). "No findings" lists what was attacked.
  Reproduce a finding before acting on it and before dismissing it. If a fix was wrong, stop and explain
  why every earlier gate missed it.
- **Before it ships:** walk the whole flow through the real entry point; run it twice, then inspect the
  files and data it left behind, not the output.

