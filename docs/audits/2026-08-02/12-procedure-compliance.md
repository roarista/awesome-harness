# 12 — PROCEDURE compliance forensics

**Question (Ro):** *"no sé si esto esté corriendo correctamente, que usamos subagentes de Codex, que decomponemos primero, que vemos el codebase first, todas estas cosas que no sé si se hagan correctamente siempre."*

**Answer up front:** he is right, but not about the step he suspects. Decomposition and codebase-first mostly *do* run. What does not run is **Codex** (0 verified source writes, 48% of delegations returned nothing), **check-all** (32%), and **push** (41%). And the guard that is supposed to stop main from coding is bypassed 61% of the time by Bash.

---

## 0. Method, denominator, and what is invisible

Corpus: `~/.claude/projects` — **2,861 main-session JSONL + 935 subagent transcripts** across 27 project dirs, streamed (never `cat`'d). Scripts: `$CLAUDE_JOB_DIR/tmp/scan2.py`, `scan3.py`.

**DENOMINATOR — "substantive coding session" = 22 sessions.** A session qualifies if it contains ≥1 write to a *source* file (`.py .js .ts .tsx .sh .go .rs .css .html .sql …`) at a **non-scratch path** (excludes `/tmp`, `.scratch`, `~/.claude/jobs`), counting main-session Edit/Write/MultiEdit, subagent Edit/Write/MultiEdit, and Bash heredoc / `sed -i` / `tee` / redirect writes. Every rate below is `n/22` unless stated otherwise.

22 is small because Ro's sessions are enormous and long-lived: the median qualifying session spans **34 hours** and the top 5 span 92–193 h. 2,839 of 2,861 sessions write no source at all (research, PDFs, essays, harness reports, telemetry stubs). These 22 sessions contain **615 source writes and 301 commits** — i.e. essentially all of Ro's real engineering.

**What I can see:** every tool call, its arguments, its result, and timestamps, in both main and subagent transcripts.
**What I CANNOT see, and never call "did not happen":**
- Work done by the **background Codex runtime**. `codex:codex-rescue` hands off to an out-of-process job; its file writes never appear in any transcript. Codex activity is *unobservable*, not *absent*.
- Reasoning. GATE is only detectable when the model *writes* a STOP/PLAN/BUILD or REUSE/ADAPT/REJECT verdict as text. A gate decided silently reads as non-compliance.
- Completion notifications delivered after a session was resumed under a **new session id** — these break my `<tool-use-id>` matching, so "unresolved forward" is an upper bound.
- 142 of 935 subagent transcripts (15%) whose `agentId` I could not map back to a `subagent_type`; they are reported as UNKNOWN, not folded into any type's total.

---

## 1. PER-STEP COMPLIANCE RATE (n = 22)

| # | Step | Evidence I accepted | Rate | Verdict |
|---|------|--------------------|------|---------|
| 0 | ORIENT | Read **or** Write of `.now.md` / `.northstar.md` / `STATE.md` | **17/22 = 77%** | **(a) running, valuable** |
| 1 | RECALL | `recall` skill, `ml prime/record/sync`, memgraph, or Read of `MEMORY.md` / `.mulch/` | **20/22 = 91%** | **(a) running, valuable** |
| 2 | UNDERSTAND | `codebase-first` skill, `graphify` bash, any `mcp__repowise__*`, or REUSE/REJECT evidence carried in a spawned agent's prompt | **21/22 = 95%** | **(a) running** — but see split below |
| 2a | └ graphify | `graphify` invoked | 14/22 = 64% | (a) |
| 2b | └ repowise | any repowise MCP call | **1/22 = 5%** | **(c) not running** |
| 3 | GATE | assistant text containing a STOP/PLAN/BUILD verdict or REUSE/ADAPT/REJECT | **16/22 = 73%** | **(d) partly unmeasurable** |
| 4 | DECOMPOSE | an Agent prompt carrying all of CONTEXT + CHANGE + GOAL + VERIFY | **15/22 = 68%** | **(a) running, weakly** |
| 5 | BUILD delegated | any builder subagent spawned | **21/22 = 95%** | **(a) running** |
| 5b | └ main wrote source anyway | ≥1 main-session source write | **16/22 = 73%** | **the real leak** |
| 6 | VERIFY — auditor | `opus` / `code-audit-agent` spawn, or an "audit" prompt | **17/22 = 77%** | **(a) running** |
| 6b | VERIFY — check-all | `check_all.sh` / check-all skill executed | **7/22 = 32%** | **(c) barely running** |
| 7 | PERSIST — commit | ≥1 `git commit` or `git-sync.sh` | **13/22 = 59%** | **(a) running, late** |
| 7b | PERSIST — push | ≥1 `git push` | **9/22 = 41%** | **(c) not running** |
| 7c | PERSIST — via `git-sync.sh` | | **3/22 = 14%** (28 of 301 commits = 9%) | **(c) not running** |

**Largest gap: step 6b, `check-all` (32%).** It is the one step the PROCEDURE names as a hard precondition for accepting a unit ("VERIFY passes only when … `check-all` shows no FAIL rows"), and two thirds of coding sessions never ran it once. Second-largest: **push (41%)** — work is committed locally and left there, which is exactly the failure mode `git-sync.sh` was built for and which is used in 9% of commits.

Note step 2's 95% is carried by cheap signals (graphify, REUSE text in a prompt). **repowise, which the project CLAUDE.md documents at length as the primary pre-edit tool, was used in exactly 1 of 22 coding sessions.** That is a whole documented tool tier that is pure prompt tax.

---

## 2. THE DELEGATION QUESTION

### 2a. Does main write feature code?

Source writes at non-scratch paths, all 22 sessions (denominator = **763 attributable source writes**):

| Writer | via Edit/Write/MultiEdit | via Bash (heredoc/`sed -i`/`tee`/redirect) | total | share |
|---|---|---|---|---|
| **MAIN session** | 35 | **55** | **90** | **11.8%** |
| Subagents | 642 | 113 | 755 | 88.2% |

**So delegation broadly works — main writes ~1 in 8 source edits.** But:

- **61% of main's source writes (55 of 90) went through Bash**, which `main-edit-guard` is not registered on. The guard is doing its job on the surface it covers (only 35 got through Edit/Write) and is blind to the majority of the actual traffic. This is documented behaviour ("Bash writes bypass them BY DESIGN"), so the honest statement is: *the guard's number looks good because the traffic moved to where it can't see.*
- **16 of 22 sessions (73%) had main write source at least once.** It is not one rogue session; it is a steady habit.
- The all-project Bash-write census (1,645 write targets extracted) shows main's writes are *mostly* legitimate: 631 to scratch/tmp and 355 to non-source files (docs, `.now.md`, reports). The 55 real ones are the violation.

### 2b. Did delegated builds go to CODEX?

Subagent transcripts attributed by `subagent_type` (935 transcripts, 793 mapped):

| subagent_type | transcripts | source writes in its own transcript |
|---|---|---|
| `general-purpose` (Claude) | 498 | **520** |
| `code-unit-agent` (Claude, code-decompose) | 47 | **102** |
| `code-audit-agent` (Claude) | 27 | **12** ← auditors editing |
| `claude` | 7 | 2 |
| UNKNOWN (unmapped) | 142 | 36 |
| **`codex:codex-rescue`** | **84** | **0** |
| `opus` (auditor) | 82 | 1 |
| `Explore`, `decompose-agent`, `Plan`, `gemini-agent` | 45 | 0 |

**Every observable build was executed by a Claude subagent. Zero source writes are attributable to a Codex-typed agent.**

The honest caveat: this is *expected*, because codex-rescue is a forwarder — Codex's writes happen in a background process outside the transcript. So the correct claim is not "Codex never built anything"; it is **"no build by Codex is verifiable from the record, and the parent had no returned artifact to verify it against."** For an audit trail that is the same thing as not having happened.

### 2c. The forwarder problem — how often did a delegation silently break?

**102 `codex:codex-rescue` calls** (Vividlist 37, virality-pipeline 37, awesome-harness 18, other 10; Jul 57 / Aug 45). Classified by what came back:

| Return | n | % |
|---|---|---|
| **Substantive result** (diff described, tests, rc=0) | 15 | 15% |
| **Hard failure** (Codex sandbox read-only, `builder-fence` blocked the forwarder, `exit 127`, config `Operation not permitted`, 10-min timeout) | 17 | 17% |
| **Receipt only**, later resolved by a `<task-notification>` matching the tool-use-id | 21 | 21% |
| **Receipt only, NEVER resolved in-session** | **49** | **48%** |

**48% of Codex delegations returned a receipt and nothing else.** Verbatim returns:

> `"Task forwarded to Codex in the background (job ID bswsgydc7)… Per my role as a forwarder, I will not poll, read, or summarize the result myself"` — Vividlist, 2026-07-27T23:57

> `"Async agent launched successfully… You know nothing about its results until that notification arrives"` — 53 occurrences

> `"Waiting on the backgrounded Codex task (ID: bchdrqjf1) — no output to report yet."` — virality-pipeline, 2026-08-01T20:10

The 17 hard failures are worse than the receipts, because they are *silent no-ops the parent had to notice*:

> `"Blocked by the repo's builder-fence hook (missing CONTEXT/CHANGE/GOAL/VERIFY/REUSE decompose block) before it could reach Codex. As a pure forwarder I can't satisfy that repo-specific gate — returning nothing."` — 2026-07-24T03:57
> `"Codex could not create the file — blocked by its own workspace sandbox … No files were modified by Codex."` — 2026-07-25T16:58
> `"The Codex companion call failed (exit code 127 — command not found) before any prompt was forwarded."` — 2026-08-01T06:06

**Did the parent treat a receipt as finished work?** I searched every unresolved forward for a parent claim of completion in the next 5 records and found **none** — the parent did not fabricate results. What it did instead, within 30 minutes:

| Parent behaviour after an unresolved forward | n |
|---|---|
| nothing at all within 30 min (delegation simply evaporated) | **27** |
| spawned a *different* agent to do the same work | 19 |
| **committed anyway within 30 min** | **3** |
| polled the output file / SendMessage'd the agent | 3 |

So the damage is not hallucinated success — it is **27 dropped units and 19 duplicated units**: the work was either lost or paid for twice. The 3 commit-anyway cases are the dangerous ones, e.g. Vividlist `10096718` at `2026-07-28T04:27` — forwarded *"An independent audit found a MAJOR test-coverage defect (B1)"* to Codex, got a receipt, committed inside the half hour.

**Verdict on step 5's Codex clause: (c) not running.** The rule "code writes → codex subagent" is followed 0% of the time in any verifiable sense; when attempted it fails or evaporates half the time; and the actual builders are Claude subagents, which work fine.

---

## 3. THE AUDIT STEP

Denominator = 22 coding sessions, plus 615 source-write events for the per-write rates.

- **A non-builder auditor ran in 17/22 (77%) sessions** — `opus` (86 spawns all-corpus) or `code-audit-agent` (30). This step genuinely runs.
- **Builder-audits-itself:** `code-audit-agent` transcripts contain **12 source writes**. The auditor is supposed to report and stop (`opus.md`: "It NEVER edits"). `opus` held the line — 1 source write in 82 transcripts. `code-audit-agent` did not.
- **Nobody audited at all: 5/22 sessions (23%)** — every one of them a small-src session (`health-system` ×2, Consulting ×2, `virality-pipeline 02:59`).
- **`check-all` before a commit: 7/22 sessions (32%).** Across the whole corpus, 55 check-all invocations against 301 commits — **an 18% commit-to-gate ratio**, and even that is concentrated: session `94c6cfd1` (awesome-harness) alone accounts for 99 of the corpus's check-all runs. Outside awesome-harness, **check-all is close to non-existent** — Vividlist's 91-source-write session ran it **0** times; intrn's 259-source-write session ran it **0** times.
- The `check-all-commit-gate` hook is **per-repo opt-in**, which explains the awesome-harness concentration. The gate is not broken; it is simply not installed where the code actually gets written. (It fired at me twice while writing this report, in the one repo that has it on.)

---

## 4. THE PERSIST STEP — real cadence

Contract: commit **+ push** the moment a unit is built and verified, via `git-sync.sh`.

| Measure | Value |
|---|---|
| Source writes / commits (22 sessions) | 615 / 301 = **2.0 source writes per commit** |
| Median session commit count | 2 (mean 13.7 — dominated by 4 sessions) |
| **Median lag, source write → next commit** | **20.3 min** (median of per-session medians) |
| Source writes committed within 10 min | **~25%** |
| Source writes never followed by any commit in the session | **34 of 615 (5.5%)** |
| **Sessions ending with uncommitted source work** | **7/22 = 32%** |
| Sessions that ever pushed | 9/22 = 41% |
| Commits made through `git-sync.sh` | **28 of 301 = 9%** (3/22 sessions) |

Reading: cadence is **per-batch, not per-unit**. 2 units per commit and a 20-minute median lag is not catastrophic, but it is not the contract, and the tail is bad — session `c64a4006` has a 72-minute median lag, `e19223f7` has a 21-hour one. Five sessions (`1a72c93c`, `1f52a6ce`, `20111f9c`, `67afc3d8`, `7c11e52e`, `4c48f5c6`) wrote source and **never committed once**.

`git-sync.sh` is the harness's answer to the multi-terminal race and it carries **9% of commits**. 91% of commits are raw `git commit` — i.e. the "never lose another terminal's work" guarantee is off for 91% of the traffic.

---

## 5. WHERE IT BREAKS DOWN

I scored each of the 22 sessions 0–10 (one point each: ORIENT, RECALL, UNDERSTAND, GATE, DECOMPOSE, no-main-source-write, auditor, check-all, commit, push).

**Most compliant**
- `10/10` — intrn, 2026-07-29T19:30, 37 src, opened with `/awesomeharness`
- `9/10` — virality-pipeline 2026-07-29T01:53 (186 src), awesome-harness 2026-07-28T03:30 (100 src), virality-pipeline 2026-07-28T00:02, awesome-harness 2026-07-16T20:28

**Least compliant**
- `2/10` — virality-pipeline 2026-08-01T02:59: *"Quiero empezar a construir el S3 y a trabajar en los skills y así del pipeline. Primero hay que…"* — 0.4 h, 1 src write, no orient, no recall, no gate, no auditor, no check-all.
- `3/10` — harness-scout run, 2026-07-27T01:01
- `4/10` — Consulting 2026-07-30T16:20 *"Tengo la computadora de mi papá y quiero ir explorando las diferentes funciones…"*; Vividlist 2026-08-01T19:59 "previz dxf to pdf"
- `5/10` — health-system ×2, 2026-07-27T15:10: *"I want to continue with this project. I want to make the MVP and I just want to get it do[ne]"*

**What actually distinguishes them:**

1. **Repo type, not urgency.** Every 8–10/10 session is in an *engineered* repo (intrn, virality-pipeline, Vividlist, awesome-harness) with a north star, mulch, graphify and hooks installed. Every ≤5/10 session is in a repo without that scaffolding (Consulting, health-system, ENGL2328) or is a drive-by in one. **Compliance is a property of the repo, not of the agent's discipline.**
2. **Task size correlates positively, not negatively.** Sessions with >20 source writes score 7–10; sessions with ≤7 score 2–5. Small tasks skip the procedure — which is arguably correct (the skill has an escape hatch) but means the low rates above are partly "escape hatch fired", not "rule broken".
3. **`/awesomeharness` at the top is the single strongest predictor.** The 10/10 session opens with it. 64 invocations corpus-wide.
4. **Post-compaction continuations score HIGH, not low** — the three sessions opening with "This session is being continued…" / a compact handoff score 9, 9, 8. `precompact-handoff` is doing its job; cold-start is not the failure mode.
5. **Time of day: no signal.** Top scorers at h01, h03, h19, h20; bottom at h02, h15, h16, h19.

**Compliance decay WITHIN a session — confirmed, and it is severe.** Splitting each session's event timeline in half:

| Event | first half | second half | change |
|---|---|---|---|
| subagent source writes | 221 | 368 | **+66%** |
| auditor spawns | 76 | 38 | **−50%** |
| decompose/unit agents | 64 | 22 | **−66%** |
| commits | 137 | 164 | +20% |
| check-all | 24 | 29 | +21% |
| main-session source writes | 22 | 4 | −82% |

Normalised: **audits per source write fall from 0.31 to 0.10 — a 3× decay.** Decomposition falls from 0.26 to 0.06 — a **4× decay**. The second half of a long session builds twice as fast with a third of the verification. That is the mechanism by which these 34-to-193-hour sessions degrade, and it is precisely what re-invoking `/awesomeharness` mid-session is supposed to fix.

---

## 6. THE HONEST VERDICT

| Step | State | Why |
|---|---|---|
| **0 ORIENT** | **(a) running and valuable** | 77%; post-compaction sessions are the *best* performers, which is the payoff |
| **1 RECALL** | **(a) running and valuable** | 91%, highest in the procedure |
| **2 UNDERSTAND — graphify + codebase-first** | **(a) running** | 95% / 64% |
| **2 UNDERSTAND — repowise** | **(c) NOT RUNNING → CUT** | 1/22 = 5%, despite ~1,200 words of CLAUDE.md describing it every single session |
| **3 GATE** | **(d) unmeasurable** | only visible when written down; 73% of sessions wrote a verdict. Keep, but make the verdict a required artifact or stop claiming it |
| **4 DECOMPOSE** | **(a) running, degrading** | 68% of sessions, but 4× decay within a session; prior audit `08-decomposition-quality.md` found only 5/72 specs carry all five fields |
| **5 BUILD — delegate at all** | **(a) running and valuable** | 88% of source writes are delegated |
| **5 BUILD — "main NEVER writes"** | **(b) running and pointless as written** | guard covers Edit/Write only; 61% of main's writes route through Bash. Either enforce with a deny-rule / pre-commit hook or drop the claim |
| **5 BUILD — "→ codex subagent"** | **(c) NOT RUNNING → CUT** | 0 verifiable Codex writes; 48% of 102 forwards returned nothing; 17% hard-failed; 27 units evaporated, 19 were redone by a Claude agent |
| **6 VERIFY — auditor** | **(a) running and valuable** | 77%; `opus` respects read-only (1 write / 82), `code-audit-agent` does not (12 writes) |
| **6 VERIFY — check-all** | **(c) NOT RUNNING outside one repo** | 32% of sessions; 55 runs vs 301 commits (18%); one awesome-harness session accounts for the bulk of all runs. Make it default-on per repo or cut the claim |
| **7 PERSIST — commit** | **(a) running, off-contract** | 2.0 units/commit, 20-min median lag, 32% of sessions end dirty |
| **7 PERSIST — push** | **(c) not running** | 41% of sessions |
| **7 PERSIST — `git-sync.sh`** | **(c) not running → the multi-terminal guarantee is off** | 9% of commits |

### CUT list (delete-over-add)
1. **The repowise tier in `.claude/CLAUDE.md`** — 5% adoption, re-read every session as pure prompt tax. (Consistent with `06-tool-adoption.md`.)
2. **`codex:codex-rescue` as the default builder** — replace the "code writes → codex subagent" rule with "code writes → `code-unit-agent`", which is what actually happens and what actually produces verifiable diffs. Keep codex only as an explicit, opt-in rescue with a mandatory poll-until-done step; a forwarder that returns before its work exists is not a delegation.
3. **The "main NEVER writes feature code" claim** — either back it with a `deny` permission rule / pre-commit hook covering Bash, or downgrade it in the skill from a rule to an advisory. Right now it reads as enforced and is bypassed 61% of the time.

### FIX-don't-cut list
- **check-all**: turn `check-all-commit-gate` on by default in Vividlist / virality-pipeline / intrn. It works; it is just not installed where the code is.
- **`git-sync.sh`**: alias it over raw `git commit` in these repos, or the "never lose another terminal's work" property is fiction at 9% coverage.
- **Mid-session decay**: the 3–4× drop in audit and decomposition in the back half of a session is the single highest-yield fix. A turn-count or elapsed-time trigger that auto-re-injects `/awesomeharness` would target it directly.
- **`code-audit-agent` must be read-only**, like `opus.md` already is.
