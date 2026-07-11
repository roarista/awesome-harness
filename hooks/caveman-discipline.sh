#!/bin/sh
# Message discipline — injected at SessionStart. Ro reads ONLY the final message.
cat <<'EOF'
MESSAGE DISCIPLINE (Ro reads ONLY your final message of each turn):
- INTERMEDIATE output: NONE. Emit ZERO prose between/alongside tool calls — not a
  sentence, not a few words, nothing. No "Let me…", no preamble, no narrating, no
  status lines. Just call tools silently. (Writing to FILES is fine; writing to the
  CHAT before the final message is not.) The only text you produce in a turn is the
  final message. NOTE: no hook can physically block chat prose — there is no hook
  event on model text — so this is on YOU to obey; nothing will catch a slip.
- URGE-TO-NARRATE OUTLET: when a tool result (esp. a returning sub-agent) makes you
  want to write "here's what came back…", DO NOT write it to chat. Append ONE terse
  caveman line to your turn-scratch file ($CLAUDE_JOB_DIR/tmp/pending.md) — e.g.
  "- agentA: distiller 97.8%, use for chart". At turn end, READ pending.md and
  expand every line into the single thorough final message. The big idea waits for
  the end; only the caveman reminder is written mid-turn, and to a FILE not chat.
- WAIT FOR AGENTS — NO PREMATURE / DOUBLE SUMMARY: if you spawned sub-agent(s)
  whose results you will report, DO NOT write a final summary before they return.
  Wait for ALL of them to come back, THEN emit ONE consolidated summary. Never
  summarize twice (once when you spawn them, again when they land) — that doubles
  the context for the same information. Prefer running agents to completion within
  the turn over backgrounding-then-pre-summarizing. End the turn early with a
  partial message ONLY if Ro told you to. Otherwise hold the summary until every
  agent is back, then say it once.
- FINAL message: the opposite — a complete, self-contained summary of the WHOLE
  turn (he did not read the middle): what changed and why, results + verification,
  what is pending, decisions needed. Thorough, stands alone.
- EVERY turn ends compaction-safe (run the compact-prep ritual before you stop):
  update `.now.md` (NOW / LAST_VERIFIED / NEXT, <=5 lines) and the STATE resume
  point, sync durable memory / mulch, and in the final message state what was
  committed to memory/mulch and the exact resume point. Treat every turn boundary
  like a possible compaction — nothing important may live only in chat.
- Precedence: this OVERRIDES ponytail brevity for the FINAL summary only (thorough).
  Ponytail still governs code. Intermediate chat text is banned outright.
EOF
