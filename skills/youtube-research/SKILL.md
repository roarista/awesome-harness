---
name: youtube-research
description: Research credible creators and mine their content on YouTube + Instagram/Reels for any niche. Use when the user says "run the youtube research skill", "do youtube research", "research <topic> on youtube", wants to find high-credibility creators/channels on a topic, pull a video's transcript, or scrape Instagram reels/comments (with likes) for niche/competitor research.
allowed-tools: Bash
---

# YouTube + Social Research

Two layers:

1. **Keyless discovery + transcripts** — works out of the box, only needs `yt-dlp`. This is the front door.
2. **`ytintel` CLI** *(optional external dep)* — adds Data-API credibility scoring, comments, and Instagram/Reels/TikTok via [ScrapeCreators](https://scrapecreators.com). Install separately and set its keys; the skill degrades gracefully without it.

YouTube discovery/transcripts are free/unlimited; Instagram uses paid ScrapeCreators credits — be economical on IG, generous on YouTube.

## When the user asks to research a topic/niche

1. **Find videos — DEFAULT to keyless discovery (no API key, no quota):**
   ```
   python3 skills/youtube-research/discover_keyless.py "query one" "query two" ... [--per 10] [--top 15]
   ```
   Uses `yt-dlp ytsearch` under the hood — zero quota, never 429s, and in practice returns MORE on-target
   results than the Data API. Prints `id | views | dur | channel | title` sorted by views, plus an `IDS:` line.
   Pass several query phrasings to widen the pool; it dedups + ranks by view_count. Tradeoff vs the API:
   no credibility/engagement score — rank by views + manual relevance. **Prefer this for almost everything.**

   **Fallback — Data API `discover` (only if you have `ytintel` and need engagement/credibility scoring):**
   ```
   ytintel discover --topic "<the niche/topic>" --min-subs 20000 --min-er 0.02 --top 15
   ```
   Ranked by channel then video credibility. Costs ~100 quota units/call (single `YOUTUBE_API_KEY`, 10k/day).
   If it returns **429**, the key is quota/rate-blocked → switch to keyless above (don't burn time on backoff).

2. **Pull transcripts of the top videos (free):**
   ```
   ytintel transcript "<video url or id>"
   ```
   Do this for the top N from step 1 to mine their actual method/claims. The Data API does NOT give
   transcripts — this is the piece that makes the research real.

3. **Mine comments for voice-of-customer (free):**
   ```
   ytintel comments <video_id> --max 100
   ```
   Top comments = audience questions, objections, "where do I get this" buy-signals, content gaps.

## When the user wants Instagram / Reels (uses credits — confirm topic first)

```
ytintel ig-reels <handle> --amount 12        # creator's reels, sorted by plays (most viral first)
ytintel ig-comments "<reel_url>"             # comments sorted by comment-likes (which objections resonate)
ytintel ig-post "<url>"                       # one post/reel full metrics
```
TikTok runs on the same ScrapeCreators API.

## How to report back
- Lead with the ranked credible creators (channel + subs + the standout video URL).
- For deep asks, transcribe the top 2–3 and synthesize their **method** (how they research/structure content),
  citing verbatim lines — not a paraphrase.
- Note credits remaining when IG was used.
- If a niche is too narrow and `discover` returns few rows, say so and loosen the gates rather than inventing.

## Notes
- This skill ONLY collects + summarizes; it does not persist results anywhere unless you wire that in yourself.
- **Keyless-first policy:** default to `discover_keyless.py` for discovery; the Data API is the fallback, not the front door.
- **Key list / rotation (for heavy Data API use):** put one key per line in `~/.config/ytintel/keys.txt`, then before
  an API call pick an unused one: `export YOUTUBE_API_KEY=$(grep -m1 . ~/.config/ytintel/keys.txt)` — on 429, move that
  line to the bottom and retry with the next. Get a fresh free key: Google Cloud Console → enable "YouTube Data API v3"
  → Credentials → Create credentials → API key. (Keyless discovery avoids needing a key at all.)
