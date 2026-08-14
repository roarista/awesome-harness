<p align="center">
  <img src="assets/hero-banner-v3.png" alt="awesome-harness">
</p>

<h1 align="center">awesome-harness</h1>

<p align="center">
  <b>A measured, local workflow harness for Claude Code and Codex.</b><br>
  Code maps · durable memory · deterministic checks · small agent workflows
</p>

---

## What is actually used

This is the current harness, not a catalogue of everything ever tried. The table below comes from 30 days of 6,426 real transcripts. “Core” means broadly useful and repeatedly used; “niche” means useful in narrower workflows; “on probation” means retained without enough adoption to call it established.

| Component | 30d calls | Repos | Verdict |
|---|---:|---:|---|
| graphify | 819 | 8 | core |
| mulch | 351 | 3 | core |
| check-all | 339 | 5 | core |
| repowise | 286 | 2 | niche |
| ytintel | 242 | 7 | niche |
| semgrep | 197 | 4 | core |
| git-sync | 166 | 5 | niche |
| l0.py | 150 | 1 | niche |
| skeleton | 142 | 3 | niche |
| finding.sh | 119 | 3 | niche |
| chains | 101 | 1 | niche |
| l1 | 85 | 2 | niche |
| retrieve.sh | 84 | 1 | niche |
| codemap.py | 81 | 2 | niche |
| route-model | 40 | 2 | niche |
| graphify-blast | 9 | 1 | on probation |
| memgraph | 6 | 1 | on probation |
| drift-replay | 3 | 1 | on probation |

The largest gap is search routing: grep ran 10,879 times and semgrep 197 times, a 55:1 ratio. The rule to prefer semgrep for structural searches is aspirational, not enforced. Grep remains the real default.

## Why this exists

Long coding sessions lose context, repeat discovery, and drift away from the requested outcome. `awesome-harness` provides a small set of local tools and conventions for orientation, retrieval, code mapping, delegated implementation, verification, and handoff.

The project now follows measured use. Components that earn repeated use stay prominent; specialized tools are documented as niche; low-use experiments remain on probation instead of being presented as proven defaults.

## Benchmarks

The current evidence base is the 30-day, 6,426-transcript usage census summarized above. It measures adoption, not causal productivity: a call count can show that a component is used, but it cannot prove that the component improved the outcome.

That distinction drove a large simplification. Measurement showed no positive effect from the old hook surface, so 41 hook entries were removed: 47 entries became 6. This counts registrations, not unique scripts. The cut removed redundant reminders, behavioral nudges, read guards, edit guards, session checkpoints, and compaction gates instead of continuing to claim unmeasured benefits.

The removed entries are no longer documented; they were largely ineffective at their stated goals.

After the cut, silent usage telemetry was restored as a seventh entry so future decisions can keep using real evidence. A narrowly scoped eighth entry now blocks duplicate `/awesomeharness` loads within a session; unlike the removed reminder hooks, it prevents a directly measured source of repeated context.

## Install

```bash
git clone https://github.com/<you>/awesome-harness
cd awesome-harness
./install.sh
./install-repo.sh /path/to/your/repo
```

Use `--dry-run` to inspect changes first. Restart Claude Code after installation so its environment and hook configuration reload.

### Codex adapter (opt-in)

The Codex adapter is installed separately and enabled per repository:

```bash
./install.sh --codex --dry-run
./install.sh --codex
./install-repo.sh --codex --dry-run /absolute/path/to/repo
./install-repo.sh --codex /absolute/path/to/repo
```

Review the merged hooks, trust the repository, and restart Codex. The compact adapter wires `PreToolUse`, `SubagentStart`, and `SubagentStop`: it protects the north star, blocks a narrow irreversible-command set, runs `check-all --fast` before commits only when `.check-all.json` exists, and gives each subagent one receipt retry. It deliberately omits repeated reminders and broad context injection.

The installer adds six compact coding skills: `awesomeharness`, `recall`, `codebase-first`, `code-decompose`, `check-all`, and `compact-prep`. Ponytail stays in global `AGENTS.md`; the former Caveman skill is not duplicated. Invoke `$awesomeharness` (also available from the slash-command list). Project `AGENTS.md` files should direct Codex to read any compact root `CLAUDE.md` router when that file carries the shared project procedure.

### Runtime pilot and rollback

Run the disposable runtime smoke test before enabling a real repository:

```bash
tests/test_codex_runtime_smoke.sh
```

The test uses a temporary repository and Codex home. To roll back, remove the awesome-harness command from the repository’s `.codex/hooks.json` and remove the repository policy marker, leaving unrelated hooks untouched.

## What you get

### The current eight hook entries

There are eight registrations backed by seven hook scripts. `northstar-protect` is intentionally registered twice because edits and shell commands have different matchers.

