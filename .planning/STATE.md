# Harness Hardening — State

## NOW
Enforcement audit + Codex parity + auditor synthesis all SHIPPED (e639ff5 → 70e1713, pushed).
The 2026-07-27 session that did this was deleted mid-flight; context recovered from transcript
`~/.claude/projects/-Users-rodrigoarista-Downloads-awesome-harness/1a72c93c-*.jsonl` on 07-28.

## Active Resume Point

**Last updated:** 2026-08-02
**Status:** SHIPPED + pushed `a7d082d`. Ro redirected: do NOT cut tools, COMBINE them, and
first check whether the bad scores were OUR misuse. Three agents ran; the redirect was right.

**(1) graphify — misuse confirmed on all three counts.** Source read at
`~/.local/share/uv/tools/graphifyy/lib/python3.13/site-packages/graphify/` (v0.8.47).
`query` scored 0/3 because we never ran graphify's OWN mandatory "Step 0 — constrained
query expansion" (`skills/claude/references/query.md`): dump the graph's label vocab, pick
<=12 tokens FROM it, query with THAT string, not the user's question. There is no stopword
list (`serve.py:91` keeps any token >2 chars) so NL questions seed on junk like "How".
Also `serve.py:390` silently rewrites the traversal graph if the question contains
"calls"/"imports"/"returns", and the default `--budget 2000` truncates the EDGE lines away
— we were reading a node list and calling it an answer. Correct form: 2.5/3.
`uses` is 100% precise against its OWN definition (`extract.py:8942`: for each
`from M import Name` in file F, edge from every class in F to Name) = a co-import /
blast-radius signal, NEVER a call graph. 30/30 vs its definition, 18/30 vs ours: the "27%"
was our measurement error. Dangling edges are DELIBERATE (`extract.py:3835`,
`build.py:179/315` call them "expected"); the real defect is bare `import _hookout`
targeting id `hookout` while the file node is `hooks_hookout` (`extract.py:1282`).
`graphify update .` fixed it here — dangling now 0/1, and the phantom node disappeared with it.

