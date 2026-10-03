"""route-only-gate: main session blocked in an armed repo; sub-agents never blocked.

Audit docs/audits/2026-10-03/hook-circumvention.md: 13 of 14 blocks hit the very
builders the gate tells main to use. `agent_id` in hook stdin = sub-agent.
Run: python3 tests/test_route_only_gate.py   (HOOKS_DIR=<dir> to test another copy)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))
HOOK = os.path.join(HOOKS, "route-only-gate.py")


def run(payload, cwd):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_CODE_ENTRYPOINT", "ROUTING_GATE")}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, cwd=cwd)
    return p.returncode, p.stderr


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        open(os.path.join(self.d, ".route-only"), "w").close()
        self.src = os.path.join(self.d, "src", "app.py")

    def payload(self, **extra):
        return {"tool_name": "Edit", "cwd": self.d, "session_id": "s",
                "tool_input": {"file_path": self.src, "old_string": "a",
                               "new_string": "b"}, **extra}

    def test_main_blocked_in_armed_repo(self):
        code, err = run(self.payload(), self.d)
        self.assertEqual(code, 2)
        self.assertNotIn("glm", err.lower())
        self.assertIn("router", err)

    def test_subagent_never_blocked(self):
        code, _ = run(self.payload(agent_id="a123", agent_type="claude"), self.d)
        self.assertEqual(code, 0)

    def test_non_code_and_unarmed_pass(self):
        p = self.payload()
        p["tool_input"]["file_path"] = os.path.join(self.d, "notes.md")
        self.assertEqual(run(p, self.d)[0], 0)
        os.remove(os.path.join(self.d, ".route-only"))
        self.assertEqual(run(self.payload(), self.d)[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
