"""clear-resume: SessionStart(clear) injects .planning/CONTINUE.md (<48 h, <=1,500 B) or nothing.

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


def raw(stdin, cwd, entry="cli"):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE") and k != "HARNESS_HOOKS"}
    env.update(CLAUDE_CODE_ENTRYPOINT=entry)
    return subprocess.run([sys.executable, os.path.join(HOOKS, "clear-resume.py")], input=stdin,
                          capture_output=True, text=True, cwd=cwd, env=env, timeout=30)


def run(source, cwd, entry="cli"):
    r = raw(json.dumps({"hook_event_name": "SessionStart", "source": source,
                        "session_id": "t", "cwd": cwd}), cwd, entry)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout else ""


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="cr-")
        git("init", "-q", cwd=self.d)
        self.cont = os.path.join(self.d, ".planning", "CONTINUE.md")
        write(self.cont, "=== CONTINUE ===\nNEXT: run U6\n" + "z" * 3000)
        write(os.path.join(self.d, ".now.md"), "NOW: a\nLAST_VERIFIED: b\nNEXT: c\n")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_clear_with_fresh_continue(self):
        sub = os.path.join(self.d, "src", "deep")
        os.makedirs(sub)
        out = run("clear", sub)  # git finds the root from a subdir
        self.assertIn("NEXT: run U6", out)
        self.assertNotIn("LAST_VERIFIED", out)

    def test_byte_cap_multibyte(self):
        write(self.cont, "NEXT: é\n" + "é中" * 2000)
        out = run("clear", self.d)
        self.assertIn("NEXT: é", out)
        self.assertLessEqual(len(out.encode("utf-8")), 1500)
        self.assertNotIn("�", out)

    def test_stale_continue_is_silent(self):
        old = time.time() - 49 * 3600
        os.utime(self.cont, (old, old))
        self.assertEqual(run("clear", self.d), "")

    def test_no_continue_is_silent(self):  # .now.md is northstar-inject's job
        os.remove(self.cont)
        self.assertEqual(run("clear", self.d), "")

    def test_non_clear_source_is_silent(self):
        for src in ("startup", "resume", "compact"):
            self.assertEqual(run(src, self.d), "")

    def test_product_call_is_silent(self):
        self.assertTrue(os.path.realpath(self.d).startswith(("/private/var/", "/var/", "/private/tmp/", "/tmp/")))
        self.assertEqual(run("clear", self.d, entry="sdk-cli"), "")

    def test_bad_stdin_is_silent(self):
        for stdin in ("[]", "null", "7", "not json", ""):
            r = raw(stdin, self.d)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), stdin)

    def test_linked_worktree_root(self):
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "i", cwd=self.d)
        wt = os.path.join(self.d + "-wt")
        git("worktree", "add", "-q", wt, cwd=self.d)
        try:
            write(os.path.join(wt, ".planning", "CONTINUE.md"), "NEXT: worktree step\n")
            write(os.path.join(wt, "pkg", ".planning", "CONTINUE.md"), "NEXT: decoy\n")  # old walk stopped here
            out = run("clear", os.path.join(wt, "pkg"))
            self.assertIn("NEXT: worktree step", out)
            self.assertNotIn("run U6", out)
            self.assertNotIn("decoy", out)
        finally:
            shutil.rmtree(wt, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
