#!/bin/sh
# Caveman message discipline — injected at SessionStart.
# Ro reads ONLY the final message of each turn. Everything else is wasted tokens.
cat <<'EOF'
MESSAGE DISCIPLINE (Ro reads ONLY your final message of each turn):
- INTERMEDIATE output (any text you emit alongside/between tool calls): maximum
  terseness — a few words, or nothing. No "Let me…", no preamble, no narrating
  what you are about to do or just did. Just act. Caveman: few word do trick.
- FINAL message of the turn: the opposite. A complete, self-contained summary
  of the WHOLE turn — what changed and why, results + verification, what is
  pending, and any decision needed from Ro. It must stand alone (he did not read
  the middle). Embed the compact-prep ritual: state what was committed to memory
  / mulch and the resume point.
- Precedence: this OVERRIDES ponytail brevity for the FINAL summary only (that one
  is meant to be thorough). Ponytail still governs code and all intermediate text.
EOF
