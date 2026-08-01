# claudemd-trim — install into the repurposed launchd slot

Label: `com.ro.engineering-harness-audit`. Runs Monday 09:00.

## How the TCC problem is solved (read this first)

The trimmer reads `CLAUDE.md` out of repos under `~/Downloads`, which macOS TCC
protects. A launchd agent inherits **no** TCC grant, so running the trimmer directly
from launchd failed every week with:

```
PermissionError: [Errno 1] Operation not permitted:
  '/Users/rodrigoarista/Downloads/NOTION_WORKFLOW_MINING_2026-06-16.md'
```

**The old "step 0: grant Full Disk Access to `/usr/bin/python3`" instruction is
superseded and is NOT achievable.** `/usr/bin` is hidden in the Finder picker that
System Settings -> Privacy & Security -> Full Disk Access uses, so that binary cannot
be added at all. There is nothing to do manually.

**Current approach — borrow Terminal.app's grant.** Terminal.app already holds access
to `~/Downloads`. So launchd runs the `run-claudemd-trim.sh` shim, which itself
touches no protected path; it uses `osascript` to tell Terminal.app to run
`/usr/bin/python3 ~/.claude/tools/claudemd-trim.py`. The real work executes inside
Terminal, under Terminal's existing grant. Bonus: the weekly run is visible in a window.

**The shim must live OUTSIDE `~/Downloads`.** The canonical copy is in this repo, but
the plist points at `~/.claude/tools/run-claudemd-trim.sh` — launchd cannot even read a
script stored under `~/Downloads` (`/bin/bash: ...: Operation not permitted`, exit 126).
Re-copy it whenever the repo copy changes.

The one-time prompt you may see is macOS Automation ("… wants to control Terminal").
Approve it once (System Settings -> Privacy & Security -> Automation); no Full Disk
Access grant is involved.

## Install and load

```sh
cp ~/Downloads/awesome-harness/tools/claudemd-trim.py ~/.claude/tools/claudemd-trim.py
cp ~/Downloads/awesome-harness/tools/check-all/claudemd_drift.py ~/.claude/tools/check-all/claudemd_drift.py   # only if yours is older; the tool imports it as a sibling
cp ~/Downloads/awesome-harness/tools/launchd/run-claudemd-trim.sh ~/.claude/tools/run-claudemd-trim.sh && chmod +x ~/.claude/tools/run-claudemd-trim.sh
cp ~/Downloads/awesome-harness/tools/launchd/com.ro.engineering-harness-audit.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.ro.engineering-harness-audit 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ro.engineering-harness-audit.plist
launchctl kickstart -k gui/$(id -u)/com.ro.engineering-harness-audit   # fire it once now
launchctl list | grep engineering-harness-audit                        # want column 2 == 0
ls ~/engineering-harness/reports/claudemd-trim/                        # the REAL proof of a run
```

### Where to look when it fails (the launchd logs only prove DISPATCH)

The trimmer runs **inside Terminal.app**, not inside the launchd job. Its stdout/stderr
go to the Terminal window, never to the plist's `StandardOutPath`/`StandardErrorPath`.
So:

- `~/engineering-harness/reports/claudemd-trim.err.log` stays **empty even when the
  trimmer fails** (`wc -l` → 0 after a successful run too). It is not a health signal.
- `~/engineering-harness/reports/claudemd-trim.out.log` holds only the shim's one-line
  `dispatched … to Terminal.app` message — i.e. launchd successfully *asked* Terminal to
  run it. That says nothing about whether the trimmer itself worked.
- **Read trimmer failures in the Terminal window that pops open**, or from the report
  written under `~/engineering-harness/reports/claudemd-trim/`. A missing/stale report
  there is the real "it didn't run" signal.

The shim also guards itself: it exits 0 with a skip notice when not in an Aqua (GUI)
session, exits 1 if the trimmer is missing, and exits 1 if `osascript` is unavailable or
the dispatch fails. The Aqua check comes first, so a non-GUI context is always a clean
skip (exit 0) regardless of whether the trimmer is installed.

Reports are written to `~/engineering-harness/reports/claudemd-trim/`, deliberately
NOT `~/Downloads`, so the write side is outside the TCC-protected folder either way.
