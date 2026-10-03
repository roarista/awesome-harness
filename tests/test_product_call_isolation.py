"""Product `claude -p` calls get ZERO harness; Ro's sessions get the harness unchanged.

Every hook registered in ~/.claude/settings.json is run twice from a scratch copy
of the hooks dir (HOOKS_DIR, default: this repo's hooks/):
  * product env (CLAUDE_CODE_ENTRYPOINT=sdk-cli, cwd/CLAUDE_PROJECT_DIR in a temp
    dir, no CLAUDE_JOB_DIR) -> stdout must be empty and exit 0;
  * normal env (entrypoint cli, cwd = this repo) -> stdout + exit code must equal
    the same hook with the guard stripped out (the pre-change behaviour).
A mutation check proves the product assertion has teeth: a guard-stripped hook
must FAIL it. Side effects land in a throwaway HOME.
Run: python3 tests/test_product_call_isolation.py   (HOOKS_DIR=~/.claude/hooks for live)
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))
PY_GUARD = "import _hookout; _hookout.exit_if_product(); "
SH_GUARD = re.compile(r'^python3 "\$\(dirname "\$0"\)/_hookout.py" && exit 0.*\n', re.M)
TOOL_INPUT = {
    "Bash": {"command": "rm -rf /tmp/zz-product-test"},
    "Write": {"file_path": "x.py", "content": "x = 1\n"},
    "Edit": {"file_path": "x.py", "old_string": "a", "new_string": "b"},
    "Read": {"file_path": "README.md"},
    "Grep": {"pattern": "is_product_call"},
    "Task": {"subagent_type": "claude", "description": "d", "prompt": "build x"},
    "Agent": {"subagent_type": "claude", "description": "d", "prompt": "build x"},
    "Skill": {"skill": "awesomeharness"},
}


def registered():
    """(event, matcher, script) for every hook command in the live settings."""
    s = json.loads(Path("~/.claude/settings.json").expanduser().read_text())
    out = []
    for ev, groups in s.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                m = re.search(r'hooks/([\w.-]+\.(?:py|sh))', h.get("command", ""))
                if m:
                    out.append((ev, g.get("matcher", ""), m.group(1)))
    return out


def payload(ev, matcher, cwd):
    p = {"session_id": "pc-test", "transcript_path": "/nonexistent.jsonl", "cwd": cwd,
         "hook_event_name": ev, "permission_mode": "default"}
    tool = (matcher.split("|")[0] or "Bash")
    if ev in ("PreToolUse", "PostToolUse"):
        p.update(tool_name=tool, tool_input=TOOL_INPUT.get(tool, {}))
        if ev == "PostToolUse":
            p["tool_response"] = {}
    elif ev == "UserPromptSubmit":
        p["prompt"] = "implement a new hook in hooks/foo.py"
    elif ev == "SessionStart":
        p["source"] = "startup"
    elif ev == "PreCompact":
        p["trigger"] = "manual"
    return json.dumps(p)


def env_for(product, cwd, home):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "HARNESS_HOOKS"))}
    e.update(HOME=home, CLAUDE_PROJECT_DIR=cwd, CLAUDE_CODE_ENTRYPOINT="sdk-cli" if product else "cli")
    return e


def run(hdir, script, ev, matcher, cwd, product):
    home = tempfile.mkdtemp(prefix="pc-home-")
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    cmd = ["sh" if script.endswith(".sh") else "python3", os.path.join(hdir, script)]
    try:
        r = subprocess.run(cmd, input=payload(ev, matcher, cwd), capture_output=True, text=True,
                           cwd=cwd, env=env_for(product, cwd, home), timeout=60)
        return r.returncode, r.stdout
    finally:
        shutil.rmtree(home, ignore_errors=True)


def copy_hooks(strip):
    d = tempfile.mkdtemp(prefix="pc-hooks-")
    for n in os.listdir(HOOKS):
        src = os.path.join(HOOKS, n)
        if not os.path.isfile(src):
            continue
        text = Path(src).read_text(encoding="utf-8", errors="surrogateescape")
        if strip:
            text = SH_GUARD.sub("", text.replace(PY_GUARD, ""))
        with open(os.path.join(d, n), "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(text)
    return d


class ProductCallIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hooks = registered()
        cls.guarded, cls.stripped = copy_hooks(False), copy_hooks(True)
        cls.tmp_cwd = tempfile.mkdtemp(prefix="pc-cwd-")  # /var/folders/... like virality

    @classmethod
    def tearDownClass(cls):
        for d in (cls.guarded, cls.stripped, cls.tmp_cwd):
            shutil.rmtree(d, ignore_errors=True)

    def test_every_registered_hook_is_guarded(self):
        self.assertGreater(len(self.hooks), 20)
        for _, _, s in self.hooks:
            text = Path(HOOKS, s).read_text()
            self.assertTrue(PY_GUARD in text or SH_GUARD.search(text), f"{s} has no product guard")

    def test_product_call_is_silent(self):
        for ev, m, s in self.hooks:
            with self.subTest(hook=s, event=ev, matcher=m):
                self.assertEqual(run(self.guarded, s, ev, m, self.tmp_cwd, True), (0, ""))

    def test_normal_session_unchanged(self):
        loud = 0
        for ev, m, s in self.hooks:
            if ev == "PreCompact":  # pre_compact_global.sh commits in cwd; never run it for real
                continue
            with self.subTest(hook=s, event=ev, matcher=m):
                got = run(self.guarded, s, ev, m, REPO, False)
                self.assertEqual(got, run(self.stripped, s, ev, m, REPO, False))
                loud += bool(got[1].strip())
        self.assertGreaterEqual(loud, 2, "normal run produced no output anywhere: test is vacuous")

    def test_mutation_unguarded_hook_leaks(self):
        """Teeth: the same product env against a guard-stripped hook MUST produce output."""
        rc, out = run(self.stripped, "caveman-discipline.sh", "SessionStart", "", self.tmp_cwd, True)
        self.assertNotEqual(out, "", "stripped hook was silent: the product assertion proves nothing")

    def test_rule(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("_hookout", os.path.join(HOOKS, "_hookout.py"))
        h = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(h)
        tmp = "/private/var/folders/x/T/tmpabc"
        p = {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli", "CLAUDE_PROJECT_DIR": tmp}
        self.assertTrue(h.is_product_call(p))
        self.assertFalse(h.is_product_call({**p, "CLAUDE_CODE_ENTRYPOINT": "cli"}))  # Ro, interactive
        self.assertFalse(h.is_product_call({**p, "CLAUDE_JOB_DIR": "/j"}))  # background job
        self.assertFalse(h.is_product_call({**p, "CLAUDE_PROJECT_DIR": REPO}))  # harness `claude -p` auditor
        self.assertFalse(h.is_product_call({**p, "HARNESS_HOOKS": "on"}))
        self.assertTrue(h.is_product_call({"CLAUDE_CODE_ENTRYPOINT": "cli", "HARNESS_HOOKS": "off"}))


if __name__ == "__main__":
    unittest.main(verbosity=1)
