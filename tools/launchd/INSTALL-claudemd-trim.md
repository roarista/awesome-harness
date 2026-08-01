# claudemd-trim — install into the dead launchd slot (STAGED, NOT LOADED)

Nothing here has been applied. The job is currently **UNLOADED**.

## Step 0 (REQUIRED, manual, do this first)

System Settings -> Privacy & Security -> **Full Disk Access** -> add `/usr/bin/python3`.

This is not optional and not a fallback. The traceback in
`~/engineering-harness/reports/launchd.err.log` runs under
`/Library/Developer/CommandLineTools/.../python3.9/pathlib.py` — i.e. **the denied
process was already `/usr/bin/python3`**. Without the grant this job cannot read
`~/Downloads/<repo>/CLAUDE.md` and will keep exiting 1, no matter which Program the
plist names.

## Step 1 — install and load

```sh
cp ~/Downloads/awesome-harness/tools/claudemd-trim.py ~/.claude/tools/claudemd-trim.py
cp ~/Downloads/awesome-harness/tools/check-all/claudemd_drift.py ~/.claude/tools/check-all/claudemd_drift.py   # only if yours is older; the tool imports it as a sibling
cp ~/Downloads/awesome-harness/tools/launchd/com.ro.engineering-harness-audit.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.ro.engineering-harness-audit 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ro.engineering-harness-audit.plist
launchctl kickstart -k gui/$(id -u)/com.ro.engineering-harness-audit   # fire it once now
launchctl list | grep engineering-harness-audit                        # want column 2 == 0
tail -20 ~/engineering-harness/reports/claudemd-trim.err.log
ls ~/engineering-harness/reports/claudemd-trim/
```

## What was actually wrong (verified, not guessed)

`~/engineering-harness/reports/launchd.err.log` (80 lines, the only failure record)
contains exactly one traceback, repeated:

```
PermissionError: [Errno 1] Operation not permitted:
  '/Users/rodrigoarista/Downloads/NOTION_WORKFLOW_MINING_2026-06-16.md'
```

The strings `timeout` and `Not logged in` appear **nowhere** in that log. The real
cause is macOS TCC. The failing frames run under
`/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py`
— that is `/usr/bin/python3`, so **that** binary is the one lacking Full Disk Access for
`~/Downloads`, not the `bin/harness` bash wrapper that invoked it.

## Residual risk I could NOT verify without loading the job

Whether the step-0 Full Disk Access grant is sufficient. The claim that
`com.ro.harness-coach` proves `/usr/bin/python3` "already carries the grant" is
DISPROVEN by the log above: the denied process was `/usr/bin/python3` itself. Do step 0,
then kickstart once and read the err log before trusting the schedule.

Reports are written to `~/engineering-harness/reports/claudemd-trim/`, deliberately
NOT `~/Downloads`, so the write side is outside the TCC-protected folder either way.
