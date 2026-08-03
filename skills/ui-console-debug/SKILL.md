---
name: ui-console-debug
description: Debug web UIs live in Ro's Chrome — read console errors, reload, screenshot, iterate until zero errors. Use for any "no se ve nada / está roto / está trabado" report about a local web page.
---

<!-- MIRROR: copy of ~/.claude/skills/ui-console-debug/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/ui-console-debug/SKILL.md skills/ui-console-debug/SKILL.md -->

# UI Console Debug Loop

Debug a web page the way a human does with F12, but automated through the
claude-in-chrome MCP tools. Never guess at a UI bug from source alone — read
the browser's own error first.

## Preconditions

- Load tools in ONE ToolSearch call:
  `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__read_console_messages,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_network_requests`
- Call `tabs_context_mcp` first (createIfEmpty: true). Never reuse tab IDs from old sessions.

## The loop

1. **Navigate** to the page URL (or reuse the tab if Ro is already on it).
2. **Read console**: `read_console_messages` with a pattern like
   `error|Error|declared|undefined|failed|404`. NOTE: tracking starts at first
   call — if messages look stale (old timestamps) or empty, hard-reload with
   `computer` key `cmd+shift+r`, wait 2-3s, read again.
3. **Screenshot** (`computer` action screenshot) — visual state is a second,
   independent signal; a page can be error-free and still visually wrong.
4. **Diagnose from the REAL error text**, not from expectations. Classic traps:
   - Two classic `<script>` files declaring the same top-level `const` →
     "Identifier X has already been declared" → wrap each file in an IIFE.
   - Stale cache → always hard reload (cmd+shift+r), never plain reload.
5. **Fix the source**, `node --check` any edited JS, hard-reload, re-read
   console. Repeat until console shows zero errors.
6. **Verify visually** with a final screenshot (save_to_disk: true so Ro gets
   the absolute path). If interaction matters (zoom, drag), actually perform
   it via `computer` (scroll/click/drag) and screenshot the result.
7. For network issues (404 assets, CORS): `read_network_requests`.

## Rules

- Zero console errors + a screenshot showing the expected UI = done. One or
  the other alone is NOT verification.
- `node --check` / `require()` canNOT catch cross-script global collisions or
  DOM/runtime errors — browser verification is mandatory for viewer changes.
- Report to Ro with the exact error text found and the screenshot path
  (full absolute path).
- Don't trigger alert()/confirm() — they freeze the extension.
