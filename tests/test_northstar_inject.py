"""northstar-inject: full north star on SessionStart only; per prompt the NOW line <= 300 B.

rule-value-audit 2026-10-02 row 10: the star repeated verbatim every prompt (1.4-2.4 KB).
Run: python3 tests/test_northstar_inject.py   (HOOKS_DIR=<dir> to test another copy)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))
STAR = "OBJECTIVE: ship the hook diet\nDONE_WHEN: tests green\nNOT_NOW: new hooks\n"


def ctx(event, cwd):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update(CLAUDE_PROJECT_DIR=cwd, CLAUDE_CODE_ENTRYPOINT="cli")
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "northstar-inject.py")],
                       input=json.dumps({"hook_event_name": event, "session_id": "t",
                                         "cwd": cwd, "prompt": "hi"}),
                       capture_output=True, text=True, cwd=cwd, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout else ""


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ns-")
        with open(os.path.join(self.d, ".northstar.md"), "w") as f:
            f.write(STAR)
        with open(os.path.join(self.d, ".now.md"), "w") as f:
            f.write("NOW: " + "x" * 900 + "\nNEXT: y\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_session_start_has_full_star(self):
        out = ctx("SessionStart", self.d)
        self.assertIn("NORTH STAR", out)
        self.assertIn("NOT_NOW: new hooks", out)

    def test_prompt_is_now_only_and_capped(self):
        out = ctx("UserPromptSubmit", self.d)
        self.assertTrue(out.startswith("NOW:"), out[:80])
        self.assertNotIn("OBJECTIVE", out)
        self.assertLessEqual(len(out.encode()), 300)


if __name__ == "__main__":
    unittest.main(verbosity=1)
