# Tool-adoption forensics — Claude Code transcripts

**Scope and method.** Exhaustive streaming pass over the five named project trees on 2026-08-02: **2,033 JSONL files** (virality-pipeline 1,469; Vividlist 249; Consulting 155; awesome-harness 103; intrn 57), including subagent files. This is four files more than the requested 2,025, so the counts are for the actual on-disk corpus, not a sample. JSON was read line-by-line with Python; no JSONL file was slurped. A CLI invocation is a command-position `graphify update|query|explain|affected`, `semgrep`, etc., after stripping heredoc bodies; an MCP invocation is an actual `mcp__repowise__*` tool-use record. Mere mentions in prompts, `grep`, `echo`, and heredocs are excluded.

“Available” is deliberately conservative and repo-level: graphify = virality-pipeline/Vividlist/awesome-harness/intrn (it is actually invoked there); repowise CLI/MCP, finding, and git-sync = awesome-harness; mulch = virality-pipeline/Vividlist/intrn; semgrep, recall, and check-all = all five (their global command/instructions are evidenced there). This avoids calling a tool “available” in a repo where the transcript proves it was absent (for example Vividlist’s `tools/git-sync.sh: No such file or directory`). Availability is historical evidence, not an inference from today’s filesystem.

## 1. Adoption by month

Each cell is **sessions ever invoking / invocations (share of available sessions)**. A session counts once per tool/month even if it invokes it repeatedly. The final total is across months; its share uses all available-repo sessions (not a sum of percentages).

| Tool | 2026-07 | 2026-08 | Total sessions / invocations / available-share |
|---|---:|---:|---:|
| graphify | 86 / 103 (8.4%; 86/1,026) | 51 / 92 (6.0%; 51/852) | **137 / 195 / 7.3% (137/1,878)** |
| repowise CLI | 2 / 4 (5.4%; 2/37) | 11 / 45 (16.7%; 11/66) | **13 / 49 / 12.6% (13/103)** |
| repowise MCP | 0 / 0 | 7 / 23 (10.6%; 7/66) | **7 / 23 / 6.8% (7/103)** |
| semgrep | 2 / 6 (0.5%; 2/1,171) | 5 / 25 (0.6%; 5/862) | **7 / 31 / 0.3% (7/2,033)** |
| mulch / `ml` | 10 / 120 (1.0%; 10/989) | 17 / 158 (2.2%; 17/786) | **27 / 278 / 1.5% (27/1,775)** |
| memgraph / recall | 2 / 2 (0.2%; 2/1,171) | 0 / 0 | **2 / 2 / 0.1% (2/2,033)** |
| `tools/finding.sh` | 0 / 0 | 1 / 6 (1.5%; 1/66) | **1 / 6 / 1.0% (1/103)** |
| check-all | 0 / 0 | 7 / 10 (0.8%; 7/862) | **7 / 10 / 0.3% (7/2,033)** |
| `tools/git-sync.sh` | 0 / 0 | 9 / 45 (13.6%; 9/66) | **9 / 45 / 8.7% (9/103)** |

The headline is not “zero adoption,” but it is very close for the intelligence layer outside a handful of August pilots: semgrep, recall, finding, and check-all each reached <=7 sessions; repowise never left awesome-harness; and graphify reached only 7.3% of the sessions where it was evidenced as available. `ml` is the exception in invocation volume, but just 27 sessions used it, mostly recording decisions rather than retrieving guidance.

## 2. What happened after a use

For **every counted invocation**, I inspected its result and the next three tool uses in the same JSONL. “Fallback” means a subsequent `Grep`/`Read`, or a Bash `rg`/`grep`, in that immediate window. This is a deliberately generous indicator of abandonment: it does not count a later fallback and therefore understates it. “Non-fallback” means no such immediate substitute; it is not automatically evidence that the output was useful (it includes direct work, another tool call, and no observable follow-up).

| Tool | Invocations | Immediate fallback to Grep/Read | Non-fallback / directly continued | Failure* |
|---|---:|---:|---:|---:|
| graphify | 195 | **160 (82.1%)** | 35 (17.9%) | 30 (15.4%) |
| repowise CLI | 49 | **16 (32.7%)** | 33 (67.3%) | 24 (49.0%) |
| repowise MCP | 23 | **5 (21.7%)** | 18 (78.3%) | 5 (21.7%) |
| semgrep | 31 | **15 (48.4%)** | 16 (51.6%) | 6 (19.4%) |
| mulch / `ml` | 278 | **60 (21.6%)** | 218 (78.4%) | 34 (12.2%) |
| memgraph / recall | 2 | 0 (0%) | 2 (100%) | 0 (0%) |
| `tools/finding.sh` | 6 | **4 (66.7%)** | 2 (33.3%) | 3 (50.0%) |
| check-all | 10 | **2 (20.0%)** | 8 (80.0%) | 1 (10.0%) |
| `tools/git-sync.sh` | 45 | **11 (24.4%)** | 34 (75.6%) | 5 (11.1%) |

\*Failure includes an explicit error/non-zero outcome, usage/syntax error, timeout, command-not-found, an explicitly empty/no-match result (`No node matching`, `No unique node match`, `No results found`, `Total pages = 0`), or no result body with exit 0. It does **not** label a valid zero-finding semgrep search as a failure merely for returning no findings.

Concrete follow-up evidence:

- graphify’s `explain "src/s3exec/review.py"` returned `No node matching ...`; the next operation was `Read` (virality-pipeline `a891d580…`, JSONL line 650). A query for `s1 fetch register` was likewise followed by a fallback (subagent `agent-a2…`, line 7). This pattern accounts for the 82.1% rate, rather than a claim inferred from installation.
- Repowise was sometimes acted upon: `mcp__repowise__get_risk` returned 11 dependents for `hooks/_hookout.py`, then Bash investigation followed (awesome-harness subagent `agent-ab…`, line 140). But its answer endpoint also returned `answer:"", citations:[] ... No wiki hits` (subagent `agent-a2…`, line 71), a counted empty-result failure.
- `ml` was normally used to persist a decision and then work continued; for example `ml record agency-pipeline --type decision ...` returned `✓ Recorded decision` (virality `a891d580…`, line 440). A syntax miss, `Error: --type is required`, was immediately corrected in the next invocation (line 680).
- check-all did yield actionable output: its virality run reported `drift: 3 paths, 0 commands` (session `12bbb61a…`, line 2651), and the agent continued with repo work rather than silently abandoning it. This is sparse adoption, not evidence that the command itself is broken.

## 3. Counterfactual: sessions that did not use the available tool

The normal substitute is visibly search/navigation, not another intelligence system. Across non-user sessions in an available repo, `Grep` or `Read` occurred in: graphify **279/1,741 (16.0%)** non-use sessions; semgrep **464/2,026 (22.9%)**; mulch **318/1,751 (18.2%)**; recall **469/2,031 (23.1%)**; and check-all **463/2,026 (22.9%)**. (The count is lower than intuition because many searches are Bash `rg`, which is intentionally not folded into this cross-session statistic; it is counted in the immediate-fallback measure above.)

There is **no defensible causal “worse outcome” finding** from these observational logs: tasks, agent role, repo, and tool availability differ sharply. The raw tool-result-error rate is actually higher in tool-use sessions (for example graphify-use sessions 271 tool-result errors across 137 sessions vs 533 across 1,741 non-use sessions), which is consistent with agents trying tools on hard tasks, not proof that the tool caused failure. The stronger, grounded conclusion is behavioral: after graphify/semgrep/finding attempts the agent frequently reverts to Grep/Read; the transcript does not establish that Grep-only sessions ship worse code.

## 4. MCP exposure cost

`deferred_tools_delta` attachments expose **304 distinct tool names** across the corpus. Only **24 (7.9%)** were ever invoked; **280 (92.1%)** were never invoked. This is a lower-bound exposure count: a tool mentioned in a tool definition but never added in an attachment is not counted.

The JSONL attachments retain tool *names*, not their full JSON schemas, so an exact schema-token total cannot be recovered honestly. A conservative standing-cost estimate is **~28k–56k input tokens per fully exposed toolset** for the 280 never-invoked tools, using 100–200 tokens/tool for a compact name+description+input schema (plus about 1k tokens of unused tool names alone). This is an estimate, not a measured billing number. The transcript directly demonstrates the breadth: e.g. the Sparktoro family alone has 13 listed operations in 795 sessions, while none appears in the called-schema set.

## 5. Adoption barriers, with transcript evidence

1. **The tool is not in the path the agent actually follows; Grep/Read is faster and more reliable for local orientation.** The graphify “no node” response at virality `a891d580…:650` is immediately followed by `Read`; the aggregate is 160/195 immediate fallbacks. This is direct behavior, not a survey claim.
2. **Index/repository coverage is incomplete or silently wrong.** Repowise `get_answer` says `No wiki hits` in awesome-harness `agent-a2…:71`; the later project-state evidence records `Total pages = 0` in the other four repos. Graphify’s same session says `No node matching 'src/s3exec/review.py'`. A system that can return an authoritative-looking empty answer makes the basic tools a rational fallback.
3. **Invocation and validation friction burns attempts.** `ml` explicitly errors `--type is required` (virality `a891d580…:680`); finding’s TTY test is blocked by the irreversible-action hook and then times out (awesome-harness `agent-af…:27` and `:30`); and semgrep’s output records `Invalid pattern for Python` despite `EXIT=0` (awesome-harness `agent-ab…:158`). These are concrete failed-use paths, not speculation that agents merely “did not know.”

## Recommendation: cut, keep, or narrow

**Cut outright from default/tool-schema exposure:** repowise **MCP** (7 sessions, 23 calls, wrong-repo/empty-index evidence) and the large unused MCP catalog (280 never-called tools). **Do not cut the repowise CLI outright** until its per-repo indexing is either made reliable or explicitly retired: it had a concentrated August pilot, but 49.0% failures and no evidence of cross-repo utility.

**Remove from default ritual, retain on-demand:** graphify query/explain (82.1% immediate fallback); global recall/memgraph (2 calls); and finding (one test/audit session, not operational use). **Keep but do not mandate:** semgrep (rare adoption but it found actionable issues), check-all (sparse but acted upon), `ml` for its actual decision-recording role, and git-sync where its commit/push workflow is wanted. The data supports reducing compulsory schema/prompt surface, not removing every executable.

## Reproducibility notes

- The report’s counts are from actual parsed `assistant.message.content[type=tool_use]` and their paired `toolUseResult` records; JSON parse failures: **0**.
- Main and subagent JSONL files are intentionally both included: excluding subagents would erase much of the pilot/verification behavior under audit.
- Session IDs above are transcript basenames (prefix shown with ellipsis); “line” is the one-based JSONL line number. Quotes are result content from that line’s paired tool result, shortened only for readability.
