# How agents locate code today — transcript forensics

**Scope.** Read-only analysis of every JSONL currently present under the five requested project directories on 2026-08-02. This is a census rather than a random sample: 2,033 transcripts (1,181 top-level and 852 `subagents/`): virality-pipeline 1,469; Vividlist 249; Consulting 155; awesome-harness 103; intrn 57. The requested inventory said 2,025 sessions / 843 subagents; the filesystem had eight additional logs when measured. Every file was opened with Python and processed one JSON object (one line) at a time—never whole-file loaded or printed.

**Command used to enumerate the sample (exact).**

```sh
python3 - <<'PY'
import os, glob
B='/Users/rodrigoarista/.claude/projects'
R=['-Users-rodrigoarista-Downloads-virality-pipeline','-Users-rodrigoarista-Downloads-Vividlist','-Users-rodrigoarista-Downloads-Consulting','-Users-rodrigoarista-Downloads-awesome-harness','-Users-rodrigoarista-Downloads-intrn']
for r in R:
 p=f'{B}/{r}'; a=glob.glob(p+'/*.jsonl'); b=glob.glob(p+'/**/subagents/*.jsonl',recursive=True)
 print(r,len(a),len(b),len(a)+len(b))
PY
```

**Analysis command (exact invocation and method).** `python3 - <<'PY' … PY` was run from this repository. Its single-pass program: recursively globbed only those five directories; iterated `for line in fh`; parsed `message.content` objects; paired `tool_use.id` with later `tool_result.tool_use_id`; classified exact native tool names (`Read`, `Grep`, `Glob`, `Bash`, `Task`) and `mcp__*`; measured UTF-8 result bytes and `ceil(bytes/4)` estimated tokens; and used `statistics.median` / nearest-rank index `round((n-1)*p/100)`. The exact core loop was:

```python
for repo, path, kind in files:
    calls, results = [], {}
    with open(path, encoding='utf8', errors='replace') as fh:
        for line in fh:                 # streaming; no whole transcript is read
            x = json.loads(line)
            for z in (x.get('message') or {}).get('content') or []:
                if z.get('type') == 'tool_result': results[z.get('tool_use_id')] = text(z.get('content',''))
                elif z.get('type') == 'tool_use': calls.append((z['name'], z.get('input') or {}, z['id']))
    # classify calls; attach results[id]; aggregate the definitions stated below
```

The supporting exact predicates were `ranged = any(input.get(x) is not None for x in ('offset','limit'))`, `token_estimate = (utf8_bytes + 3)//4`, and terminal-search `re.search(r'(^|[;&|]\\s*|\\$\\()\\s*(?:rg|grep|ag|fd|find)\\b', command)`. Current on-disk file-size statistics use `os.path.getsize(input['file_path' or 'path'])` only where that old path still exists. This gives reproducible definitions without pretending transcript output is the original file size.

## Bottom line

Agents mostly locate code through shell searches, not Claude's native search tools: 4,918 Bash search commands versus **one** native `Grep` and zero `Glob`. Native-Read use is sparse across the full population (median zero), but when it happens it is usually a whole-file pull (72.31%). Terminal search is often an iterative diagnostic narrowing process: 229 candidate three-or-more-search episodes under the conservative definition below. This is a measured behavior pattern, not proof that every episode was unproductive.

## 1. Tool-call census

**Command and sampling.** The single-pass command above, over all 2,033 available transcripts. A share's denominator is all 21,156 `tool_use` records; `other` (2,994, chiefly edit/write/planning/system tools) remains in that denominator. Per-session medians include zero-tool sessions, intentionally.

| Tool | Calls | Share of all calls | Median/session | P90/session |
|---|---:|---:|---:|---:|
| Read | 2,138 | 10.11% | 0 | 4 |
| Grep | 1 | 0.00% | 0 | 0 |
| Glob | 0 | 0.00% | 0 | 0 |
| Bash | 14,171 | 66.98% | 0 | 21 |
| Task | 0 | 0.00% | 0 | 0 |
| MCP (`mcp__*`) | 90 | 0.43% | 0 | 0 |

