# What agents are actually trying to LEARN when they search — intent, success, and the method that fits

Companion to `docs/audits/2026-08-02/01-search-behavior.md`. That audit measured **how** we search
(4,918 Bash `rg`/`grep`/`find` vs one native Grep; 72.31% full-file Reads; 380 wasteful re-reads;
median 9 tool calls before the first edit; 229 flailing episodes). Ro's objection was that this is the
wrong question: *"lo que yo quería es que veas cómo buscamos, pero CUÁL ES LA META de esa búsqueda."*
This document answers the meta question — per **intent**, does the search succeed, what does it cost,
and where is grep structurally the wrong instrument.

---

## 0. Sample, method, and honesty boundaries

**Corpus (census, not a sample).** Every JSONL under the five project directories in
`~/.claude/projects/` on 2026-08-02: **2,054 transcripts** (1,199 top-level + 855 `subagents/`) across
virality-pipeline, Vividlist, Consulting, awesome-harness, intrn. Files were streamed line-by-line with
`python3`; no file was ever `cat`-ed or whole-loaded.

**Episode definition (the unit of analysis).** An *episode* = one search call plus every tool call that
follows it, until one of: (a) an `Edit`/`Write` (the agent **acted**), (b) a user message (**topic
change**), (c) a subsequent search sharing **no identifier token** with the episode's prior searches
(**topic change** — this is what stops one session collapsing into one giant episode), (d) end of
session. Searches that share tokens are folded into the *same* episode, so a 21-query hunt for one
answer counts once, with `nsearch=21`.

**Result: 1,456 episodes** over 4,424 search calls. This is 7× the 200-episode floor the brief asked
for, and it is a census rather than a sample, so no sampling error applies.

Scripts (kept, not shipped): `$CLAUDE_JOB_DIR/tmp/episodes.py`, `agg.py`.

**Measured vs inferred — stated once, honestly.**

| Signal | Status |
|---|---|
| Episode counts, `nsearch`, tool calls, result bytes/tokens, outcome terminator | **Measured** (exact, from the transcript) |
| Empty / broken / near-empty results and their retry-or-not | **Measured** (exact string match on the tool result) |
| Compound-command segment counts and empty sub-sections | **Measured** |
| **Intent label** | **Inferred** — regex classifier over the command shape + the assistant's preceding text. Validated by hand-reading 40 randomly sampled episodes (seed 7) and one full re-write of the taxonomy after the first pass produced a 40% "unclassified" bucket. Expect ~10-15% label noise. |
| **Success** | **Inferred** from what happened next (definition in §2). It is a behavioral proxy, not a ground-truth grade. |
| Rework rate | **Weak inferred** — 875/1,815 edits (48.2%) touched a file already edited in that session. Multi-hunk edits inflate this; treat as directional only. |

Token counts are `ceil(utf8_bytes/4)` of captured tool-result text — estimates, not billing tokens.

---

## 1. The intent taxonomy (measured frequency)

The seeded categories from the brief mostly survived, but **the data forced three changes**, and these
changes are themselves findings:

1. **"Recover a name the agent half-remembered" is not a rare edge case — it is the single largest
   intent (20.8%).** It shows up as alternation-hedged patterns (`grep "a\|b\|c\|d"`) where the agent
   is guessing three-to-eight spellings of one concept at once.
2. **"Locate a definition" is much smaller than expected (7.6%)** because most of what looks like
   definition-hunting is actually **targeted-slice-read (11.1%)**: using `grep -n X -A40 file.py` or
   `sed -n '445,475p'` as a *navigation* tool, because native `Read` is too coarse and re-reads cost
   too much. This is a real, distinct, and *highly successful* intent.
3. **"Understand control flow" did not survive as its own class** — it never appears as a discrete
   search; it is executed as a chain of targeted-slice-reads. Its cost is hidden inside other rows.

