#!/usr/bin/env node
// PostToolUse hook for SendUserFile.
// Purpose: guarantee the full ABSOLUTE path of every delivered file is surfaced
// back into the assistant's context so it is always relayed to the user in plain
// text (no ellipsis, no truncation). Read-only; fails silently — never blocks.

const path = require('path');

let input = '';
const timer = setTimeout(() => process.exit(0), 4000);
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => (input += c));
process.stdin.on('end', () => {
  clearTimeout(timer);
  try {
    const data = JSON.parse(input || '{}');
    const cwd = data.cwd || process.cwd();

    // Prefer the absolute paths the tool actually delivered (tool_response),
    // fall back to the requested paths (tool_input), resolved against cwd.
    const resp = data.tool_response || data.tool_result || {};
    const reqInput = data.tool_input || {};

    let files = [];
    if (Array.isArray(resp.files)) {
      files = resp.files.map((f) => (typeof f === 'string' ? f : f && f.path)).filter(Boolean);
    }
    if (files.length === 0 && Array.isArray(reqInput.files)) {
      files = reqInput.files;
    }
    if (files.length === 0) process.exit(0);

    const abs = files.map((f) => (path.isAbsolute(f) ? f : path.resolve(cwd, f)));
    const lines = abs.map((p) => `  ${p}`).join('\n');
    const message =
      'REMINDER: relay these FULL ABSOLUTE paths to the user verbatim in your reply ' +
      '(no ellipsis, no abbreviation, one per line):\n' +
      lines;

    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PostToolUse',
          additionalContext: message,
        },
      })
    );
  } catch (e) {
    // Never block the deliverable on a hook error.
  }
  process.exit(0);
});
