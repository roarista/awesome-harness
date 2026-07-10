#!/usr/bin/env python3
"""Render assets/benchmark.svg — the 'bare Claude Code vs awesome-harness'
before/after chart, from the measured V2 benchmark numbers. Deterministic,
exact (image models garble digits; this doesn't). Dark card so it reads on both
GitHub light and dark themes. Re-run to regenerate."""
from pathlib import Path

# (label, WITHOUT, WITH, unit, multiplier_text, tag)
ROWS = [
    ("Median context cost / session", 1_352_122, 64_372, "tok", "~21x lighter", "observational"),
    ("Redundant >8KB re-reads / session", 0.345, 0.015, "", "23x fewer", "measured"),
    ("Compactions / session", 1.31, 0.32, "", "4x fewer", "measured"),
]
W, PAD, ROW_H, BAR_MAX = 760, 28, 74, 300
TOP = 96
H = TOP + len(ROWS) * ROW_H + 64
BG, CARD = "#0d1117", "#161b22"
RED, GREEN, TXT, DIM = "#f0736a", "#3fb886", "#e6edf3", "#8b949e"


def fmt(v, unit):
    s = f"{v:,.0f}" if v >= 100 else (f"{v:g}")
    return f"{s} {unit}".strip()


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Roboto,sans-serif">',
    f'<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>',
    f'<text x="{PAD}" y="40" fill="{TXT}" font-size="22" font-weight="700">'
    f'Bare Claude Code vs awesome-harness</text>',
    f'<text x="{PAD}" y="64" fill="{DIM}" font-size="13">Full 94-session history '
    f'(2026-06-09 - 07-09), split at the first harness commit. Observational.</text>',
    # legend
    f'<rect x="{W-250}" y="26" width="12" height="12" rx="2" fill="{RED}"/>'
    f'<text x="{W-232}" y="36" fill="{DIM}" font-size="12">WITHOUT</text>'
    f'<rect x="{W-150}" y="26" width="12" height="12" rx="2" fill="{GREEN}"/>'
    f'<text x="{W-132}" y="36" fill="{DIM}" font-size="12">WITH everything</text>',
]

y = TOP
for label, wo, wi, unit, mult, tag in ROWS:
    ratio = (wi / wo) if wo else 0
    wi_w = max(3, round(BAR_MAX * ratio))
    parts += [
        f'<text x="{PAD}" y="{y-6}" fill="{TXT}" font-size="15" font-weight="600">{esc(label)}</text>',
        f'<text x="{W-PAD}" y="{y-6}" fill="{GREEN}" font-size="14" font-weight="700" '
        f'text-anchor="end">{esc(mult)}</text>',
        # WITHOUT bar (full)
        f'<rect x="{PAD}" y="{y+4}" width="{BAR_MAX}" height="16" rx="4" fill="{RED}"/>',
        f'<text x="{PAD+BAR_MAX+10}" y="{y+17}" fill="{DIM}" font-size="12">{esc(fmt(wo,unit))}</text>',
        # WITH bar (proportional)
        f'<rect x="{PAD}" y="{y+30}" width="{wi_w}" height="16" rx="4" fill="{GREEN}"/>',
        f'<text x="{PAD+max(wi_w,0)+10}" y="{y+43}" fill="{TXT}" font-size="12">{esc(fmt(wi,unit))}</text>',
        f'<text x="{W-PAD}" y="{y+43}" fill="{DIM}" font-size="10" text-anchor="end">[{tag}]</text>',
    ]
    y += ROW_H

parts.append(
    f'<text x="{PAD}" y="{H-30}" fill="{DIM}" font-size="12">Also: 167,919 tok '
    f'pulled out of the every-session read path (state-distiller) - one 4.13M-tok '
    f're-read loop eliminated - 0 to 21 structured handoffs.</text>')
parts.append(
    f'<text x="{PAD}" y="{H-14}" fill="{DIM}" font-size="11">Per-session rates '
    f'hold under every session-size filter. Full method: docs/BENCHMARK.md</text>')
parts.append("</svg>")

out = Path(__file__).resolve().parent.parent / "assets" / "benchmark.svg"
out.write_text("\n".join(parts))
print(f"wrote {out} ({out.stat().st_size} bytes)")