**(2) Real-task benchmark (26 questions mined from 1011 + 537 commits, 14 hand-ground-truthed
BEFORE any tool ran).** Genres won: **Grep 8, graphify 3, semgrep 2, repowise 0-for-13.**
Grep is still the default and beats the fancy tools on prior-art / config-owner / abandoned-
approach questions because those span code AND prose. semgrep wins write-site enumeration
decisively: +79pp recall in Python (grep misses multi-line `conn.execute(\n "INSERT…`),
+25pp precision in TS (grep's `.update(` collides with `createHash().update()`).
graphify is symbol-level depth-1 ONLY — file-name queries return the wrong node silently,
depth-2 precision ~30%.

**(3) Chains + rules shipped and tested** (`tools/chains/`, `tools/semgrep/`): 7 chains,
12 rules in 5 files, all `--validate` clean, all run on awesome-harness AND virality-pipeline.
Every chain caps stdout at 14 lines via `_lib.sh finish()`; full dump -> `/tmp/chains/<repo>/`,
`CHAIN_RECORD=1` files it via `tools/finding.sh`. **No chain needs the MCP** (`repowise
risk`/`dead-code` are CLI), so all 5 repos work despite the pin.
Verified independently by main: `c3-enumerate` -> 72 sites + honest unparsed-file warning;
`c1-blast "_hookout"` -> 11/11 importers via the semgrep fallback leg after graphify's node
vanished — the UNION design is what saved that answer.

**FOUR SILENT-FAILURE CLASSES found (all exit 0) — these are the real product of the day:**
- repowise `Total pages = 0` in the other 4 repos -> "No results found" == true negative.
- repowise MCP pinned to awesome-harness -> answers about the WRONG repo, silently.
- **semgrep `--validate` says VALID for a rule that returns 0 when 116 exist** (`...` inside
  a string literal is not an ellipsis). `--validate` is NECESSARY BUT NOT SUFFICIENT; the
  only real guard is a positive control asserting non-zero. Also: semgrep silently SKIPS
  files it cannot parse (hid 2 deny sites from a "complete" 13) — chains now warn.
- graphify `explain "<file>.ts"` returned a throwaway node with 1 importer instead of the
  real one with 12; `affected "BrandResearch"` -> "No unique node match" with no candidates.
- Bonus bug worth a sweep: `set -o pipefail` + grep's exit-1-on-no-match killed a chain at
  the exact moment it found something. Audit harness scripts for `x=$(… | grep …)`.

**Semgrep first real findings:** forclosurehomes 591 (164 of 235 HTTP calls with no
`timeout=`), Vividlist 463 (48 hand-rolled retry loops + 14 named helpers), virality-pipeline
172 (reproduced the original burn: 13 retry sites + `tenacity` declared/never-imported),
awesome-harness 72, intrn 50 (29 hardcoded `/Users/...` paths).

**Wiki verdict: 1 of 5 keeps one, 0 of 5 get one generated.** awesome-harness YES (60 pages
already exist, sunk cost, MCP-reachable). The other four NO — every chain ran on
virality-pipeline today at 0 wiki pages. Vividlist is the best FUTURE candidate, after its
463 findings are harvested.

**NOT DONE (next session):** fold survivors into the `/awesomeharness` skill (asked 3x now);
cut `graphify query` from its 12 doc refs OR replace them with the Step-0 form; wire
`c2-prior-art` -> codebase-first, `c1-blast` -> code-decompose, `c7-preship` -> check-all;
`graphify update` on the other 4 repos; **LAST: restart the repowise MCP** (Ro's explicit
order — everything else first, since the restart kills this session).
NOTE `.claude/CLAUDE.md` is GITIGNORED — the scope warning added there is local-only and
does NOT propagate to the other repos; each needs its own.

**Prior status (superseded):**

**Last updated:** 2026-08-01 (late)
**Status:** SHIPPED + pushed `468067d`. (1) The weekly CLAUDE.md trimmer finally RUNS. Full Disk Access for `/usr/bin/python3` turned out to be UNACHIEVABLE — `/usr/bin` is hidden in the Finder picker, so Ro cannot add it. Replaced with `tools/launchd/run-claudemd-trim.sh`: launchd runs a bash shim that drives Terminal.app via `osascript` (argv-passed path, injection-safe), borrowing the grant Terminal already holds. The shim must live OUTSIDE `~/Downloads` — launchd cannot even read a script inside a TCC-protected dir (exit 126) — so the canonical copy is in the repo and an identical copy is installed at `~/.claude/tools/run-claudemd-trim.sh`, which is what the plist runs. Keep them in sync. NOTE: the plist logs now prove only DISPATCH; trimmer failures show up in the Terminal window or in `~/engineering-harness/reports/claudemd-trim/`. (2) `tools/git-sync.sh` stamps every commit with a `Terminal: <id>` trailer (`--terminal` > `$HARNESS_TERMINAL` > tty+PID > host+PID) and runs a read-only pre-commit survey classifying other remote branches AHEAD / RECENT / STALE (`GIT_BRANCH_STALE_DAYS`, default 3). AHEAD branches are ALWAYS printed regardless of the 20-line display cap. The survey never merges, deletes, or blocks.

**Prior status (superseded):** Auditor REJECT redispatch (13 ordered fixes + 1 extra) APPLIED by a fresh builder, uncommitted. Trimmer collision resolved: `tools/claudemd-trim.py` KEPT, `tools/claudemd_trim_audit.py` + `templates/…plist` DELETED. understand-gate reverted to global `warn` with repo opt-in via a `.understand-gate` marker (this repo is marked). check-all stamp moved to the END of the run and now carries `ok`. Scaffold capture is ambient off a GREEN check_all.sh (SCAFFOLD_CATEGORY/APPROACH/ITERS/AUDITOR env).
**Next concrete step:** Decide `~/.route-only` — the written verdict in `.scratch/route-only-verdict.md` is DELETE. It armed every repo (zero-byte file at `$HOME`, dated Jul 11) and today pushed three builders to write via Bash heredoc instead of Edit, which ALSO blinds the uncommitted-work notice (it only sees Write/Edit/MultiEdit rows).
**Blocked on:** nothing. FDA is no longer needed — the Terminal-borrowing shim removed that dependency entirely.

## LAST_VERIFIED (2026-07-27)
- `e639ff5` un-inverted guards (mention-matching → write-matching), main-edit-guard/builder-fence/route-only-gate
- `a083ecc` boot-heavy / turn-light injection; `/awesomeharness` re-asserts the full floor
- `d89589a` Codex parity — code-decompose/compact-prep/check-all/recall + both standards + AGENTS.md router
- `70e1713` deduped graphify-blindspot in settings.json; harness-coach fails loud; irreversible-pause blocks graded submits
- Auditor verdict in durable memory: `memory/harness-auditor-yield-verdict.md` (do NOT re-read the 10 reports)

## NEXT (open decisions, ranked)
1. Give harness-coach + harness-scout memory of their own prior reports — highest value, XS effort
2. `launchctl unload` the dead `com.ro.engineering-harness-audit` (exit 1 every Monday since 06-24)
3. Move harness-scout back to weekly (was switched to daily 07-27)
4. Trim the scout creator list
5. Stop-hook violation counter (~30 lines in session-checkpoint.py; UX win, NOT a token win — measured 2166 saved vs 4224 spent)

## CARRIED
- `understand-gate` still in `warn`, never armed to block
- Map auto-refresh unwired
- `~/awesome-harness` stale clone with unresolved `UU .now.md`
- `northstar-protect.py` mention-matching inversion sweep
- `~/.codex/skills/codex-primary-runtime/` is an empty dir — stale artifact?
- Codex asymmetry (documented, not faked): self-audit instead of independent auditor; no hooks fire on the Codex side
