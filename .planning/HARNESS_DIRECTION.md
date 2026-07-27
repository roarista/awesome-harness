# Harness direction — Ro brain-dump 2026-07-23 (decisions pending)

Six threads. [FIX] = concrete, ready to execute on go. [DECIDE] = needs Ro's fork.

## 1. Gemini models (INFO) — gemini subagent now LIVE (he authed)
- Text models (2.5/3.x flash/pro) → usable NOW via `gemini` subagent + tools/gemini-opencode.sh.
- Veo 3.1 (video gen), Gemini embeddings, robotics: DIFFERENT API surfaces (generateVideo/embedContent),
  NOT chat-completions — the opencode text bridge can't call them. Likely need the paid API key, not the
  free CLI-OAuth grant. Verdict: don't wire until a concrete need; embeddings would need a tiny direct-API script.

## 2. Semgrep (INFO+FIX) — now enforced (7298d11)
- Used ONLY inside check-all CHECK G (`semgrep --config auto --error --quiet`), fails the gate on findings.
- Max-out options (offer): add a repo-local `.semgrep.yml` with targeted rules; run `semgrep --config auto`
  ad-hoc; or a pre-commit hook. Not auto-added (YAGNI until he wants per-repo rules).

## 3. Remote control (FIX-pending-info)
- `remoteControlAtStartup: true` ALREADY set in ~/.claude/settings.json:329. Config is fine.
- So breakage is elsewhere (account mismatch? headless/bg sessions don't expose remote control?).
  NEED from Ro: does `/remote-control` error, or does the session just not appear in the app? which account
  is `claude` logged into vs the app?

## 4. Harness auditor never runs (FIX) — ROOT CAUSE FOUND
- launchd jobs (scout Sun18:00, audit Mon09:00) + a cron (Sun03:00) fire while Mac is ASLEEP.
- No `pmset repeat wake` scheduled → machine never wakes for them; logs are EMPTY.
- FIX (recommend): `sudo pmset repeat wake MTWRFSU 08:55:00` (or per-day) so Mac wakes just before the run;
  keep launchd (catches up on wake); DROP the duplicate cron (cron does NOT catch up on wake).
- Suggest-only is ALREADY enforced (run-harness-scout.sh delegates report write; prompt says do NOT edit).

## 5. /goal-centric harness + session-start boot skill (DECIDE)
- Ro: /goal >> North Star for detailed, interruptible, success-criteria-driven work. Wants to lean into slash cmds.
- Wants a `/boot` (session-start) skill that invokes the harness pieces (codebase-first etc.) so CLAUDE.md trims down.
- RECOMMEND: keep North Star as the 1-line destination anchor (compaction survival); make /goal the DEFAULT
  execution loop for real work. Build a thin `/boot` skill that: loads codebase-first + recall + states NOW.
  Trim CLAUDE.md to a pointer that says "run /boot". DECISION: build /boot? how much to trim CLAUDE.md?

## 6. Hooks: keep or remove? (DECIDE)
- RECOMMEND KEEP the enforcement hooks (msg-discipline, now-gate, main-edit-guard, builder-fence, semgrep) —
  they're the load-bearing guarantees that survive even when a skill isn't invoked. Move DISCOVERABILITY
  (codebase-first, routing reminders) into /boot + skills; keep ENFORCEMENT in hooks. Hooks = floor, skills = workflow.
