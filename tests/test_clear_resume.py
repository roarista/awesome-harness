"""clear-resume: SessionStart(clear) injects .planning/CONTINUE.md (<48 h, <=1.5 KB) or .now.md.

Run: python3 tests/test_clear_resume.py   (HOOKS_DIR=<dir> to test another copy)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))


def run(source, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update(CLAUDE_CODE_ENTRYPOINT="cli")
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "clear-resume.py")],
                       input=json.dumps({"hook_event_name": "SessionStart", "source": source,
                                         "session_id": "t", "cwd": cwd}),
                       capture_output=True, text=True, cwd=cwd, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout else ""


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="cr-")
        os.makedirs(os.path.join(self.d, ".git"))
        os.makedirs(os.path.join(self.d, ".planning"))
        self.cont = os.path.join(self.d, ".planning", "CONTINUE.md")
        with open(self.cont, "w") as f:
            f.write("=== CONTINUE ===\nNEXT: run U6\n" + "z" * 3000)
        with open(os.path.join(self.d, ".now.md"), "w") as f:
            f.write("NOW: a\nLAST_VERIFIED: b\nNEXT: c\nl4\nl5\nl6-hidden\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_clear_with_fresh_continue(self):
        out = run("clear", os.path.join(self.d, ".planning"))  # walks up to the root
        self.assertIn("NEXT: run U6", out)
        self.assertNotIn("LAST_VERIFIED", out)
        self.assertLessEqual(len(out), 1500 + 80)

    def test_stale_continue_falls_back_to_now(self):
        old = time.time() - 49 * 3600
        os.utime(self.cont, (old, old))
        out = run("clear", self.d)
        self.assertNotIn("run U6", out)
        self.assertIn("LAST_VERIFIED: b", out)

    def test_now_fallback_when_no_continue(self):
        os.remove(self.cont)
        out = run("clear", self.d)
        self.assertIn("NEXT: c", out)
        self.assertIn("l5", out)
        self.assertNotIn("l6-hidden", out)

    def test_non_clear_source_is_silent(self):
        for src in ("startup", "resume", "compact"):
            self.assertEqual(run(src, self.d), "")

    def test_nothing_to_inject_is_silent(self):
        os.remove(self.cont)
        os.remove(os.path.join(self.d, ".now.md"))
        self.assertEqual(run("clear", self.d), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
