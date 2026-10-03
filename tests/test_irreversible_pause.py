"""irreversible-pause: audit false blocks pass, real danger still blocks.

Cases come from docs/audits/2026-10-03/hook-circumvention.md (78% of 285 blocks
were FALSE: tmp/job/build rm -rf, heredoc bodies, `-Rodrigo` read as `-R`).
Run: python3 tests/test_irreversible_pause.py   (HOOKS_DIR=<dir> to test another copy)
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.expanduser(os.environ.get("HOOKS_DIR", os.path.join(REPO, "hooks")))
HOOK = os.path.join(HOOKS, "irreversible-pause.py")
sys.path.insert(0, HOOKS)
_spec = importlib.util.spec_from_file_location("irrpause", HOOK)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

FALSE_BLOCKS = (  # each was blocked by the old hook; none is dangerous
    'cp "$CLAUDE_JOB_DIR/tmp/v8-Cambria.pdf" Arista-Rodrigo-Resume-2026.pdf',
    "cat > .artifacts/agent-reports/r.md <<'EOF'\nrun rm -rf build then git push --force\nEOF",
    "rm -rf /tmp/x11m",
    'rm -rf "$CLAUDE_JOB_DIR/tmp/r3"',
    "rm -rf ${CLAUDE_JOB_DIR}/tmp/old && mkdir -p $CLAUDE_JOB_DIR/tmp/old",
    "rm -rf node_modules dist build __pycache__ .pytest_cache",
    "cd web && rm -rf ./dist/ out",
    "rm -rf /private/tmp/hc /var/folders/ab/T/x",
    "git worktree remove /tmp/wt-a1 --force; rm -rf /tmp/wt-a1",
    "rm -rf .claude/worktrees/agent-a1",
    'D=$(mktemp -d); cp x "$D"; rm -rf "$D"',
    "rm -f notes.txt",
    'echo "rm -rf / and git push --force"',
    "# rm -rf build\ngit status",
    "git stash list", "git checkout -b foo", "git push origin main",
    "curl -s https://canvas.instructure.com/api/v1/courses/1/assignments/2 -o rubric.json",
    'git commit -m "drop table x via psql"',
)
REAL_DANGER = (
    "rm -rf ~/.cache/huggingface/hub/models--google--gemma-4",
    "rm -rf src", "rm -rf /", "sudo rm -rf /usr/local/lib", 'rm -rf "$HOME/x"',
    "rm -rf $CLAUDE_JOB_DIR/../..", "rm -rf $CLAUDE_JOB_DIR", "rm -rf build ~/docs",
    "rm -rf build/../src", "rm -r -f --verbose data", "rm --recursive --force data",
    "bash -c 'rm -rf ~/x'", "ls | xargs rm -rf", "rm -rf *", "rm -rf /tmp",
    "git push --force", "git push origin --force-with-lease", "git reset --hard HEAD~1",
    "git clean -fd", "git clean -fx", "git stash", "git checkout -- foo.py",
    "find . -delete", "truncate -s 0 f", "dd if=x of=/dev/disk9", "mkfs.ext4 /dev/disk9",
    "aws s3 rm s3://b --recursive", "gcloud projects delete p", "rclone purge r:p",
    "psql -c 'drop table users'",
    # cf687c4 audit bypasses: keywords reset command position
    "if true; then rm -rf ~/x; fi", "for d in a b; do rm -rf ~/$d; done",
    'while read d; do rm -rf "$d"; done', "{ rm -rf ~/x; }", "! rm -rf ~/x",
    "if false; then :; else rm -rf ~/x; fi", "time rm -rf ~/x",
    # prefix commands with options / args / assignments
    "sudo -u ro rm -rf ~/x", "env -i rm -rf ~/x", "env FOO=1 rm -rf ~/x", "X=1 rm -rf ~/x",
    "timeout 5 rm -rf ~/x", "nohup rm -rf ~/x", "nice -n 5 rm -rf ~/x",
    "stdbuf -o0 rm -rf ~/x", "find . -print0 | xargs -0 rm -rf",
    # shell -c flag groups and eval
    'sh -lc "rm -rf ~/x"', "bash -ec 'rm -rf ~/x'", "zsh -c 'rm -rf ~/x'", "eval rm -rf ~/x",
    # force-push flag groups and +refspec
    "git push -fu origin main", "git push -uf origin main", "git push origin +main",
    "curl -X POST https://canvas.instructure.com/api/v1/courses/1/assignments/2/submissions -F f=@a.pdf",
)


def run_hook(cmd):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_ENTRYPOINT"}
    env["CLAUDE_JOB_DIR"] = env.get("CLAUDE_JOB_DIR", "/tmp/jobdir")
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": REPO}),
        capture_output=True, text=True, env=env, cwd=REPO)
    return p.returncode


class T(unittest.TestCase):
    def test_false_blocks_pass(self):
        bad = [c for c in FALSE_BLOCKS if mod.matches_denylist(c)]
        self.assertEqual(bad, [], "still blocked")

    def test_real_danger_blocks(self):
        missed = [c for c in REAL_DANGER if not mod.matches_denylist(c)]
        self.assertEqual(missed, [], "not blocked")

    def test_hook_exit_codes(self):
        self.assertEqual(run_hook("rm -rf /tmp/x11m"), 0)
        self.assertEqual(run_hook("rm -rf ~/x"), 2)
        self.assertEqual(run_hook("CLAUDE_ALLOW_IRREVERSIBLE=1 rm -rf ~/x"), 0)

    def test_tmp_symlink_to_home_is_not_safe(self):
        link = "/tmp/irp-test-link-%d" % os.getpid()
        try:
            os.symlink(os.path.expanduser("~"), link)
            self.assertTrue(mod.matches_denylist("rm -rf %s/" % link))
            self.assertTrue(mod.matches_denylist("rm -rf %s/Documents" % link))
        finally:
            if os.path.islink(link):
                os.unlink(link)

    def test_mutation_has_teeth(self):
        """Neuter the target check: the danger assertion must then FAIL."""
        rms = sys.modules.get("_rmscan")
        if rms is None:
            self.skipTest("old single-file hook has no _rmscan")
        orig = rms._safe_target
        rms._safe_target = lambda *a: True
        try:
            self.assertFalse(mod.matches_denylist("rm -rf ~/x"))
        finally:
            rms._safe_target = orig
        self.assertTrue(mod.matches_denylist("rm -rf ~/x"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