The zeros for native search are real, not missing data: this transcript population predominantly represents agents using shell commands such as `grep`, `rg`, `find`, and `sed` inside Bash. The separate terminal-search predicate found **4,918** such Bash commands.

## 2. Read behavior

**Command and sampling.** Same complete-corpus streaming command. `FULL` means neither `offset` nor `limit` appears with a non-null value; `RANGED` means either is non-null. Read payload is the captured tool-result text; token counts are estimates (`ceil(UTF-8 bytes/4)`), not model-billing tokens.

| Measure | Result |
|---|---:|
| Read calls | 2,138 |
| Full-file Reads | 1,546 (72.31%) |
| Offset/limit ranged Reads | 592 (27.69%) |
| Captured Read output | 16,145,601 bytes / ~4,037,122 tokens |
| Per-session Read output, median | 0 bytes / 0 tokens |
| Per-session Read output, P90 / P95 / P99 | 25,024 / 49,117 / 129,917 bytes; ~6,256 / 12,280 / 32,480 tokens |
| Per-Read captured output, median / P90 / P99 | 3,090 / 23,114 / 52,339 bytes |

File-size distribution (current filesystem only; 1,675 of 2,138 historical Read paths still exist): P25 **6,386 B**, median **16,965 B**, P75 **34,486 B**, P90 **100,584 B**, P95 **275,483 B**, P99 **3,336,383 B**. The other **462** historical paths no longer existed, so they are excluded rather than guessed.

## 3. Re-reads

**Command and sampling.** Same complete-corpus command. Within each transcript, Read paths were grouped by exact input path. Every Read after the first for that path is an extra read; its captured-result `ceil(bytes/4)` is counted as estimated avoidable re-read tokens. This is deliberately conservative: it does not call the first read waste, and it does not merge different spellings/symlinks.

**Result.** 248 / 2,033 sessions (**12.20%**) re-read at least one same path. There were **380 extra Reads**, carrying an estimated **784,736 tokens** of repeated output.

Top paths by extra Reads (with repeated-output token estimate):

| Path | Extra Reads | Estimated repeated tokens |
|---|---:|---:|
| `Vividlist/scripts/probes/pdf_intake/discover_pdf_source_facts.py` | 37 | 71,695 |
| `Vividlist/services/package_to_render/runner.py` | 35 | 88,842 |
| `intrn/.../reverse-poolb/job-selection.ts` | 17 | 11,425 |
| `intrn/.../reverse-poolb/__tests__/job-selection.test.ts` | 14 | 12,933 |
| `virality-pipeline/.now.md` | 12 | 3,155 |
| `intrn/.../heavy-funnel/stage-2-roster/index.ts` | 10 | 4,936 |
| `Consulting/.now.md` | 7 | 1,311 |
| `Vividlist/services/package_to_render/label_seeded_room_recovery.py` | 6 | 7,140 |
| `Vividlist/services/package_to_render/cad_text_classifier.py` | 6 | 13,050 |
| `intrn/.../reverse-poolb/candidate-trim-rank.ts` | 6 | 13,235 |

## 4. Search-then-read chains

**Command and sampling.** Same complete-corpus command. For every *native* `Grep`, I count subsequent `Read`s until the next native `Grep` or `Glob`; file hits are paths matching `path:line` in that Grep result, and an opened hit is a following Read with that exact path or suffix. This is the precise answer for the requested tools. I also counted Bash search-equivalents with the regex stated above to avoid a misleading conclusion from tool naming.

