#!/usr/bin/env python3
"""PreToolUse:Bash — hard STOP on IRREVERSIBLE ops (bypassPermissions guard).

Denylist only, tuned against cry-wolf: recursive force-delete of a target that is
NOT provably disposable (tmp, $CLAUDE_JOB_DIR, build output — see SAFE_*), force
push, reset --hard, clean -fd/-fx, stash, checkout ./--, find -delete, dd/mkfs,
cloud deletes, destructive SQL via a DB client, graded-coursework submission.
Heredoc bodies, comments and quoted arguments are never scanned as commands.
Narrowed 2026-10-03 (docs/audits/2026-10-03/hook-circumvention.md: 78% false).
Override after Ro approves: prefix the command with CLAUDE_ALLOW_IRREVERSIBLE=1.
Exit 2 + stderr reason = deny; any internal error fails open (exit 0).
Tests: tests/test_irreversible_pause.py
"""
import _hookout; _hookout.exit_if_product(); import json
import re
import sys

from _rmscan import rm_is_recursive_force as _rm_is_recursive_force

OVERRIDE = "CLAUDE_ALLOW_IRREVERSIBLE=1"

# 2. git push carrying a force flag.
GIT_FORCE_PUSH = re.compile(
    r"\bgit\b[^\n;|&]*\bpush\b[^\n;|&]*(?:--force-with-lease|--force|(?<![\w-])-f\b)",
)

# 3. Destructive SQL — only with a real DB client invoked outside quotes.
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
# stash mutates uncommitted work (list/show pass); checkout ./-- discards it.
GIT_STASH = re.compile(r"\bgit\b[^\n;|&]*\bstash\b(?!\s+(?:list|show)\b)")
GIT_CHECKOUT = re.compile(r"\bgit\b[^\n;|&]*\bcheckout\b([^\n;|&]*)")
FIND_DELETE = re.compile(r"\bfind\b[^\n;|&]*\s-delete\b|\bfind\b[^\n;|&]*\s-exec\s+rm\b")
TRUNCATE_ZERO = re.compile(r"\btruncate\s+-s\s+0\b")
DD_OF = re.compile(r"\bdd\b[^\n;|&]*\bof=")
MKFS = re.compile(r"(?:^|[\s;|&])mkfs(?:\.[\w-]+)?\s")
AWS_S3_RM_RECURSIVE = re.compile(r"\baws\s+s3\s+rm\b[^\n;|&]*--recursive\b")
GCLOUD_DELETE = re.compile(r"\bgcloud\b[^\n;|&]*\bdelete\b")
RCLONE_DELETE = re.compile(r"\brclone\s+(?:delete|purge)\b")


# 5. Graded-coursework submission (Ro submits himself; agent submitted 07-17).
#    Action shape only: LMS URL + HTTP client + submit verb/endpoint.
LMS_URL = re.compile(
    r"""(?:https?://|\bwww\.|//)[^\s'"<>]*"""
    r"(?:instructure\.com|blackboard|gradescope|turnitin|moodle|canvas)",
    re.IGNORECASE,
)
SUBMIT_VERB = re.compile(
    r"(?:\bsubmit\b|\bsubmissions?\b|\bturn[-_ ]?in\b|\bupload\b|"
    r"-X\s*POST|--request\s+POST|--data\b|--form\b|(?<![\w-])-[dF]\b|"
    r"--upload-file\b|--post-file\b|--post-data\b)",
    re.IGNORECASE,
)
SUBMIT_ENDPOINT = re.compile(r"/(?:submissions?|submit)(?:[/?#]|\b)", re.IGNORECASE)
HTTP_CLIENT = re.compile(r"(?:^|[\s;|&(])(?:curl|wget|http|httpie|xh)\b")


def _is_graded_submission(cmd: str) -> bool:
    """True iff the command LOOKS LIKE submitting coursework to an LMS: an LMS
    URL, an HTTP client actually invoked, and a submit-shaped endpoint or verb.
    Mere mention of Canvas/Gradescope never qualifies."""
    m = LMS_URL.search(cmd)
    if not m or not HTTP_CLIENT.search(cmd):
        return False
    url = cmd[m.start():].split()[0]
    return bool(SUBMIT_ENDPOINT.search(url) or SUBMIT_VERB.search(cmd))


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
COMMENT = re.compile(r"(?:^|\s)#.*$", re.MULTILINE)


def _split_heredocs(cmd: str) -> str:
    """`cmd` with heredoc BODIES removed (opener lines kept)."""
    lines = cmd.split("\n")
    code, i = [], 0
    while i < len(lines):
        line = lines[i]
        code.append(line)
        delims = [m.group(2) for m in HEREDOC.finditer(line)]
        i += 1
        for delim in delims:
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            if i < len(lines):
                i += 1  # skip the closing delimiter line itself
    return "\n".join(code)


def _strip_comments(cmd: str) -> str:
    """Blank unquoted `#` comments (start-of-line or after whitespace)."""
    return COMMENT.sub("", cmd)


def _dequote(cmd: str) -> str:
    """Blank quoted spans so triggers inside quoted args never match."""
    return re.sub(r'"[^"]*"|\'[^\']*\'', " ", cmd)


def _git_checkout_is_destructive(cmd: str) -> bool:
    """True iff one `git checkout` invocation discards working-tree changes:
    bare `.` as the (first) arg, or a `-- <path>` pathspec-restore form. A
    branch switch (`checkout main`, `checkout -b foo`) is NOT destructive."""
    for m in GIT_CHECKOUT.finditer(cmd):
        tokens = m.group(1).split()
        if not tokens:
            continue
        if tokens[0] == "." or tokens[0] == "--":
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
    # heredoc bodies first (delimiter may be quoted), then dequote, then comments
    cmd = _split_heredocs(cmd)
    bare = _strip_comments(_dequote(cmd))
    if _rm_is_recursive_force(cmd):
        return True
    if GIT_FORCE_PUSH.search(bare):
        return True
    if _git_clean_is_destructive(bare):
        return True
    if GIT_STASH.search(bare):
        return True
    if _git_checkout_is_destructive(bare):
        return True
    if any(pattern.search(bare) for pattern in (
        GIT_RESET_HARD, FIND_DELETE, TRUNCATE_ZERO,
        DD_OF, MKFS, AWS_S3_RM_RECURSIVE, GCLOUD_DELETE, RCLONE_DELETE,
    )):
        return True
    if DB_CLIENT.search(bare) and SQL_DESTRUCTIVE.search(_strip_comments(cmd)):
        return True
    if _is_graded_submission(_strip_comments(cmd)):
        return True
    return False


def deny() -> None:
    sys.stderr.write(
        "BLOCKED: this is an IRREVERSIBLE operation (recursive force-delete, "
        "force push, git stash/checkout that discards uncommitted work, "
        "destructive SQL/DB reset, or a GRADED-COURSEWORK SUBMISSION) "
        "and cannot be undone. NEVER submit Ro's coursework — he submits it himself. "
        "STOP and confirm with Ro before proceeding. After he approves, re-run "
        "the EXACT command prefixed with `" + OVERRIDE + " ` to re-arm and "
        "allow it through this guard."
    )
    sys.exit(2)


def main() -> None:
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if data.get("tool_name", "") != "Bash":
        return
    cmd = str((data.get("tool_input", {}) or {}).get("command", ""))
    if OVERRIDE in cmd:
        return  # override / re-arm — always allow
    if matches_denylist(cmd):
        deny()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call over this guard
