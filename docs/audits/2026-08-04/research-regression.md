# Research regression audit — youtube-research lag + research quality

Date: 2026-08-09 (~/.claude transcript data spans 2026-07-11 to 2026-08-10)

## 1. YOUTUBE LAG

`ytintel` is installed and on PATH (`/Users/rodrigoarista/.local/bin/ytintel`, uv-run script).
Timed each real entry point:

```
$ time python3 skills/youtube-research/discover_keyless.py "productivity tips" --per 5 --top 5
... real results ...
0.25s user 0.08s system 26% cpu 1.251 total
```
→ keyless discovery: **1.25s, fast, not the problem.**

```
$ time ytintel discover --topic "productivity" --min-subs 20000 --min-er 0.02 --top 3
... real results ...
0.08s user 0.05s system 8% cpu 1.563 total
```
→ Data API discover: **1.56s, fast, not the problem.**

```
$ time ytintel transcript "Hu4Yvq-g7_Y"
[youtube-transcript-api failed: AttributeError; trying yt-dlp]
RATE_LIMITED: YouTube returned HTTP 429 for this IP (captions endpoint throttled;
retry later or change IP) — ERROR: Unable to download video subtitles for 'en':
HTTP Error 429: Too Many Requests
1.14s user 0.20s system 32% cpu 4.166 total
```
→ **transcript is the broken/slow call.** 4.17s wall clock per attempt, and it never
succeeds: the primary library (`youtube-transcript-api`) throws `AttributeError` on
every call (API surface changed vs. the version pinned in the ytintel script header:
`youtube-transcript-api>=1.2`), so it falls through to the yt-dlp captions fallback,
which is IP-throttled and returns HTTP 429 every time. This is not a timeout or a
backoff retry loop inside ytintel itself — it's a single 4s round trip that ends in a
hard failure. The "laggy/unusable" feeling is this: every research session that pulls
transcripts (step 2 of the skill, described as "the piece that makes the research
real") burns ~4s per video and then produces **zero transcripts**, likely triggering
either a stall while Claude retries variants, or research proceeding without the
transcript data the skill depends on.

```
$ time ytintel comments Hu4Yvq-g7_Y --max 20
... real comments with likes/author ...
0.07s user 0.02s system 24% cpu 0.365 total
```
→ comments: **0.37s, fast, not the problem.**

**Diagnosis:** it's neither a timeout, a retry loop, nor a missing-API-key fallback,
nor a general rate limit on ytintel's own calls (discover/comments/keyless are all
sub-2s and unlimited). It is a broken primary path (`AttributeError` in
`youtube-transcript-api`) that always falls through to an already-throttled yt-dlp
captions endpoint (`429`) on the specific IP. Fix candidates: pin/upgrade
`youtube-transcript-api` to match its current API, or rotate/avoid the yt-dlp
captions fallback (e.g. cookies/proxy) since this IP is already blocked by YouTube for
that endpoint.

**Confound checked:** `ENABLE_TOOL_SEARCH: "true"` is set in `~/.claude/settings.json`,
and `claude mcp list` shows only 4 connected servers (Hugging Face, Supabase, Notion,
Vercel) — no research-specific MCP servers are configured or disconnected. WebSearch/
WebFetch are native tools, not MCP, so ToolSearch deferral does not explain the
youtube-research lag; it is fully explained by the transcript-call failure above.

## 2. RESEARCH QUALITY

Method: recursively globbed `~/.claude/projects/**/*.jsonl` (6,213 files as of this run;
a shallow non-recursive glob would have undercounted). Transcript timestamps span
2026-07-11T18:30Z to 2026-08-10T04:44Z — i.e. the entire retained transcript history is
~29 days, not the full 45-day window asked for (nothing older than 2026-07-11 exists on
disk to compare against).

A session was counted "research-shaped" if it contained ≥1 user message matching
research keywords (research/find creators/youtube/sources/look up/search for) AND at
least one `WebSearch` or `WebFetch` tool call. Split at the 22-day mark (2026-07-18) to
divide the available window into two ~equal halves.

```
total research-shaped sessions (29d retained window): 198
OLDER (2026-07-11 .. 2026-07-18): n=0
NEWER (2026-07-18 .. 2026-08-09): n=198, avg_websearch=7.05, avg_webfetch=7.47,
  avg_urls_in_user_msgs=13.53, total_correction_msgs=25, corr_per_session=0.13
```

**UNDERPOWERED** — the older arm has n=0 (transcript retention only goes back to
2026-07-11, giving ~7 days of history before the midpoint, and none of those early
sessions happened to match the research-shaped filter). There is no usable older arm to
compare against, so no before/after claim on research quality can be made from this
transcript store. The 198-session "newer" arm alone shows research sessions do
routinely fetch multiple real sources (avg ~7 WebSearch + ~7 WebFetch calls/session,
~13.5 URLs referenced) and correction-by-user is infrequent (25 correction-flagged
messages across 198 sessions, ~13%), but with no earlier baseline this cannot show
whether quality is better, worse, or unchanged vs. "recently."

**Bottom line:** Ro's (b) report (youtube-research is laggy/unusable) is measured and
confirmed — the transcript call is broken (AttributeError → 429) on every invocation.
Ro's (a) report (research quality regression) cannot be confirmed or denied from
`~/.claude/projects` transcripts — the retained window is too short (29 days, not 45)
and the older comparison arm is empty (n=0, UNDERPOWERED per the VERIFY threshold).