| # | Intent | What question the agent is answering | Episodes | Share |
|---|---|---|---:|---:|
| 1 | `name-recovery-hedge` | "What is this thing *called*? I'll guess 3-8 spellings at once." | 303 | 20.8% |
| 2 | `enumerate-occurrences` | "Where are ALL the places that touch X?" | 234 | 16.1% |
| 3 | `history/prior-art` | "Has this been done/changed before? What did the diff do?" | 229 | 15.7% |
| 4 | `check-existence` | "Does this file/module/test exist at all?" | 196 | 13.5% |
| 5 | `targeted-slice-read` | "Show me the 40 lines around X in *this* file." | 162 | 11.1% |
| 6 | `locate-definition` | "Where is X defined?" | 110 | 7.6% |
| 7 | `diagnose-failure` | "Why did this fail? (from a symptom/log/test output)" | 95 | 6.5% |
| 8 | `other-symbol-lookup` | Residual, unclassifiable | 43 | 3.0% |
| 9 | `verify-change-landed` | "Did my edit actually take?" | 35 | 2.4% |
| 10 | `blast-radius` | "What breaks if I change X?" | 33 | 2.3% |
| 11 | `config-value-lookup` | "What is the current value / default of this knob?" | 16 | 1.1% |
| | **Total** | | **1,456** | 100% |

**The most important structural fact in this table:** `blast-radius` — the intent with the highest
consequence when wrong — is **2.3% of searches**. Agents almost never ask "what breaks?" before editing.
They ask "what is this called?" nine times more often. That is not a search-quality problem; it is a
*search-agenda* problem, and no better grep fixes it.

---

## 2. Success rate per intent — the core deliverable

**Success definition (behavioral proxy, applied uniformly).** An episode is **FAILED** if any holds:
- `nsearch >= 3` — the agent had to re-query three or more times on the same tokens (flailing); or
- every search in the episode returned empty **and** the agent did not go on to edit.

It is **SUCCEEDED** if it terminated in an `Edit`/`Write` with `<3` searches, or the first search
returned content and the agent proceeded to read/act without re-querying. Everything else is failed.
This is deliberately generous to grep: a single search followed by a confident read counts as a win.

| Intent | n | **Success** | Flail (≥3 searches) | Ended in an edit | Median calls | Median tokens | P90 tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| `verify-change-landed` | 35 | **77.1%** | 8.6% | 57.1% | 3.0 | 390 | 3,214 |
| `targeted-slice-read` | 162 | **69.8%** | 19.1% | 38.3% | 4.5 | 1,886 | 7,328 |
| `config-value-lookup` | 16 | 62.5% | 31.2% | 37.5% | 7.0 | 3,287 | 6,209 |
| `other-symbol-lookup` | 43 | 60.5% | 34.9% | 34.9% | 5.0 | 3,412 | 25,966 |
| `history/prior-art` | 229 | 59.4% | 18.8% | 20.5% | 4.0 | 1,242 | 9,678 |
| `check-existence` | 196 | 51.5% | 37.2% | 32.1% | 8.0 | 3,107 | 14,944 |
| `locate-definition` | 110 | 50.0% | 30.9% | 27.3% | 5.0 | 2,060 | 11,146 |
| `diagnose-failure` | 95 | 49.5% | 35.8% | 24.2% | 6.0 | 1,199 | 5,020 |
| `blast-radius` | 33 | **48.5%** | 36.4% | 30.3% | 6.0 | 1,223 | 9,103 |
| `enumerate-occurrences` | 234 | **41.9%** | 40.6% | 27.4% | 6.0 | 2,248 | 19,085 |
| `name-recovery-hedge` | 303 | **46.2%** | 38.6% | 35.3% | 6.0 | 3,312 | 18,533 |
| **All** | **1,456** | **~52%** | 33.6% | 30.7% | 5.0 | 2,100 | 15,000 |

**Read the top and the bottom of that table together.** The two intents grep is *actually good at* —
"show me lines N-M of a file I already named" and "did my edit land" — are the two with the highest
success and the lowest cost. Every intent that requires grep to **resolve something** (a name, a
complete set, a definition, a dependency) sits at or below 50%.

Episode outcomes overall: 642 topic-change, 447 acted-edit, 361 end-of-session, 6 long-run.
Flail-depth distribution (`nsearch`): 720 episodes at 1, 274 at 2, 112 at 3, 87 at 4, 55 at 5, 41 at 6,
25 at 7, and **142 episodes at 8 or more searches on the same question**.

---

## 3. Cost per intent, and the expensive-AND-failing intersection

Total across the corpus: **12,117 tool calls and ~7.2M estimated tokens** spent inside search episodes.

