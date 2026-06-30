#!/usr/bin/env python3
"""ctxproxy — a local, *safe* context-compression proxy for Claude Code.

Sits between Claude Code and api.anthropic.com. Point ANTHROPIC_BASE_URL at it.
Credentials pass straight through; nothing leaves your machine but the same
request that was already going to Anthropic (minus terminal color codes).

SAFETY MODEL (learned the hard way — see review notes):
  * We strip ONLY ANSI/OSC/DCS escape sequences (terminal color/cursor noise).
  * We strip them ONLY from tool_result blocks, and NEVER from Read/NotebookRead
    output — those are the only results a later Edit exact-matches against the
    on-disk file. Touching them silently breaks Edit. So we don't.
  * We do NOT strip trailing whitespace or \\r (that broke Edit / CRLF files).
  * If a request changes nothing, we forward the ORIGINAL bytes verbatim — so
    Anthropic's prompt cache prefix is never disturbed for untouched turns.
  * Anti-inflation: if the rewrite somehow grew, we forward the original.
  * Fail-open: any parse/transform error forwards the original request.
  * Responses are streamed straight through, never modified.

Usage:
    python3 ctxproxy.py serve            # 127.0.0.1:8788
    ANTHROPIC_BASE_URL=http://127.0.0.1:8788 claude
    python3 ctxproxy.py savings          # byte savings so far
    python3 ctxproxy.py demo             # self-check

ponytail: ANSI-only is the safe ceiling. Bigger savings = lossy + need
headroom's frozen-prefix/CCR machinery; out of scope for a single file.
"""
from __future__ import annotations

import http.client
import json
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8788
UPSTREAM = "api.anthropic.com"
LOG = Path.home() / ".ctxproxy.log.jsonl"

# Tools whose result content a later Edit matches against the real file — never touch.
PROTECTED_TOOLS = {"Read", "NotebookRead"}

# Recognized terminal escape sequences. Order matters: terminated forms (OSC/DCS)
# before the generic two-char ESC so we strip whole sequences, not just the intro.
_ANSI = re.compile(
    r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"      # OSC  ... BEL or ST
    r"|\x1b[P^_X][^\x1b]*\x1b\\"               # DCS/PM/APC/SOS ... ST
    r"|\x1b\[[0-9;?]*[ -/]*[@-~]"              # CSI  (colors, cursor)
    r"|\x1b[@-Z\\-_]"                          # other two-char ESC
)


def squeeze_text(s: str) -> str:
    """Strip terminal escape sequences only. Line count and every other byte
    are preserved, so this can never alter content an Edit might match."""
    return _ANSI.sub("", s)


def _squeeze_block_content(content):
    if isinstance(content, str):
        return squeeze_text(content)
    if isinstance(content, list):
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ):
                part["text"] = squeeze_text(part["text"])
    return content


def squeeze_body(raw: bytes) -> bytes:
    """Strip ANSI from non-protected tool_result blocks. Returns the ORIGINAL
    bytes unchanged when nothing was modified, on inflation, or on any error."""
    try:
        body = json.loads(raw)
        msgs = body.get("messages")
        if not isinstance(msgs, list):
            return raw

        # map tool_use_id -> tool name, so we can skip Read/NotebookRead results
        names: dict[str, str] = {}
        for m in msgs:
            content = m.get("content") if isinstance(m, dict) else None
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id"):
                        names[b["id"]] = b.get("name", "")

        changed = False
        for m in msgs:
            content = m.get("content") if isinstance(m, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                    continue
                if names.get(block.get("tool_use_id", ""), "") in PROTECTED_TOOLS:
                    continue
                before = json.dumps(block.get("content"), ensure_ascii=False)
                block["content"] = _squeeze_block_content(block.get("content"))
                if json.dumps(block.get("content"), ensure_ascii=False) != before:
                    changed = True

        if not changed:
            return raw  # forward verbatim — do not disturb the prompt cache
        out = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return out if len(out) < len(raw) else raw  # anti-inflation
    except Exception:
        return raw


def _log(in_n: int, out_n: int, path: str) -> None:
    try:
        with LOG.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "t": datetime.now(timezone.utc).isoformat(),
                        "path": path,
                        "in": in_n,
                        "out": out_n,
                        "saved": in_n - out_n,
                    }
                )
                + "\n"
            )
    except Exception:
        pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _proxy(self):
        sent = False
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""

        out = squeeze_body(raw) if raw else raw
        if raw:
            _log(len(raw), len(out), self.path)

        skip = {"host", "content-length", "connection", "transfer-encoding"}
        fwd = {k: v for k, v in self.headers.items() if k.lower() not in skip}
        fwd["Content-Length"] = str(len(out))

        conn = http.client.HTTPSConnection(UPSTREAM, timeout=600)
        try:
            conn.request(self.command, self.path, body=out, headers=fwd)
            resp = conn.getresponse()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() in {"transfer-encoding", "connection", "content-length"}:
                    continue
                self.send_header(k, v)
            self.send_header("Connection", "close")
            self.end_headers()
            sent = True  # headers committed — past this point we must not inject
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except Exception as e:
            if not sent:
                try:
                    self.send_response(502)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
                except Exception:
                    pass
            # if headers already sent, just drop the connection (truncated SSE
            # is a retryable error to the client; injecting bytes would corrupt it)
        finally:
            conn.close()

    do_POST = _proxy
    do_GET = _proxy


def serve():
    print(f"ctxproxy on http://127.0.0.1:{PORT} -> {UPSTREAM}  (log: {LOG})")
    print(f"  ANTHROPIC_BASE_URL=http://127.0.0.1:{PORT} claude")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


def savings():
    if not LOG.exists():
        print("no requests logged yet")
        return
    tin = tout = n = 0
    for line in LOG.read_text().splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        tin += d["in"]
        tout += d["out"]
        n += 1
    if not tin:
        print("no bytes logged")
        return
    pct = 100 * (tin - tout) / tin
    print(f"{n} requests | in {tin:,}B  out {tout:,}B  saved {tin-tout:,}B ({pct:.1f}%)")


def demo():
    # ANSI stripped, line count preserved
    assert squeeze_text("\x1b[31mhi\x1b[0m\nbye") == "hi\nbye"
    # OSC fully removed (regression: H1 body-bleed)
    assert squeeze_text("\x1b]0;title\x07X") == "X"
    # trailing whitespace PRESERVED (regression: C1 — must not break Edit)
    assert squeeze_text("def f():   \n    pass") == "def f():   \n    pass"
    # CRLF PRESERVED (regression: C2)
    assert squeeze_text("a\r\nb") == "a\r\nb"

    def mk(tool, content):
        return json.dumps({"messages": [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "u1", "name": tool, "input": {}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "u1", "content": content}]},
        ]}).encode()

    # Bash result: ANSI stripped
    bash = json.loads(squeeze_body(mk("Bash", "\x1b[32mok\x1b[0m")))
    assert bash["messages"][1]["content"][0]["content"] == "ok"
    # Read result: NEVER touched, even with ANSI present (file may legitimately hold ESC)
    read_raw = mk("Read", "\x1b[32mok\x1b[0m")
    assert squeeze_body(read_raw) == read_raw, "Read output must be byte-identical"
    # nothing to change -> original bytes returned verbatim (cache safe)
    clean = mk("Bash", "plain output")
    assert squeeze_body(clean) == clean
    # non-message body passes through
    assert squeeze_body(b'{"foo":1}') == b'{"foo":1}'
    print("demo OK")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    {"serve": serve, "savings": savings, "demo": demo}.get(cmd, serve)()
