# opus48-audit blind cross-audit — 2026-10-01

**Question:** opus48-audit passed 112 of 112 units in 30 days. Is that rubber-stamping?

**Method:** 10 opus48 PASS units from virality-pipeline (09-22 to 10-01), stratified toward risky code (money, secrets, persistence, retries). Packs are in `.artifacts/cross-audit/` and opus48's answers are in `KEY.md`. Two blind `opus` auditors re-judged them under the new **shared verdict rubric**, now in all three auditor agent definitions. They ran offline in /tmp worktrees with no commit messages and no prior reports.

| unit | area | opus48 | opus (shared rubric) | top finding |
|---|---|---|---|---|
| 01 | paid embed client | PASS (3 LOW) | **REJECT** (5 M) | tests write fake spend rows into the real `state/costs.jsonl` (7 rows per run) |
| 02 | treg 403 header fix | PASS | PASS | |
| 03 | Seedance roles + voice | PASS | PASS | |
| 04 | runner refs / ElevenLabs | PASS | PASS | |
| 05 | live re-embed | PASS | **REJECT** (2 H, 3 M) | `--db` copy rewrites the LIVE-path DB without `CREATIVE_RAG_ALLOW_LIVE`; backup taken of the wrong file; spend cap never checked against real spend |
| 06 | handoff hang | PASS | PASS | |
| 07 | R1 AI Mode stage | PASS | **REJECT** (3 M on the money path) | paid fetch path untested; spec asked for Chrome questions verbatim, two were rewritten |
| 08 | treg 503 retryable | PASS | PASS | |
| 09 | local voice provider | PASS | PASS WITH FIXES | Kokoro failure reported as "dry-run, no audio" |
| 10 | YouTube transcript cache | PASS | PASS WITH FIXES | good yt-dlp fallback transcript discarded on IpBlocked |

**Result:** 5 of 10 agree. **3 REJECT and 2 PASS WITH FIXES that opus48 passed.** Unit 05's two HIGH findings were reproduced offline. As of 2026-10-01 both 01 and 05 are **still in virality-pipeline HEAD** (no later commits to those files).

**Verdict:** the earlier conclusion that 0% REJECT was a "diet effect" was too generous. opus48 can detect defects: it scored 6/6 on the planted fixture, and here it listed LOW findings. But under its old "PASS = no HIGH" bar it let real money and data-loss defects through. The shared rubric's rule ("any MEDIUM touching money/secrets/data-loss → REJECT") is what separates the two verdicts.

**Limits:** n = 10, all from one repo, one opus run each. The two auditors used different rubrics: opus48 had its old bar, opus had the new one. This test measures how strict the bar is as well as how sharp each auditor is. Next step: re-run opus48 itself on these 10 units under the shared rubric.
