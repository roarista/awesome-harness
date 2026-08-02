# Wrong-answer forensics: Claude Code transcript corpus

## Executive finding

The dominant failure was **claiming that a code path, subsystem, or field was absent when it was actually present** (5 of 17 validated incidents). The recurring mechanical cause was drawing a global conclusion from a narrow search or an architectural summary without reopening the owning file/module. The cheapest prevention is not a new agent: make an absence claim only after a scoped `rg`/Semgrep enumeration and re-read the owning file; use graphify only for the depth-1 symbol blast radius after the symbol is known.

This is a high-precision forensic sample, not a claim that all 580 lexical hits are failures. It contains only incidents where a real assistant transcript explicitly retracts/corrects a codebase-related assertion, or a user correction is followed by a grounded assistant correction. The raw scan deliberately rejects appearances of marker words inside injected skill instructions, task notifications, copied summaries, and ordinary apologies.

## What was sampled

On 2026-08-02, a streaming Python JSONL scan (one physical line decoded at a time; no whole transcript was read) covered every `*.jsonl` below the five requested project directories:

| Repository directory | Main-session files | Subagent files | Notes |
|---|---:|---:|---|
| `-Users-rodrigoarista-Downloads-virality-pipeline` | 1,143 | 326 | largest source of validated codebase corrections |
| `-Users-rodrigoarista-Downloads-Vividlist` | 20 | 229 | scanned; no high-confidence incident selected |
| `-Users-rodrigoarista-Downloads-Consulting` | 6 | 149 | selected factual/schema/workflow corrections |
| `-Users-rodrigoarista-Downloads-awesome-harness` | 5 | 94 | selected tool/harness corrections |
| `-Users-rodrigoarista-Downloads-intrn` | 7 | 50 | scanned; no high-confidence incident selected |
| **Total** | **1,181** | **848** | **2,030 files; 103,750 JSONL records; 826,225,518 bytes; 0 parse errors** |

The directory counts are the current on-disk counts, not the headline counts in the request. The lexical pass found 580 hits across the supplied Spanish/English markers. Manual validation produced 17 codebase incidents. “Line” below is the JSONL physical-line number, so it is an approximate but directly reproducible reference: `python3` can stream to that line; do not `cat` the file.

## Taxonomy and prevention

| Failure mode | Validated incidents | What the evidence shows | Tool most likely to have caught it |
|---|---:|---|---|
| (a) Invented API/function/parameter/field | 2 | Rules were authored against artifact fields that did not exist; a protocol implementation made an unsupported assumption. | Re-reading the schema/file (and a small executable positive-control test) |
| (b) Claimed something absent when it exists | 5 | Retrieval/S2 paths were described as dead or absent despite live implementations or a renamed module. | Plain Grep, then re-reading the file |
| (c) Claimed something exists when it does not | 1 | A report/path was represented as delivered although the requested handoff had not actually been surfaced. | Nothing purely structural; delivery check / user-visible artifact verification |
| (d) Right symbol/name, wrong module/owner | 2 | A live component was attributed to the wrong pipeline/layer; an issue was attributed to the wrong product surface. | Graphify affected after identifying the symbol, plus re-reading the owner |
| (e) Incomplete enumeration | 1 | A list of “all” relevant processing paths omitted a live consumer. | Semgrep for structural variants; plain Grep for prose/config variants |
| (f) Stale belief after edit/branch state changed | 2 | A proposed DB fallback and a “preexisting failures” narrative survived after the underlying branch/test facts had changed. | Re-reading current file/branch state; `git`/test rerun |
| (g) Claimed verification it never ran (or treated a prior assertion as verified) | 2 | “Known/preexisting” test failures and an implementation status were stated without the decisive current check. | Nothing automatic proves a human did a check; require command output/exit code in the claim |
| (h) Misread the user’s goal/model | 2 | The model conflated what the user wanted delivered with an internal spec/path, and confused a business role/tenant premise. | Nothing; reflective restatement and user confirmation |
| **Total** | **17** | Categories are exclusive at the incident level; “best tool” is the primary countermeasure, not a promise. | |

Two important negatives: **repowise** was not the primary preventative tool for any validated incident; it is a risk/dead-code aid, not evidence for current symbol existence. **Nothing** is the honest answer for the goal-misread and unexecuted-verification variants unless the workflow forces an explicit confirmation or command receipt.

## Top 10 most expensive incidents

“Expensive” here means likely to block a production pipeline, cause a wrong implementation/architecture decision, waste a long investigation, or misdirect a client deliverable—not a measured dollar amount. Quotations are verbatim excerpts from the indicated JSONL message; ellipses only omit unrelated surrounding text.

1. **Invented artifact fields that would permanently block a verifier pipeline** — category (a); prevention: **re-read schema + executable positive control**.

   - False claim: “**Constituciones de verificadores v1 committeadas (`c706690e`) — 29 reglas con evidencia citada.**”
   - Correction: “**18 de las 19 reglas bloqueantes apuntaban a campos que no existen en ningún modelo.**”
   - Trace: `virality-pipeline/a891d580-38f5-421b-84b3-2e5725ec3a34.jsonl`, assistant lines **before 2137** and **2137**.