**Result.** There was only **1 native Grep**, it had **0 parseable file hits**, and it was followed by **0 Reads** (median/P90/P95/P99 following Reads all **0**). Thus the hit-open fraction is **not measurable (0/0)**, not 0%. The logs do *not* show a native `grep-then-read-everything` pattern; they show that agents nearly always search via Bash instead (**4,918** `rg`/`grep`/`ag`/`fd`/`find` command invocations). Bash output does not have a stable machine-readable hit schema across commands, so no invented hit-open rate is reported for it.

## 5. Failed-search / flailing pattern

**Command and sampling.** Same complete-corpus stream, plus this exact candidate-episode predicate over Bash searches (native Grep/Glob yielded **0** episodes because there are fewer than three calls):

```python
leading = re.match(r'\\s*(?:cd\\s+[^;&]+\\s*&&\\s*)?(rg|grep|ag)\\b', command)
# within one session: same leading executable, <=2 intervening tool calls,
# three or more distinct command strings; take each maximal non-overlapping run
```

**Result.** **229 candidate episodes**. These are search-refinement/flailing candidates, not an assertion of failure: the definition detects repeated near-by, same-family searches with different patterns and prevents the far larger false count caused by `grep` used only as an output filter in a pipeline. Native Grep/Glob: **0 episodes**.

Three verbatim examples (all from `virality-pipeline/a891d580-38f5-421b-84b3-2e5725ec3a34.jsonl`):

```sh
grep -n "bracket-this-or-that\|format_priorities\|selected_format_card" src/s2/*.py src/pipeline.py 2>/dev/null | head -15
grep -rn "def choose_format\|format_id" src/s2/brief.py 2>/dev/null | head; ls src/s2/ 2>/dev/null; grep -rn "format_id =" src/originated/brief* src/s2 2>/dev/null | head -5
grep -rn "format" src/blra/brief_generator.py 2>/dev/null | head -8; grep -rln "bracket" src/ | head -5; grep -rn "format_priorities\[0\]\|format_priorities" src/blra/*.py | grep -v compile | head -8
```

```sh
grep -n "def \|log\|stderr\|category" src/s3exec/codex_host.py | head -30
grep -n "transcript\s*=\|transcript_path\|\.jsonl" src/s3exec/codex_host.py | head -8; find state -name "*.stderr" -newer /tmp -mmin -30 2>/dev/null | head; find . -path ./node_modules -prune -o -name "*.stderr" -mmin -60 -print 2>/dev/null | head -5
grep -n "def synthesize_hooks\|class S3Tools" src/s3exec/*.py | head; grep -n "timeout\|tool_timeout" src/s3exec/codex_mcp_server.py | head
```

```sh
grep -n "expected = {" -A4 src/s3exec/codex_mcp_server.py
grep -n "provider_codex_home\|invocation_id" src/s3exec/codex_host.py src/s3exec/codex_mcp_server.py | head -12
grep -n "provider_codex_home\|provider_home\|invocation" src/s3exec/codex_host.py | head; grep -n "context.write_text" -B3 -A20 src/s3exec/codex_host.py | sed -n '1,40p'
```

## 6. Orientation tax

**Command and sampling.** Same complete-corpus command. For each session with an exact native `Edit` or `Write`, take the number of preceding `tool_use` records; sessions without either tool are excluded because there is no first edit. This includes all tool kinds in the count (orientation, shell checks, planning, etc.).

**Result.** 426 sessions had an Edit/Write. The median number of tool calls before the first Edit/Write was **9** (P25 **4**, P75 **17**, P90 **27**, P95 **36**, P99 **74**). This is the measurable pre-change orientation/diagnosis tax, not a claim that every preceding call was unnecessary.

## Interpretation for restructuring

The immediate design fact is not “replace Grep”: it is that the actual front door is Bash, where code location and diagnosis are interleaved. Native search-chain instrumentation currently has almost no behavioral surface to optimize. The biggest directly measured opportunities are (1) make the existing shell-search path more structured/reusable, (2) avoid duplicate whole-file Reads, and (3) reduce repeated search pivots once a subsystem has been found.