| Intent | Total tokens | Total calls | Failed episodes | **Tokens burned in failed episodes** |
|---|---:|---:|---:|---:|
| `name-recovery-hedge` | 1,913,481 | 2,752 | 163 | **1,305,650** |
| `enumerate-occurrences` | 1,511,203 | 2,150 | 136 | **1,198,908** |
| `check-existence` | 1,246,647 | 1,986 | 95 | **787,678** |
| `history/prior-art` | 794,356 | 1,595 | 93 | 406,452 |
| `targeted-slice-read` | 502,624 | 1,032 | 49 | 189,945 |
| `locate-definition` | 461,222 | 852 | 55 | 360,848 |
| `other-symbol-lookup` | 354,958 | 418 | 17 | 177,071 |
| `diagnose-failure` | 190,474 | 744 | 48 | 134,302 |
| `blast-radius` | 116,747 | 271 | 17 | 98,142 |
| `config-value-lookup` | 63,161 | 164 | 6 | 30,809 |
| `verify-change-landed` | 42,006 | 153 | 8 | 15,781 |

### The intersection — this is the whole answer to Ro's question

**Three intents are simultaneously the most expensive and the least successful, and together they burn
~3.3M tokens on episodes that did not resolve — 46% of all search spend in the corpus:**

| Rank | Intent | Share of episodes | Success | Wasted tokens |
|---|---|---:|---:|---:|
| 1 | **`name-recovery-hedge`** | 20.8% | 46.2% | 1.31M |
| 2 | **`enumerate-occurrences`** | 16.1% | **41.9%** (worst) | 1.20M |
| 3 | **`check-existence`** | 13.5% | 51.5% | 0.79M |

A fourth, `blast-radius`, is cheap only because it is almost never attempted (2.3%); at 48.5% success it
belongs in the same failure family and would join the top of this list the moment agents actually
started asking it.

`targeted-slice-read`, `verify-change-landed` and `history/prior-art` are the opposite corner: cheap,
successful, and grep/git are the *correct* tools. **Do not touch them.**

---

## 4. THE MISMATCH — the specific property grep lacks, per failing intent

### 4.1 `enumerate-occurrences` (41.9% success, worst) — grep has **no notion of completeness**, and we cap it ourselves

Measured: **71.8% of enumeration episodes piped the search into `| head -N`.** Success with `| head`
was **39.3%**; without it, **48.5%**. We ask "where are ALL the places?" and then explicitly instruct
the tool to answer only the first 20-60. The result is a list the agent cannot distinguish from a
complete one, because `head` truncates silently — there is no "…and 340 more".

Second missing property: **no structural awareness.** `grep -rn "room_boundary"` matches the string in a
comment, a docstring, a test fixture, a `.venv` vendored copy, and a real call site with equal weight,
and it cannot match "every call site of this function regardless of how it is spelled at the call".

> **Evidence — `Vividlist/.../subagents/agent-af543470fc35a169e.jsonl:7`.**
> `grep -rn "room_boundary" --include=*.py . | head -60` → **42 bytes** (broken, see §4.4).
> `:11` re-runs the *identical* query with different plumbing → 9,082 bytes.
> `:15` narrows to `'"room_boundary"'` in `services/` → 2,441 bytes.
> `:17` gives up on the string and hedges five different function names.
> Twelve searches later (`:67`) it is reading `sed -n '115,200p'`. The episode never produced a
> defensible "these are all the places", and ended with `end-of-session` — no edit.

### 4.2 `name-recovery-hedge` (20.8% of all searches, 46.2%) — grep has **no vocabulary; it cannot tell you what exists**

This intent exists *only because* grep requires you to already know the token. The agent's actual
question is "what is the identifier called?", and the only way to ask grep that is to guess. Measured:
83.2% of these episodes used `| head`, and the median episode costs 3,312 tokens across 6 calls.

> **Evidence — `Vividlist/.../subagents/agent-aae95290234035b75.jsonl:23-58`.** Nine searches, one
> question ("what is the module/flag actually named?"): a shell `for` loop over seven guessed module
> names → 441 bytes; then five guessed function names (`route_package|build_manifest|render_pdf_pages|
> rank_floor_plan_pages|is_floor_plan_page`) → **42 bytes, nothing**; then a fallback to
> `grep -n "^def \|^class "` on three files to *read the vocabulary out of the source* — which is the
> agent hand-building the symbol index that `graphify-out/graph.json` already contains.
> Then the same dance again for `enable_pdf_ladder` vs `enable-pdf-ladder`.

The lacking property is precise: **grep is an exact-string oracle over an unknown vocabulary.** There is
no fuzzy match, no ranking, no "did you mean", no snake/camel/kebab equivalence, and no rename history —
so a symbol renamed three commits ago is indistinguishable from a symbol that never existed.

### 4.3 `check-existence` (13.5%, 51.5%, median **8 tool calls**) — grep **cannot prove a negative**

