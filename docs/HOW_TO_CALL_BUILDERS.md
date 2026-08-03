# How to call the builders

**TRAP:** `codex:codex-rescue` (the plugin agent) is a FORWARDER — 84 transcripts,
ZERO source writes ever, 48% of its receipts never resolved. It returns a task id,
not a diff. **Never route a build there.** The real builder is the `codex` agent
(`~/.claude/agents/codex.md`), a thin wrapper over the synchronous `codex exec` CLI.

## 1. BUILD — `codex` (writes files, prints a diff)

Subagent: `Agent(subagent_type="codex", prompt="<CONTEXT/CHANGE/GOAL/VERIFY spec>")`

Raw CLI (what the agent actually runs — usable directly from Bash):

    codex exec --sandbox workspace-write --skip-git-repo-check --cd <repo> "<full unit spec>"

Verified 2026-08-02 in `/tmp/codextest`: authenticated, edited `m.py`
(`return a-b` → `return a+b`), printed a real unified diff, 28,614 tokens.

Failure modes:
- **Writes stray harness files.** In the test it also created `.planning/STATE.md`
  and `.now.md` in the target dir (it obeys the global CLAUDE.md). Check
  `git status --porcelain` after every run and discard extras.
- No `timeout` binary on this Mac — don't wrap the call in `timeout`; use the
  Bash tool's own `timeout` parameter (runs take 1-4 min).
- If it errors or emits no diff, the agent falls back to Edit/Write. A run with no
  file change is a FAILED unit, not a done one.

## 2. AUDIT — `opus` (reads, never edits)

    Agent(subagent_type="opus", prompt="Audit this diff against its spec: <spec> <diff>")

Use after every codex unit. It cannot fix what it finds — hand findings back to codex.
Failure mode: it will happily audit a spec you forgot to paste; always include the spec.

## 3. SECOND OPINION — `gemini` (real Gemini 2.5, non-Anthropic voice)

    Agent(subagent_type="gemini", prompt="<task>")

Raw CLI (`~/bin/gemini` → `opencode run` with the gemini-auth plugin):

    gemini -p "<task>" [-m gemini-2.5-pro|gemini-2.5-flash] [--dir <repo>] [-f <img>]

Verified 2026-08-02: `gemini -p "..."` returned `GEMINI_OK google/gemini-2.5-pro`.
Gemini has its own Read/Bash/Edit inside OpenCode — tell it to *look*, don't paste files.

Failure modes: without `--dir` it is stuck in the current cwd; prompts over a few KB
must go via stdin (argv ~1MB ceiling); multi-image calls take minutes — don't abort.

## Which one

| Need | Use |
|---|---|
| Write/change code | `codex` |
| Check the code that was written | `opus` |
| Non-Claude opinion, huge-context read, vision/video, scraping | `gemini` |
| Council (2 models) | `opus` (low effort) + Codex 5.5; optional 3rd: `gemini` |
