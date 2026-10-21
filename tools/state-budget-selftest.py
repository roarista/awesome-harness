#!/usr/bin/env python3
"""Exercise public budget CLI boundaries, isolation and read-only behavior."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

TOOL = Path(__file__).with_name("state-distiller.py").resolve()


def run(root, home, *args):
    result = subprocess.run([sys.executable, str(TOOL), str(root), "--budget", *args],
                            env={**os.environ, "HOME": str(home)}, capture_output=True,
                            text=True, check=True)
    assert not result.stderr, result.stderr
    return result.stdout


with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp).resolve() / "home"
    home.mkdir()
    root = Path(tmp).resolve() / "repo with spaces"
    root.mkdir()
    samples = {"CLAUDE.md": b"x" * 2500, "AGENTS.md": b"x" * 2501,
               "a/SKILL.md": b"x" * 2501, ".claude/CLAUDE.md": b"x" * 2501,
               ".planning/STATE.md": b"line\n" * 150, ".now.md": b"line\n" * 5,
               "nested/STATE.md": b"line\n" * 151,
               "nested/.now.md": b"line\n" * 6,
               "node_modules/CLAUDE.md": b"x" * 2501,
               ".git/SKILL.md": b"x" * 2501}
    for name, data in samples.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    globals_ = [home / name for name in (".claude/CLAUDE.md", ".codex/AGENTS.md",
                                        ".claude/skills/awesomeharness/SKILL.md")]
    for global_file in globals_:
        global_file.parent.mkdir(parents=True, exist_ok=True)
        global_file.write_bytes(b"x" * 2501)
    outside = Path(tmp) / "outside"
    outside.mkdir()
    (outside / "CLAUDE.md").write_bytes(b"x" * 2501)
    (root / "linked-dir").symlink_to(outside, target_is_directory=True)
    for flag in ("--apply", "--selftest"):
        result = subprocess.run(
            [sys.executable, str(TOOL), str(root), "--budget", flag],
            env={**os.environ, "HOME": str(home)}, capture_output=True,
            text=True, check=False)
        assert result.returncode == 2, result
        assert "usage:" in result.stderr.lower(), result.stderr
        assert not (root / ".planning/STATE-ARCHIVE.md").exists()
        for name, data in samples.items():
            assert (root / name).read_bytes() == data, name
    out = run(root, home)
    assert len(out.splitlines()) == 8, out
    home_out = run(home, home)
    for global_file in globals_:
        assert home_out.count(f"PRUNE: {global_file} ") == 1, home_out
    for name in ("AGENTS.md", "a/SKILL.md", ".claude/CLAUDE.md",
                 "nested/STATE.md", "nested/.now.md"):
        assert f"PRUNE: {root / name} " in out, out
    for global_file in globals_:
        assert f"PRUNE: {global_file} " in out, out
    assert "node_modules" not in out and ".git" not in out and "linked-dir" not in out
    assert "151 lines > 150" in out and "2501 bytes > 2500" in out
    for name, data in samples.items():
        assert (root / name).read_bytes() == data, name
    assert not (root / ".planning/STATE-ARCHIVE.md").exists()
    clean = Path(tmp).resolve() / "clean"
    clean.mkdir()
    for global_file in globals_:
        assert global_file.read_bytes() == b"x" * 2501
        global_file.write_bytes(b"")
    assert run(clean, home) == "PRUNE: none\n"
    (clean / "AGENTS.md").symlink_to(clean / "missing")
    out = run(clean, home)
    assert "BUDGET ERROR:" in out and "PRUNE: none" not in out, out
    assert "BUDGET ERROR:" in run(clean / "missing", home)
print("budget selftest passed: boundaries, recursion, globals, symlinks, errors, read-only")
