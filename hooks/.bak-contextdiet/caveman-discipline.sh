#!/bin/sh
# Per-turn contract — injected at SessionStart. Ro reads ONLY the final message.
cat <<'EOF'
PER-TURN CONTRACT (Ro reads ONLY your final message of each turn):
1) INTERMEDIATE output: NONE. Emit ZERO prose between/alongside tool calls — not a
   sentence, not a few words. No "Let me…", no preamble, no narrating, no status
   lines. Call tools silently. (Writing to FILES is fine; writing to the CHAT before
   the final message is not.) NOTE: no hook can physically block chat prose — there is
   no hook event on model text — so this is on YOU to obey; nothing will catch a slip.
   URGE-TO-NARRATE OUTLET: when a tool result (esp. a returning sub-agent) makes you
   want to write "here's what came back…", append ONE terse caveman line to
   $CLAUDE_JOB_DIR/tmp/pending.md instead — e.g. "- agentA: distiller 97.8%, use for
   chart". At turn end READ pending.md and expand every line into the final message.
2) FINAL message: the opposite — thorough, self-contained, covering the WHOLE turn (he
   did not read the middle): what changed and why, results + verification, what is
   pending, decisions needed. It must stand alone.
3) COMPACTION-SAFE CLOSE, every turn — the `compact-prep` skill owns this ritual:
   update `.now.md` (NOW / LAST_VERIFIED / NEXT, <=5 lines) and the STATE resume point,
   sync durable memory / mulch, and state in the final message what was saved and the
   exact resume point. Treat every turn boundary as a possible compaction — nothing
   important may live only in chat.
4) ORIENTATION, before deep work: read `.northstar.md` + `.now.md` + the STATE resume
   point. Missing north star -> ask Ro for the one-sentence destination first.
Precedence: this OVERRIDES ponytail brevity for the FINAL summary only (thorough).
Ponytail still governs code. Intermediate chat text is banned outright.
EOF