| Entry | Event / matcher | Behavior |
|---|---|---|
| codemap-inject | `SessionStart` | Injects the compact repository map. |
| skill-reinject-guard | `PreToolUse: Skill` | Blocks a duplicate `/awesomeharness` body within the same session. |
| northstar-protect | `PreToolUse: Write\|Edit\|MultiEdit` | Protects the repository’s north-star file from direct edits. |
| northstar-protect | `PreToolUse: Bash` | Applies the same protection to shell writes. |
| irreversible-pause | `PreToolUse: Bash` | Pauses recognized irreversible shell operations. |
| bash-write-fence | `PreToolUse: Bash` | Fences shell-based file writes. |
| claude-spawn-gate | `PreToolUse: Task\|Agent` | Routes builder and auditor work through the supported agent path. |
| harness-usage-telemetry | `PostToolUse` | Silently records relevant usage; emits 0 bytes. |

The count can otherwise look contradictory: the reduction was from 47 to 6 entries, telemetry restored the seventh, and the measured duplicate-skill guard added the eighth.

### What was removed, and why

On 2026-08-10, 41 hook entries were removed after measurement showed no positive effect on session outcomes; see the [audit](docs/audits/2026-08-04/simpler-harness.md).

Removed scripts: `reread-guard`, `token-discipline`, `caveman-discipline`, `graphify-blindspot`, `graphify-gate`, `understand-gate`, `main-edit-guard`, `now-gate`, `manifest-guard`, `recall-inject`, `northstar-inject`, `spawn-necessity`, `builder-fence`, `coding-routing-guard`, `post-agent-guard`, `phantom-edit-guard`, `advertised-command-guard`, `filesize-cap`, `check-all-commit-gate`, `session-checkpoint`, `compact-prep-gate`, `abs-path-nudge`, `harness-enforce`, and `precompact-handoff`.

The files remain in `hooks/` and can be re-registered individually; removal was from `settings.json`, not from disk.

### Secret-file deny rules

Nineteen rules in `permissions.deny` block reads of secret files, including `.env` variants, `*.pem`, `*.p12`, `*.pfx`, `id_rsa`, `.ssh/`, `.aws/`, `.gnupg/`, and service-account and credentials JSON files. The safe template `.env.example` remains readable. Because deny rules take precedence over allow rules, protected patterns are enumerated explicitly rather than expressed through negation. These rules are enforced by Claude Code itself, not by a hook.

### Orientation and memory

- `codemap.py` creates a compact repository index, and `codemap-inject` makes it available at session start.
- graphify is the primary structural code-map tool.
- mulch is the primary per-repository durable-memory tool.
- memgraph is still available for global memory, but its measured adoption puts it on probation.
- `l0.py`, `l1.py`, `retrieve.sh`, and `skeleton.py` support narrower retrieval and context-building workflows.

### Build and verification

- `codebase-first` asks whether existing code, the platform, or an installed dependency already covers the request.
- `code-decompose` turns the remaining work into small units with an explicit verification command.
- `check-all` composes repository checks with deterministic pre-ship checks.
- semgrep remains part of deterministic checking and structural search, despite the measured grep-routing gap.
- `git-sync.sh`, `finding.sh`, and the chain scripts support handoff, evidence storage, and preship workflows where those conventions are installed.

### Builders and auditors

Builders and auditors are the `codex` and `codex-audit` agents. Those agents are thin dispatchers: they call real GPT through the OpenAI Codex plugin companion, with the Codex CLI as the narrow fallback. They are not alternate Claude personas pretending to be GPT.

### Code intelligence

graphify is the core structural map. repowise remains a niche CLI for the workflows that use its risk, dead-code, and preship signals.

The repowise MCP server was removed. Only the CLI survives, currently consumed by `c5-dead.sh` and `c7-preship.sh`.

### Measurement and experiments

`harness-usage-telemetry` is silent instrumentation, and `tools/harness-usage.sh` summarizes its local log. `drift-replay`, `graphify-blast`, and memgraph remain on probation: available for the jobs they already serve, but not advertised as proven defaults.

## How it works (two layers)

- The global layer under `~/.claude/` contains hooks, skills, agents, and tools.
- A repository opts in through `install-repo.sh`, which installs its local orientation and policy files.

Most behavior is local and inspectable. Hooks cover only their declared events and matchers; the rest of the workflow is behavioral and verified through explicit checks, not described as mechanically guaranteed.

## Dependencies

The installer detects optional tools and degrades gracefully.

| Tool | Purpose |
|---|---|
| Python and Git | Harness scripts and repository operations |
| graphify | Core structural code map |
| mulch (`ml`) | Core per-repository memory |
| semgrep | Deterministic structural and security checks |
| repowise CLI | Niche dead-code and preship analysis |
| OpenAI Codex plugin companion | Dispatch to GPT-backed builders and auditors |

Install only the optional components used by your workflow. The usage table is a better guide than the size of the `tools/` directory.

## Safety & privacy

- Harness state and telemetry stay local.
- Usage telemetry is fail-open, can be disabled with `HARNESS_TELEMETRY=off`, and emits no model-context text.
- `install.sh` backs up Claude settings before merging its entries.
- Repository installation is explicit; the Codex adapter is separately opt-in.
- Open-source documentation uses aggregate, anonymized measurements and does not expose consuming repositories’ internal paths or business logic.

## Related

- [youtube-research](https://github.com/roarista/youtube-research) provides the `ytintel` workflow used for transcript and creator research.

## Status & contributing

This project is actively used and periodically cut back based on measured adoption. Contributions are welcome, but new hooks and tools should arrive with a way to measure whether they are used and whether they help. MIT licensed.
