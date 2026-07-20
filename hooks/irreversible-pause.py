#!/usr/bin/env python3
"""PreToolUse hook — hard STOP on IRREVERSIBLE Bash ops (bypassPermissions guard).

This machine runs Claude Code in bypassPermissions mode: dangerous shell
commands execute with no confirmation. This gate converts a tight, denylist-only
set of irreversible operations into a forced reconsideration — the agent must
confirm with Ro, then re-arm by re-running the command prefixed with the
override token.

Design principle: DENYLIST ONLY, tight, minimize false positives. A cry-wolf
gate gets ignored, so we cover exactly three families:
  1. Recursive force delete  (rm with combined -r + -f flags)
  2. Force push              (git push with --force / -f / --force-with-lease)
  3. Destructive SQL / DB reset (drop table / drop database / truncate table)

Override / re-arm: any command containing the literal substring
`CLAUDE_ALLOW_IRREVERSIBLE=1` is always allowed.

Deny protocol: exit 2 + reason on stderr → Claude Code blocks the call and
feeds the reason back to the model. Fail-open on any internal error (exit 0) —
this must never wedge the session.
"""
import json
import re
import sys

OVERRIDE = "CLAUDE_ALLOW_IRREVERSIBLE=1"

# 1. rm with BOTH recursive and force flags — handled by _rm_is_recursive_force
#    below (parses the clustered short flags; handles -rf, -fr, -r -f, -Rf, -rfv).

# 2. git push carrying a force flag.
GIT_FORCE_PUSH = re.compile(
    r"\bgit\b[^\n;|&]*\bpush\b[^\n;|&]*(?:--force-with-lease|--force|(?<![\w-])-f\b)",
)

# 3. Destructive SQL / DB reset (case-insensitive) — only counts when an actual
#    DB client is being invoked, so prose or an LLM prompt containing "drop table"
#    (e.g. `codex exec "...drop table..."`, a commit message, an echo) does NOT trip
#    the guard. This killed a real cry-wolf that blocked commits + subagent spawns.
SQL_DESTRUCTIVE = re.compile(
    r"\b(?:drop\s+table|drop\s+database|truncate\s+table)\b",
    re.IGNORECASE,
)
DB_CLIENT = re.compile(
    r"\b(?:psql|mysql|mariadb|sqlite3?|mongosh?|clickhouse-client|cockroach|"
    r"prisma|sequelize|alembic|dbmate|flyway|mysqldump|pg_dump)\b",
    re.IGNORECASE,
)

# 4. Other destructive filesystem, repository, disk, and cloud operations.
GIT_RESET_HARD = re.compile(r"\bgit\b[^\n;|&]*\breset\s+--hard\b")
FIND_DELETE = re.compile(r"\bfind\b[^\n;|&]*\s-delete\b|\bfind\b[^\n;|&]*\s-exec\s+rm\b")
TRUNCATE_ZERO = re.compile(r"\btruncate\s+-s\s+0\b")
DD_OF = re.compile(r"\bdd\b[^\n;|&]*\bof=")
MKFS = re.compile(r"(?:^|[\s;|&])mkfs(?:\.[\w-]+)?\s")
AWS_S3_RM_RECURSIVE = re.compile(r"\baws\s+s3\s+rm\b[^\n;|&]*--recursive\b")
GCLOUD_DELETE = re.compile(r"\bgcloud\b[^\n;|&]*\bdelete\b")
RCLONE_DELETE = re.compile(r"\brclone\s+(?:delete|purge)\b")


def _dequote(cmd: str) -> str:
    """Blank out single/double-quoted spans so a trigger word living inside a
    quoted ARGUMENT to another program (codex/claude/glm/echo "... rm -rf ...")
    is not mistaken for a command. A real `rm -rf "/a b"` keeps its flags OUTSIDE
    the quotes, so it still matches."""
    return re.sub(r'"[^"]*"|\'[^\']*\'', " ", cmd)