2. **Declared live format retrieval absent/dead** — category (b)/(e); prevention: **plain Grep, then re-read the consumer**.

   - False claim: “Te dije ‘**cero retrieval bajo `src/originated/`**’.”
   - Correction: “**Estaba mal.** `format_library/consumers.py::apply_top_format` llama a `retrieve_formats`...”
   - Trace: `virality-pipeline/c64a4006-e2f1-4260-b7d0-1cd5b28f84d6.jsonl`, assistant line **9**.

3. **Proposed a destructive/wrong fallback from the wrong root-cause theory** — category (f); prevention: **re-read current branch/file state**.

   - False claim: “Yo te propuse ‘**fallback a la fila del DB**’.”
   - Correction: “**Habría sido un parche equivocado**, porque la fila del DB no guarda `grammar`...”
   - Trace: `virality-pipeline/c64a4006-e2f1-4260-b7d0-1cd5b28f84d6.jsonl`, assistant line **238**.

4. **Declared S2 absent although it had been renamed and was complete** — category (b)/(d); prevention: **plain Grep and re-read module ownership**.

   - False claim: “**El S2 no está en el camino.** ... `src/s2/` ...”
   - Correction: “**El S2 sí existe, y está completo** `src/strategy_folded/` (lo que era `src/s2/`)...”
   - Trace: `virality-pipeline/c64a4006-e2f1-4260-b7d0-1cd5b28f84d6.jsonl`, assistant lines **251** and **456**.

5. **Treated nine failing tests as permanently ‘preexisting’ instead of diagnosing them** — category (g)/(f); prevention: **rerun tests and inspect the failing fixtures**.

   - False claim: “Suite: **9 falladas / 3047 pasadas — las 9 de siempre.**”
   - Correction: “**nunca fueron un bug. Eran fechas podridas.** ... nadie las había diagnosticado nunca.”
   - Trace: `virality-pipeline/c64a4006-e2f1-4260-b7d0-1cd5b28f84d6.jsonl`, assistant lines **2227** and **2568**.

6. **Misdiagnosed a vendor outage as lack of inventory** — category (c)/(g); prevention: **re-read stored request/response evidence; no graph tool needed**.

   - False claim: “The ad library is not ‘**vendor has no inventory**’...”
   - Correction: “... it’s **vendor-broken, and I was wrong**. Credits are ruled out by measurement, not by assumption...”
   - Trace: `virality-pipeline/12bbb61a-1c66-46d9-ac24-ddea01b06dbc.jsonl`, assistant line **4160**.

7. **Asserted the wrong capability boundary for remote control** — category (b)/(d); prevention: **re-read config and trace the owning mechanism**.

   - False claim: “I retract ‘**background/agent sessions can’t be remote-controlled**’...”
   - Correction: “**you’re right, I was wrong** ... I found it in your config.”
   - Trace: `awesome-harness/e19223f7-e327-41f0-8b6d-6107e2af394f.jsonl`, assistant line **1823**.

8. **Conflated two S1 documents and failed to hand over the requested one** — category (h)/(c); prevention: **nothing structural; explicitly restate the requested deliverable and open it**.

   - False claim: “I’d been **conflating them**.”
   - Correction: “**You were right that I never handed it over. Two file paths**...”
   - Trace: `virality-pipeline/12bbb61a-1c66-46d9-ac24-ddea01b06dbc.jsonl`, assistant line **4571**.

9. **Wrongly denied the accessible Gemini route** — category (b); prevention: **re-read the actual credential/config path and run a minimal probe**.

   - False claim: “yo estaba equivocado en decirte que **no** [funcionaba].”
   - Correction: “**Gemini — sí funciona, y es gratis** ... `cloudcode-pa.googleapis.com/v1internal:generateContent`...”
   - Trace: `virality-pipeline/a891d580-38f5-421b-84b3-2e5725ec3a34.jsonl`, assistant line **3368**.

10. **Misidentified the client-side business/tenant premise** — category (h); prevention: **nothing automatic; ask/confirm the premise before architectural conclusions**.

   - False claim: “**tu papá SÍ es socio de Clyde**” is explicitly introduced as “**Mi error**”.
   - Correction: “Lo tengo ya corregido en memoria con la evidencia que ustedes fotografiaron...”
   - Trace: `Consulting/c52f762c-10d5-4c53-bdc0-dd97fe0cda78.jsonl`, assistant line **1320**.

## Practical control changes

1. Treat “does not exist,” “dead,” “all places,” “only importer,” and “no callers” as **claims requiring a receipt**: the exact `rg`/Semgrep command, scope, and hit count. A bare prose conclusion is not enough.
2. Before changing a schema-facing verifier, read the concrete model and add one tiny positive control that instantiates/uses every referenced field. This would have stopped the 18/19 phantom-field incident before implementation.
3. For a known symbol, run **graphify affected** only for its depth-1 blast radius; do not use it to establish global absence. Use Semgrep when syntax variants make Grep non-exhaustive.
4. Do not let “preexisting” persist across a turn. It must carry a dated test command, result, and owner; otherwise rerun and diagnose it.
5. Separate fact claims from user-goal claims in final responses: “I verified X by Y” and “I understand you want Z.” The latter needs an explicit confirmation when the choice affects the deliverable.

## Limits

This report measures documented self-correction, not the true error rate. Some false claims were never corrected, while some corrections are only in user turns or collapsed summaries. The 17 incidents therefore form a conservative lower bound. The source scan was exhaustive over the five current directories, but the high-confidence classification was intentionally manual and sampled; it does not pretend that every lexical apology was a codebase error.
