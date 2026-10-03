#!/usr/bin/env python3
"""Heredoc splitter with exact shell termination semantics, for irreversible-pause.

An opener is an UNQUOTED `<<` / `<<-` (never `<<<`, never inside quotes or a
comment; quote state carries across lines). Its body ends at the FIRST line
exactly equal to the delimiter (`<<-`: after stripping leading TABS only); an
unterminated body runs to the end. Everything else is returned as code, so a
bare `EOF` inside data ends the heredoc and the lines after it ARE scanned.
Audit: docs/audits/2026-10-03/hook-circumvention.md (re-audit of ec11506)."""


def _delim(line: str, j: int):
    """Parse the delimiter word at line[j:]. Returns (word, quoted, next_index)."""
    n, d, quoted = len(line), "", False
    while j < n and line[j] not in " \t;&|<>()":
        ch = line[j]
        if ch in "'\"":
            k = line.find(ch, j + 1)
            k = n if k < 0 else k
            d, quoted, j = d + line[j + 1:k], True, k + 1
        elif ch == "\\":
            d, quoted, j = d + line[j + 1:j + 2], True, j + 2
        else:
            d, j = d + ch, j + 1
    return d, quoted, j


def openers(line: str, q=None):
    """([(delim, strip_tabs, quoted)], quote_state_at_end_of_line)."""
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if q:
            if c == "\\" and q == '"':
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in "'\"":
            q, i = c, i + 1
        elif c == "\\":
            i += 2
        elif c == "#" and (i == 0 or line[i - 1] in " \t;&|("):
            break
        elif line.startswith("<<<", i):
            i += 3
        elif line.startswith("<<", i) and not line[max(0, i - 3):i].endswith("$(("):
            j, tabs = i + 2, False
            if j < n and line[j] == "-":
                j, tabs = j + 1, True
            while j < n and line[j] in " \t":
                j += 1
            d, quoted, j = _delim(line, j)
            if d:
                out.append((d, tabs, quoted))
            i = j
        else:
            i += 1
    return out, q


def split_heredocs(cmd: str):
    """(code_text, [(body, opener_line, quoted_delim)])."""
    lines, code, bodies, i, q = cmd.split("\n"), [], [], 0, None
    while i < len(lines):
        line = lines[i]
        code.append(line)
        i += 1
        ops, q = openers(line, q)
        for d, tabs, quoted in ops:
            body = []
            while i < len(lines):
                cur = lines[i]
                i += 1
                if (cur.lstrip("\t") if tabs else cur) == d:
                    break
                body.append(cur)
            bodies.append(("\n".join(body), line, quoted))
    return "\n".join(code), bodies
