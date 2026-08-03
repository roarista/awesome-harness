# Retrieval routing — state the intent, then search

Front door: `REPO=<repo> tools/retrieve.sh <intent> <query> [scope]`.
Basis: `docs/audits/2026-08-02/10-search-intent.md` (census, 1,456 episodes / 4,424 searches).
No intent, or an unknown one, prints this table and exits 2. It never guesses.

| intent | winning combination | measured success | receipt it owes you |
|---|---|---|---|
| `name` | vocab dump from `graphify-out/graph.json` (fallback: source-derived def/class list) | 46.2% today | `id \| label \| file:line` you **copy**, never retype |
| `enumerate` | committed rule → `c3-enumerate.sh`; else a generated+validated semgrep rule | 41.9% today (worst) | a **COUNT**, never a `\| head` list |
| `exists` | `grep -rn` with a **quoted** `--include` + printed scope | 51.5% today | zero **plus** scope, file count, exact command |
| `blast` | label→node **id**, then `c1-blast.sh` (graphify affected ∪ semgrep importers) | 48.5%, asked only 2.3% | union size + which leg produced it |
| `slice` | `grep -n -A30 '<anchor>' <file>` — **grep wins, kept** | 69.8% | non-empty lines |
| `verify` | `grep -n '<new string>' <scope>` — **grep wins, kept** | 77.1% (best fit in corpus) | non-empty lines |
| `history` | `git log --grep` + `git log -S` — **git wins, kept** | 59.4% | commit hashes |
| `diagnose` | none. Prints an honest non-answer and the 3-step manual path | 49.5%, 35.8% flail | that no tool wins this |

`name` + `enumerate` + `exists` are ~50% of episodes and burn ~3.3M tokens on searches that
never resolve. `slice` / `verify` / `history` are the cheap, successful corner — routing them
away from grep/git would be a regression, so the router does not.

## Three invariants, enforced inside the script

1. **`--include` is always single-quoted.** 137 measured searches (3.1%) never ran because zsh
   glob-expanded `--include=*.py`; 49 of those produced a believed false negative.
2. **One search per invocation.** No `echo === ; cmd1; cmd2` bundles — 634 measured searches
   (14.5%) hid a completely empty sub-section inside output that read as successful.
3. **3-attempt circuit breaker.** A sentinel per `(intent,query)` under `/tmp/chains/<repo>/`;
   the 4th call refuses and tells you to change instrument (exit 4). Override with
   `RETRIEVE_ATTEMPT=1`; reset with `rm /tmp/chains/<repo>/.attempts-<key>`.

## No route may return a silent empty

Every route prints a `PREFLIGHT` line proving the tool ran (rules validated / graph present /
grep executed), and an explicit `FALLBACK:` line whenever a primary leg comes back empty or a
delegated chain exits non-zero. `c1-blast` exiting 3 is reported as a **chain failure**, never
as "nothing depends on it". Verdicts are capped at 14 lines by `_lib.sh`; the last line is
always `FULL: <path>`.

## Known gotchas

- `graphify affected` on a **label** returns `No affected nodes found` — a false negative. The
  `blast` route resolves label→id first and says so; ambiguous stems pick the first fuzzy match,
  so check the printed id.
- `graphify`'s `uses` edge is 27% precision — nothing here builds on it. In awesome-harness all
  178 `imports` edges dangle (repo-specific); `graph_gate()` (R-0b) catches that.
- The generated `enumerate` rule is python-only; on 0 hits it cross-checks with a literal grep
  count and says so.
