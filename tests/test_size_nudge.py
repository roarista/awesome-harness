"""size-nudge: 201-line source fires, 200 silent, non-source silent, product call silent.

Run: python3 tests/test_size_nudge.py   (HOOKS_DIR=<dir> to test another copy)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))
HOOK = os.path.join(HOOKS, "size-nudge.py")


def _load(name, path):
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_hook(path, product=False, tool="Write"):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_CODE_ENTRYPOINT", "CLAUDE_JOB_DIR", "HARNESS_HOOKS",
                        "CLAUDE_PROJECT_DIR")}
    if product:  # the measured product shape: sdk-cli, temp cwd, no job dir
        env.update(CLAUDE_CODE_ENTRYPOINT="sdk-cli", CLAUDE_PROJECT_DIR="/tmp")
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(
        {"tool_name": tool, "tool_input": {"file_path": path}, "cwd": "/tmp"}),
        capture_output=True, text=True, env=env, cwd="/tmp")
    return p.returncode, p.stdout


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="sizenudge")

    def _file(self, name, n):
        p = os.path.join(self.d, name)
        with open(p, "w") as f:
            f.write("".join(f"x = {i}\n" for i in range(n)))
        return p

    def test_201_fires(self):
        p = self._file("big.py", 201)
        rc, out = run_hook(p)
        self.assertEqual(rc, 0)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(ctx, f"{p} is 201 lines (cap 200): split into a new module before continuing.")
        rc, out = run_hook(p, tool="Edit")
        self.assertIn("201 lines", out)

    def test_200_silent(self):
        self.assertEqual(run_hook(self._file("ok.ts", 200)), (0, ""))

    def test_non_source_silent(self):
        self.assertEqual(run_hook(self._file("notes.md", 500)), (0, ""))
        self.assertEqual(run_hook(self._file("data.json", 500)), (0, ""))

    def test_product_call_silent(self):
        self.assertEqual(run_hook(self._file("prod.py", 400), product=True), (0, ""))

    def test_other_tool_and_missing_silent(self):
        self.assertEqual(run_hook(self._file("r.py", 300), tool="Read"), (0, ""))
        self.assertEqual(run_hook(os.path.join(self.d, "nope.py")), (0, ""))

    def test_ext_list_mirrors_ratchet(self):
        nudge = _load("sizenudge", HOOK)
        ratchet = _load("ratchet", os.path.join(REPO, "tools", "git-hooks", "ratchet.py"))
        self.assertEqual(nudge.SRC_EXT, ratchet.SRC_EXT)
        self.assertEqual(nudge.SKIP_DIRS, ratchet.SKIP_DIRS)
        self.assertEqual(nudge.CAP, ratchet.CAP)


if __name__ == "__main__":
    unittest.main(verbosity=1)