An empty result has at least six causes that are byte-identical in the transcript: the thing does not
exist; it exists under another name; it exists in a file type excluded by `--include`; it exists outside
the `cd`'d directory; the pattern had a regex/escaping bug; or **the command never ran** (§4.4). Since
the agent cannot discriminate, it does the only rational thing — searches again — which is exactly the
37.2% flail rate and the 8-call median, the highest of any intent.

### 4.4 The critical failure class: **silent negatives the agent believed** (measured, exhaustive)

Two distinct mechanisms, both measured across all 4,424 searches:

**(a) Shell-level non-execution masquerading as "no matches."** 457 searches (10.3%) returned <80 bytes.
The breakdown of those results:

| Result string | Count | What actually happened |
|---|---:|---|
| `(Bash completed with no output)` | 96 | genuine empty **or** silent failure — indistinguishable |
| `(eval):1: no matches found: --include=*.py` | 90 | **zsh glob-expanded `--include=*.py`; grep never ran** |
| `…--include=*.ts` / `*.md` / `*` | 39 | same bug |
| `Exit code 1` + `no matches found` / `== not found` | 8 | same family |
| `Exit code 143 / timed out after 2m` | 8 | search killed, no result |

**137 searches (3.1% of all searches in the corpus) failed because of unquoted `--include=*.py` under
zsh.** The tool returned a message that reads, to a fast-moving agent, like "nothing in this codebase."

**(b) Believed vs retried.** Of the **294** broken/near-empty searches, **245 were retried** with
overlapping tokens (the agent noticed) and **49 were not — the agent accepted a negative from a command
that had not executed or had produced nothing verifiable.**

> **Flagged episodes (all 49 are in the script output; the clearest):**
> - `Vividlist/.../agent-ace69b905ca973a13.jsonl:5` — `grep -rn "missing_world_plan_scale" --include=*.py . | head -30` → `(eval):1: no matches found: --include=*.py`. **Not retried.**
> - `…ace69b905ca973a13.jsonl:7` — same session, next search, `scale_m_per_unit`, same zsh failure. **Not retried.** Two consecutive "this symbol doesn't exist" conclusions from two commands that never ran.
> - `Vividlist/.../agent-aea8b924b51645e3b.jsonl:7` — `meters_per_length_unit|METERS_PER|_runner_scale_m_per_unit --include=*.py` → same failure, not retried.
> - `Vividlist/10096718-…jsonl:1350` — `OCG_FILTER_LOW_YIELD_FRACTION|low_yield|wall_ocg_filter --include=*.py` → same failure, not retried.
> - `Vividlist/.../agent-adbc9457ca02dc24c.jsonl:54` — `grep -n "GEOMETRIC_INFERENCE" schemas/package_to_render/models.py` → `(Bash completed with no output)`, not retried.
> - `Vividlist/.../agent-a3ba5680d53d130fe.jsonl:92`, `…agent-a971051eeb3181a0c.jsonl:41`, `…agent-a5df07d0c3a2ae1d4.jsonl:76` — same shape.

**(c) The sub-section blind spot — the largest silent-empty class.** 39.1% of search commands (1,710 of
4,373) bundle **two or more** searches into one call with `echo ===` separators. Of the 2,006 commands
that used separators, **634 (31.6%) returned at least one completely empty section** — i.e. **14.5% of
all searches in the corpus contained a sub-query that found nothing, buried inside output that looked
successful.** A single-search empty result is at least visible; an empty *third section* of a
five-section compound command reliably is not.

> **Evidence** — `virality-pipeline/a891d580-…jsonl:2782`, `:2789`, `:2845`, `:2563`, `:2632`
> (five in one session), each a multi-section compound where one `grep` produced nothing and the
> non-empty neighbors carried the response forward.

### 4.5 `blast-radius` (48.5%) — grep has **no call graph and cannot see dynamic dispatch**

Grep answers "where does this string appear", never "what transitively depends on this". It cannot
follow re-exports, cannot resolve a method through an interface, and cannot see a call made through a
registry/dict dispatch or a dynamically-built module name.

> **Evidence — `Vividlist/.../agent-aae95290234035b75.jsonl:23`.** The agent literally writes a bash
> `for m in format_router manifest_parser pdf_sheet_image …; do grep -rn "package_to_render.$m"; done`
> — a hand-rolled, hand-enumerated, string-matched import graph over seven modules it had to name
> itself. 441 bytes back. This is a call-graph query being simulated in shell, and the enumeration is
> only as complete as the agent's memory of the module list.

