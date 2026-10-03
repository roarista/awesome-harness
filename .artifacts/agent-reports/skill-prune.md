# Skill prune — zero-use skills (2026-10-03)

Ro-approved deletion of zero-use skills, keeping `code-decompose`.

## Removed
Skills: check-all, coursework-read, goal, harness-audit, harness-scout, notes-inbox, orient, recall, state-trim, treg, ui-console-debug.

- Repo copies `git rm -r`'d: `skills/check-all`, `skills/goal`, `skills/notes-inbox`, `skills/orient`, `skills/ui-console-debug`, `codex/skills/check-all`, `codex/skills/recall`. (No repo copy existed for coursework-read, harness-audit, harness-scout, state-trim, treg, ui-console-debug beyond the ones listed.)
- Installed copies moved (not deleted) to `~/.claude/skills-retired/2026-10-03/`: all 11 names from `~/.claude/skills/`, plus `check-all-codex`, `recall-codex`, `treg-codex` from `~/.codex/skills/`.
- `tools/check_all.sh`, the git pre-commit hook, and `.check-all.json` untouched — only the skill wrapper went. The `treg` MCP server is untouched — only the skill wrapper went.

## References fixed
- `skills/code-decompose/SKILL.md` (and synced `~/.claude/skills/code-decompose`): replaced `orient (`/orient`)` entry-condition reference with the underlying recall+understand+REUSE/ADAPT/REJECT description (no tool command exists to swap in).
- `codex/skills/code-decompose/SKILL.md` (and synced `~/.codex/skills/code-decompose`): replaced `~/.codex/skills/check-all/SKILL.md` pointer with the underlying tool command `tools/check-all/check_all.sh <repo>`.
- `skills/harness-intel/SKILL.md` (and synced `~/.claude/skills/harness-intel`): dropped the dead `"/harness-audit"` trigger-phrase alias from its description (harness-intel's own AUDIT mode already covers it).
- `~/.claude/CLAUDE.md`, `templates/global-CLAUDE.md`, `codex/AGENTS.md`, `tools/skill-drift.sh`, `install.sh`: checked, no skill-invocation references to deleted names — left identical. (install.sh and skill-drift.sh references to `check-all` are all to the `tools/check-all/` directory, which stays.)

## Verification
- `bash tools/skill-drift.sh` → `skill-drift: 11 copies in sync`
- `python3 tools/desc-bytes.py` → `desc-bytes: 0 over cap`
- Follow-up grep for `/orient`, `/check-all`, `/recall`, `state-trim`, `/goal`, `/harness-audit`, `/harness-scout`, `/notes-inbox`, `/treg`, `/ui-console-debug`, `/coursework-read` across `skills/` and `codex/skills/` (excluding `tools/check-all` path hits): no remaining invocation references.
- `~/.claude/skills` now: ast-mastering-hw, ast-reading, awesomeharness, code-decompose, compact-prep, harness-intel, humanizer, synced, youtube-research.
- `~/.codex/skills` now: awesomeharness, code-decompose, codebase-first, codex-primary-runtime, compact-prep, pdf, youtube-research.

## Commit
See git log for sha (staged only the files this task touched).
