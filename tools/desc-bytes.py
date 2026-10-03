#!/usr/bin/env python3
"""desc-bytes.py — byte-count frontmatter `description:` of skills (cap 160) and agents (cap 300).
Usage: tools/desc-bytes.py [--all]   exit 1 if any file is over its cap. --all lists every file."""
import glob, os, re, sys
H, R = os.path.expanduser("~"), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = [(160, [f"{H}/.claude/skills/*/SKILL.md", f"{R}/skills/*/SKILL.md", f"{R}/codex/skills/*/SKILL.md", f"{H}/.codex/skills/*/SKILL.md"]),
        (300, [f"{H}/.claude/agents/*.md", f"{R}/agents/*.md"])]

def desc(path):
    m = re.match(r"---\n(.*?)\n---", open(path, encoding="utf-8").read(), re.S)
    if not m: return None
    out, grab = [], False
    for line in m.group(1).split("\n"):
        if re.match(r"description:", line): grab = True; out.append(line[12:].strip()); continue
        if grab and (line.startswith((" ", "\t")) or not line.strip()): out.append(line.strip()); continue
        grab = False
    v = " ".join(x for x in out if x not in ("|", ">", "|-", ">-")).strip()
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1].replace('\\"', '"')
    return v if out else None

bad = 0
for cap, pats in SETS:
    for f in sorted({os.path.realpath(p) for pat in pats for p in glob.glob(pat)}):
        d = desc(f)
        n = len(d.encode()) if d is not None else -1
        over = n > cap or n < 0
        bad += over
        if over or "--all" in sys.argv: print(f"{'OVER' if over else 'ok  '} {n:5d}/{cap} {f.replace(H, '~')}")
print(f"desc-bytes: {bad} over cap")
sys.exit(1 if bad else 0)