def _rm_is_recursive_force(cmd: str) -> bool:
    """True iff a single `rm` invocation carries BOTH recursive AND force —
    via short-flag clusters (-rf, -fr, -Rf, -r -f), long flags
    (--recursive / --force), or any mix of the two."""
    for m in re.finditer(r"\brm\b([^\n;|&]*)", cmd):   # args up to a cmd separator
        args = m.group(1)
        short = "".join(re.findall(r"(?<!-)-([a-zA-Z]+)\b", args))  # clusters, not --long
        recursive = "r" in short or "R" in short or re.search(r"(?<!\S)--recursive\b", args)
        force = "f" in short or re.search(r"(?<!\S)--force\b", args)
        if recursive and force:
            return True
    return False


def _git_clean_is_destructive(cmd: str) -> bool:
    """True iff one git-clean invocation has force plus d or x flags."""
    for m in re.finditer(r"\bgit\b[^\n;|&]*\bclean\b([^\n;|&]*)", cmd):
        short = "".join(re.findall(r"(?<!-)-([a-zA-Z]+)\b", m.group(1)))
        if "f" in short and ("d" in short or "x" in short):
            return True
    return False


def matches_denylist(cmd: str) -> bool:
    # rm + force-push are SHELL-STRUCTURE ops: match on the dequoted command so a
    # trigger buried in a quoted argument to codex/echo/git-commit doesn't fire.
    bare = _dequote(cmd)
    if _rm_is_recursive_force(bare):
        return True
    if GIT_FORCE_PUSH.search(bare):
        return True
    if _git_clean_is_destructive(bare):
        return True
    if any(pattern.search(bare) for pattern in (
        GIT_RESET_HARD, FIND_DELETE, TRUNCATE_ZERO,
        DD_OF, MKFS, AWS_S3_RM_RECURSIVE, GCLOUD_DELETE, RCLONE_DELETE,
    )):
        return True
    # destructive SQL only when a real DB client is invoked OUTSIDE quotes
    # (dequoted cmd), while the SQL keyword may live anywhere (original cmd) - so a
    # commit message / prose mentioning a client + the SQL keyword does NOT trip it.
    if DB_CLIENT.search(_dequote(cmd)) and SQL_DESTRUCTIVE.search(cmd):
        return True
    return False


def deny() -> None:
    sys.stderr.write(
        "BLOCKED: this is an IRREVERSIBLE operation (recursive force-delete, "
        "force push, or destructive SQL/DB reset) and cannot be undone. "
        "STOP and confirm with Ro before proceeding. After he approves, re-run "
        "the EXACT command prefixed with `" + OVERRIDE + " ` to re-arm and "
        "allow it through this guard."
    )
    sys.exit(2)


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest()
        return
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") != "Bash":
        return
    cmd = str((data.get("tool_input", {}) or {}).get("command", ""))
    if OVERRIDE in cmd:
        return  # override / re-arm — always allow
    if matches_denylist(cmd):
        deny()


def _selftest() -> None:
    destructive = (
        "rm -rf scratch", "git push --force", "psql -c 'drop table users'",
        "git reset --hard", "git clean -fd", "git clean -fx", "find . -delete",
        "find . -exec rm {} \\;", "truncate -s 0 file", "dd of=/dev/disk9",
        "mkfs.ext4 /dev/disk9", "aws s3 rm s3://bucket --recursive",
        "gcloud projects delete test", "rclone delete remote:path", "rclone purge remote:path",
        "git push origin --force", 'psql -c "drop table x"',
    )
    for command in destructive:
        assert matches_denylist(command), command
    allowed = (
        "git status", "git commit -m x", "git push",
        "git push origin main && tar -f b.tar data/",
        'git commit -m "drop table x via psql"',
        "vim mkfs.sh",
    )
    for command in allowed:
        assert not matches_denylist(command), command
    print("selftest passed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
