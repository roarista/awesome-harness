# awesomeharness skill rewrite — 2026-10-02

VERDICT: shipped. Both skills rewritten to what is in force, installed live, drift check added.

## Changed
- skills/awesomeharness/SKILL.md (94 -> 109 lines): post-/compact framing (pasted summary = resume point);
  absolute router path ~/.claude/tools/route-model.sh + fmr outcome with FMR_HOME default and the 5 result
  values; Ro-named model override; spend rules; reset-credit consent; agent types (claude/codex; auditors;
  general-purpose + Explore blocked); one builder per unit (router's pick); cross-family audit + shared
  rubric (4 severities + VERDICT rule), loop until VERDICT != REJECT; spec CONTEXT/REUSE/CHANGE/GOAL/VERIFY
  with GOAL/NOT-GOAL/PROOF folded in; "Enforcement that is real": git pre-commit ratchet + check-all --fast
  (bypass only with Ro's yes) and all 25 registered hook scripts grouped blocking/injecting/nudge;
  reinjection-guard line now true (re-invoking reloads by design); "26 gates" count removed; l1/skeleton absolute.
- codex/skills/awesomeharness/SKILL.md (84 -> 103): same content in Codex vocabulary; kept the router
  paragraph (added outcome values); l1/skeleton -> ~/Downloads/awesome-harness/tools/ (absent from ~/.codex/tools);
  native Codex hook adapter described from codex/hooks/pre_tool_use.py + subagent.py (recursive forced
  removal, forced push, reset --hard, clean -fd; it has no SQL check, so none claimed).
- tools/skill-drift.sh (34 lines): diffs repo skills vs ~/.claude/skills and ~/.codex/skills; args = skill
  names; CLAUDE_SKILLS_DIR / CODEX_SKILLS_DIR override; skips legacy codex/caveman; exit 1 on drift/missing/no match.
  Not wired into check-all: check_all.sh is a per-repo gate that runs in every repo, where a live-skill
  diff is wrong. Documented in both skill footers instead.

## Verification
1. wc -l: 109 / 103 (<=110).
2. skill-drift.sh awesomeharness: rc=1 before install (165/131 lines differ), rc=0 after; mutated temp copy
   (1 char, Claude) rc=1; appended byte (Codex) rc=1; restored rc=0; unknown skill name rc=1.
3. grep "Codex builder per unit" / "26" / "no HIGH/CRITICAL" (and lowercase): 0 in both.
4. Every ~/ path in both skills passes test -e (17 paths). Hook names in the skill == the registered set
   (25/25, both directions).
5. Hook claims spot-checked against source: graphify-gate re-arms at SessionStart; compact-prep-gate keys on
   .now.md mtime only; irreversible-pause covers recursive forced rm / forced push / destructive SQL;
   spawn-gate blocks general-purpose + Explore.

## Risk / open
- Full `skill-drift.sh` (no args) exits 1 on PRE-EXISTING drift: claude check-all, code-decompose,
  compact-prep, goal. Those live copies were edited 2026-10-02, after the repo copies, so they were NOT
  overwritten. Ro decides the direction (pull live -> repo, or re-run install.sh).
- The skill groups hooks by behavior (dense lines) instead of one line per hook, to stay <=110.
- Some hook messages still carry retired policy (coding-routing-guard, route-only-gate, claude-spawn-gate);
  the skill says CLAUDE.md + router win. Hooks were left untouched, per the brief.
- irreversible-pause false-positived on this report's heredoc text (matches the rule-value audit row 5).
- Router probe ID 8c470094 was left unrecorded (a probe, not a launch).
- Backups: $CLAUDE_JOB_DIR/tmp/skill-backup/{claude,codex}-awesomeharness.SKILL.md
