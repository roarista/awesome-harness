# Skill resync — 2026-10-03

Trigger: `tools/skill-drift.sh` flagged live ~/.claude/skills/{check-all,code-decompose,compact-prep,goal}/SKILL.md (all mtime 2026-10-02 11:25).
Method: diffed every live copy against every historical repo commit of skills/<name>/SKILL.md.
Backup of the live copies: $CLAUDE_JOB_DIR/tmp/skill-backup-2/<name>/SKILL.md (/Users/rodrigoarista/.claude/jobs/116ee60d/tmp/skill-backup-2/).

| skill | live copy = | decision | reason |
|---|---|---|---|
| check-all | byte-identical to 86d0d85 (2026-07-12) | reinstall repo → live | older restore; it has no YAML frontmatter and is missing later semgrep/REUSE work (459e314..47d4880) |
| code-decompose | byte-identical to 86d0d85 (2026-07-12) | reinstall repo → live, plus a fix in the repo | older restore. In the repo copy, 5 stale `codebase-first` references (that skill was merged into `orient`) now point to `orient` |
| compact-prep | byte-identical to ca24f7d (2026-07-16) | reinstall repo → live | older restore; it lacks the MINIMUM PATH, the git-sync and the turn-files work (1c6152c..b211e84) |
| goal | byte-identical to 86d0d85 (2026-07-12) | reinstall repo → live | older restore; it lacks the REUSE field and the ml-record pointer (cef88ce, 47d4880) |

None of the live copies held new work, so nothing was copied from live into the repo.

Every path the repo versions reference exists. Checked: bash -n on check_all.sh (~/.claude and repo copies), graphify-blast.sh, pre_compact_global.sh and git-sync.sh; py_compile on turn-files.py, state-distiller.py and goal_judge.py; `turn-files.py --help` runs; the ml, graphify and semgrep commands are on PATH. jscpd is not installed, but check-all already skips it with a note (it is optional).

Codex copies: codex/skills/{check-all,code-decompose,compact-prep} are identical to ~/.codex/skills. `goal` has no Codex copy on either side. `codebase-first` still exists as a Codex skill, so the Codex code-decompose was left unchanged.

Result: `bash tools/skill-drift.sh` reports "16 copies in sync", exit 0.

Not fixed (out of scope): code-decompose line 49 says "builder is always the codex CLI". That contradicts the router-decides rule in the global CLAUDE.md.