### 4.6 Where grep is genuinely right — say it plainly

`targeted-slice-read` (69.8%) and `verify-change-landed` (77.1%) are the two highest-scoring, cheapest
intents in the corpus, and `history/prior-art` (59.4%, 4 calls, 1,242 tokens) is third. For "print lines
around a known anchor in a named file", "confirm a string I just wrote is present", and "what did this
commit change", `grep`/`sed`/`git` are correct and nothing in our toolbox beats them. **Any proposed
method that routes these away from grep is a regression.**

---

## 5. What would have worked — from tools we already have and have measured

| Failing intent | Better instrument | Why it fits the *property* grep lacks | Honesty check |
|---|---|---|---|
| `enumerate-occurrences` | **`semgrep --lang <l> -e '<pattern>'`** | Structural, AST-level, **exhaustive by default** (no `head`, no truncation), and it will not match comments/strings. Measured on this repo: `semgrep --lang python -e 'def $F(...): ...' --quiet tools/` returns in **1.6s**. Prior measurement: 13/13 recall in ~1.3s. | Only for languages semgrep parses, and only for structural patterns — not for prose/markdown/config sweeps, where `rg` remains correct. |
| `name-recovery-hedge` | **Step-0 vocabulary dump from `graphify-out/graph.json`**, then query with tokens *from* the vocab | Converts "guess the name" into "read the name off a list". The graph is 714 nodes with `label` + `id` + `source_file` + `source_location` for this repo — exactly the symbol index the agent was hand-building with `grep -n "^def "`. | Only in repos with a graph. In repos without one, `rg -o '\bdef \w+' | sort -u` (a one-shot local vocab dump) is the poor-man's substitute — still strictly better than serial guessing. |
| `check-existence` (proving absence) | **`semgrep`** for code presence (exit code is meaningful); **`repowise dead-code`** for "is this reachable/used at all"; and for the shell layer, a **verified-empty protocol** (§6) | The failure is not the tool, it is that our invocation cannot distinguish "absent" from "did not run". Any method that returns a *count* plus a *scope statement* beats one that returns silence. | `repowise dead-code`/`risk` are CLI and work in all repos; `repowise` MCP is indexed only where a Repowise index exists. |
| `blast-radius` | **`graphify affected "<node_id>" --depth 1`** | True reverse traversal over `calls/references/imports/inherits/…`. Measured live: `graphify affected "hooks_pre_tool_use_command_from" --depth 1` → `decision() [calls] codex/hooks/pre_tool_use.py:L130`, in **0.10s**. | **Load-bearing gotcha, reproduced live:** `graphify affected "northstar-inject" --depth 1` (a plausible *label*) → `No affected nodes found.` — a silent false negative. **You must pass the node `id`**, not the label or filename. Depth-2 precision is ~30%; use `--depth 1`. |
| `locate-definition` | **`graphify explain "<node>"`** or the graph's `source_file`+`source_location`; else `semgrep -e 'def $F(...)'` | The graph stores the definition site as data (`source_location: 'L50'`); no pattern-guessing required. | For a symbol you can spell exactly, plain `rg -n "def name"` is already fine and cheaper — this only wins when the name is uncertain. |
| `diagnose-failure` (49.5%) | **Nothing we have.** | Honest answer. The bottleneck is not locating the symptom text — it is causal reasoning from symptom to cause. `git log -S<symbol>` / `git bisect` help *only* when the failure is a regression with a known-good baseline. The 35.8% flail rate here is reasoning cost, not search cost, and a better index will not move it. | Stated as a non-recommendation deliberately. |
| `history/prior-art`, `targeted-slice-read`, `verify-change-landed` | **Keep `git log --grep` / `git diff` / `grep -n -A/-B` / `sed -n`.** | Already the best fit; 59-77% success at the lowest cost per episode in the corpus. | No change proposed. |

---

## 6. THE PROPOSED SEARCH METHOD — routing decision table

The method is not "stop using grep". It is: **name the intent before you type the command, route on the
intent, and never accept an empty result you cannot prove.**

### 6.1 Routing table

