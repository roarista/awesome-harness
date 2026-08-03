# codex-audit vs opus on a known-bad fixture — 2026-08-03

`codex-audit` has been the DEFAULT auditor since 2026-08-02 (Ro's call: Codex
credits are abundant, Opus is not) and had never been measured. `opus` has prior
measured evidence: 12% of the fleet, 39/55 rejects, 36 invented-API catches.

## Method

Fixture: `fixture-known-bad.py` — 78 lines, a plausible retry/backoff HTTP helper
plus a small on-disk cache, written by a codex builder to contain EXACTLY 6
planted defects spanning difficulty classes. No comments hint at them. Nothing
imports it. Answer key written at the same time: `fixture-known-bad.KEY.md`.

Both auditors got the SAME prompt, blind: no key, explicitly forbidden from
opening `*KEY.md`, told that a padded or wrong finding counts against them exactly
as much as a miss. Same return format. Neither saw the other's answer.

## Result

| # | planted defect | line | codex-audit | opus |
|---|---|---|---|---|
| 1 | inverted TTL condition | 30 | HIT | HIT |
| 2 | resource leak on error path | 45 | HIT | HIT |
| 3 | off-by-one: `range(retries + 1)` | 60 | **MISS** | HIT |
| 4 | invented API `response.ensure_success()` | 67 | HIT | HIT |
| 5 | bare `except: pass` swallowing the real failure | 69 | HIT | HIT |
| 6 | silent-empty: returns `{}` on exhaustion | 78 | HIT | HIT |
| | **planted defects caught** | | **5 / 6** | **6 / 6** |
| | **false positives** | | **0** | **0** |

**Opus also found a 7th defect that is not in the key and is real:** L43 calls
`os.replace(temporary, path)` while `handle` is still open and unflushed, so the
published cache file can be truncated or empty. The builder wrote that bug by
accident and did not know it was there. It is arguably more dangerous than the
leak it was trying to plant, because it corrupts data rather than leaking an fd.

Both auditors ranked the invented API first, which matches the prior finding that
it is the highest-yield class. Neither padded.

## Verdict

Opus wins this run 6/6 (+1 unplanted) to 5/6, with both clean on false positives.
The two it separated on are exactly the classes that need a careful reader: an
arithmetic boundary, and an ordering bug between a write and a rename.

**Honest limits:** n = 1 file, 6 planted defects, one run each, no repeats, and
the fixture was written by a Codex builder — which could cut either way. This is
suggestive, NOT decisive, and it does not overturn the credits argument that put
codex-audit in the default seat. codex-audit at 5/6 with zero noise is a
competent auditor, not a broken one.

**Recommendation:** keep codex-audit as the default (the cost argument stands and
its miss was the least dangerous of the six), and keep routing irreversible work
— money, auth, credentials, data-loss — to opus, which is already the documented
escalation rule. The measurement now supports that rule instead of assuming it.
Revert path if this ever flips: the commented-out row in `tools/route-model.sh`.