| # | Your intent (state it) | Run FIRST | Proof the answer is real | STOP when |
|---|---|---|---|---|
| 1 | "What is this called?" (any uncertainty about the identifier) | **Step 0 — dump the vocab.** `python3 -c "import json;[print(n['id'],'|',n['label'],'|',n['source_file']) for n in json.load(open('graphify-out/graph.json'))['nodes']]" \| rg -i '<concept>'` — or, no graph: `rg -o '\b(def\|class\|function\|const) \w+' -r '$0' --no-filename \| sort -u \| rg -i '<concept>'` | You have a **literal token copied from the vocab dump**, not typed from memory | You hold an exact identifier. **Never** issue a 3+-alternation guess-grep. If the vocab dump has no match, the concept is named something else — widen the concept word, do not widen the pattern. |
| 2 | "Where are ALL the places?" | `semgrep --lang <lang> -e '<structural pattern>' <scope>` (no `head`) | semgrep prints a **finding count**; a count is falsifiable, a truncated list is not | The count is stable and you have read every hit. **Never** pipe an enumeration through `head`. If you must, print `\| wc -l` **first**, then page. |
| 3 | "What breaks if I change X?" | `graphify affected "<node_id>" --depth 1` — get the id from the Step-0 dump, **not** the label | Non-empty result naming files+lines. **`No affected nodes found` is NOT evidence of no callers** — it is the expected output of a wrong id | You have the depth-1 set. Do not trust depth-2 (~30% precision). Cross-check leaf-level with one `semgrep` pass. |
| 4 | "Does this exist at all?" | `semgrep`/`rg` with **explicit scope printed**: `rg -c '<tok>' <dir> \|\| echo "ZERO in $(pwd)/<dir> across $(rg --files <dir> \| wc -l) files"` | The negative must carry its **scope and file count**. Bare silence is not a negative | You have a zero *with* a scope statement. Absent that, you have not proven absence — you have proven nothing. |
| 5 | "Show me lines around X in *this* file" | `rg -n 'X' -A30 path` / `sed -n 'a,bp' path` | Non-empty output | Immediately. This works (69.8%); do not escalate. |
| 6 | "Did my edit land?" | `rg -n '<new string>' <file>` | Non-empty | Immediately. (77.1% — the best tool/intent fit in the corpus.) |
| 7 | "Has this been done before?" | `git log --grep=<t>` / `git log -S<sym>` / `git diff --stat` | Commit hashes | Immediately. (59.4% — keep.) |
| 8 | "Why did it fail?" | Read the actual error, then intent #1 or #5 on the named symbol | — | **Do not run a fourth diagnostic grep.** At `nsearch>=3` on a failure symptom, escalate to a subagent or ask, do not keep grepping — 35.8% of these already flail and no index fixes it. |

### 6.2 Three hard invariants (each fixes a measured failure)

1. **QUOTE `--include`.** Always `--include='*.py'`. *Fixes:* 137 measured searches (3.1%) that never
   executed because zsh glob-expanded the flag, 49 of which produced a believed false negative. This is
   the single highest-yield one-character fix in the audit.
2. **ONE SEARCH PER BASH CALL.** No `echo ===` compound bundles. *Fixes:* 634 measured searches (14.5%)
   that contained a silently empty sub-section inside output that read as successful. A bundle trades a
   visible negative for an invisible one.
3. **THE 3-SEARCH CIRCUIT BREAKER.** At the third search on the same tokens, **stop and switch method**
   (to §6.1 row 1, 2, or 3) — do not issue a fourth pattern. *Fixes:* the 33.6% of episodes that flail,
   including 142 episodes that issued **8 or more** searches on one question. Flailing is the measured
   signature of a wrong instrument, not of a hard question.

### 6.3 The agenda change (the part no tool provides)

`blast-radius` is 2.3% of searches. Before any edit, the routing table should be entered at **row 3**,
not row 1 — "what breaks?" before "what is it called?". The cheapest correctness win in this audit is
not a faster search; it is asking the impact question at all, once, with `graphify affected --depth 1`
at 0.1s per call.

---

## 7. One-paragraph answer to Ro

We search to answer eleven different questions, and we use one instrument for all of them. Where the
instrument fits the question — read a slice of a named file, confirm an edit landed, check git history —
we succeed 60-77% of the time at 3-4 calls. Where it does not — recover a name we half-remember (20.8%
of searches, 46.2%), enumerate a complete set (16.1%, 41.9%), prove something is absent (13.5%, 51.5%) —
we fail about half the time and burn 3.3M tokens doing it, because grep has no vocabulary, no notion of
completeness, and no way to distinguish "not there" from "my command never ran" (137 measured cases of
exactly that, 49 of them believed). So yes: a different method is needed, but not a *replacement* one —
a **router**. State the intent, then use semgrep for completeness, the graph's node list for vocabulary,
`graphify affected` for impact, and keep grep for the three things it is genuinely the best tool for.
