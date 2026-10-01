# Cross-audit U01: E5a paid embedding client

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show 1f9e9680de42:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `1f9e9680de426c31af8ff98ec2761356bffff60d` (parent `9e1436954f5d9e5070966a5b745062984a7734d1`)
- Builder report (claim): `.artifacts/agent-reports/e5a-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 9e1436954f5d 1f9e9680de42 -- config/s1_providers.yaml src/creative_rag/embed_client.py tests/creative_rag/test_embed_client.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= 1f9e9680de42 -- config/s1_providers.yaml src/creative_rag/embed_client.py tests/creative_rag/test_embed_client.py
```

Code stat (unit paths only):
```
config/s1_providers.yaml                |  31 ++++
 src/creative_rag/embed_client.py        | 248 ++++++++++++++++++++++++++++++++
 tests/creative_rag/test_embed_client.py | 167 +++++++++++++++++++++
 3 files changed, 446 insertions(+)
```

## Unit spec as given to the builder (verbatim, 2026-09-22T18:58:53.041Z)

````text
You are a BUILDER for one unit in /Users/rodrigoarista/Downloads/virality-pipeline (branch codex-procedure-parity). Keep reads scoped; be concise. Use `.venv/bin/python`. Never git add -A, never checkout/restore/stash/reset/clean, never edit .planning/STATE.md, .now.md, .northstar.md. Do NOT commit. Write ONLY with Edit/Write tools (a hook blocks writing .py/.json via Bash). ZERO paid calls in this unit: tests use a fake transport; you may make at most ONE real call per provider that has a key, of ≤3 short strings, to prove the adapter parses the real response (say exactly how many calls you made). NEVER print, log or write any API key value. Never touch the live DB. New files ≤200 lines. Do not modify `src/spine/embeddings.py` (global MODEL_NAME also drives S1 clustering) nor `src/creative_rag/store.py`.

UNIT E5a — paid embedding client for the bake-off (per-use model, not global).
CONTEXT: The RAG embeds with local bge-large-en-v1.5 (1024d) via `src/spine/embeddings.py` (`embed(texts) -> np.ndarray`), and `store.upsert(items, embedder=...)`, `store.reembed_stale(embedder=...)`, `aspects.replace_aspect_vectors(conn, rows, embedder=..., vec=...)` accept any callable `embedder(list[str]) -> array (n,1024)`. The vec0 tables are FLOAT[1024], so every paid model must be requested at 1024 output dims (all candidates support it: Gemini `output_dimensionality`, OpenAI `dimensions`, Voyage `output_dimension`, Cohere `output_dimension`/embedding_types float). Keys available in `.env` (names only): `GEMINI_API_KEY`, `OPENAI_API_KEY`. Not present yet: `VOYAGE_API_KEY`, `COHERE_API_KEY` (build the adapters anyway; they raise a clear `MissingKey` error). Check how `.env` is loaded elsewhere (rg "dotenv|load_env" src) and reuse that.
CHANGE: new `src/creative_rag/embed_client.py` (≤180 lines): `class PaidEmbedder` with `__init__(self, model: str, *, input_type: str = "document", cache_dir: Path|None = None, transport=None, batch_size=64)`. Supported `model` ids and REST endpoints (plain `httpx`, already a dependency — verify with `rg httpx pyproject.toml`): `gemini-embedding-2` and `gemini-embedding-001` via `https://generativelanguage.googleapis.com/v1beta/models/<model>:batchEmbedContents` with `taskType` RETRIEVAL_QUERY / RETRIEVAL_DOCUMENT from input_type and `outputDimensionality` 1024, header `x-goog-api-key`; `text-embedding-3-large` via OpenAI `/v1/embeddings` with `dimensions: 1024`; `voyage-4-large`, `voyage-4` via `https://api.voyageai.com/v1/embeddings` with `input_type` query/document and `output_dimension` 1024; `embed-v4.0` (Cohere) via `https://api.cohere.com/v2/embed` with `input_type` search_query/search_document, `embedding_types ["float"]`, `output_dimension` 1024. Behaviour: (1) `__call__(texts) -> np.ndarray float32 (n,1024)`, L2-normalized (check whether the local embedder normalizes — mirror it so cosine distance in vec0 behaves the same); (2) disk cache: sqlite file `<cache_dir or state/creative_rag/embed_cache>/<model>.<input_type>.sqlite` keyed by sha256(text) → blob, hit before any network call, so re-runs cost 0; (3) retry with exponential backoff on 429/5xx/timeouts (max 5 tries, honour Retry-After), raise `EmbedError` with status and a truncated body (no key echo) otherwise; (4) cost ledger: after each real batch call `src.spine.costs.record(provider, call, units=<chars or tokens>, explicit_usd=<price>)` — read `costs.record` and the `_prices()` table, add the missing providers' pricing there ONLY if that file has a config table for it (read it first; if pricing lives in a data file, add rows there; USD per 1M tokens: gemini-embedding-2 0.20, gemini-embedding-001 0.15, text-embedding-3-large 0.13, voyage-4-large 0.12, voyage-4 0.06, embed-v4.0 0.12; estimate tokens as chars/4 when the response has no usage field); (5) a `FakeTransport` in `tests/creative_rag/test_embed_client.py` (≤150 lines) returning deterministic vectors, tests: cache hit avoids transport, retry on 429 then success, MissingKey without env var, request payload per provider (taskType/input_type/dimensions correct), output shape/dtype/normalization, query vs document input_type produce different cache files. Mutation-proof one test (e.g. break the normalization, see it fail by name, restore).
GOAL: `PaidEmbedder("gemini-embedding-2", input_type="document")` can replace `embed` in `store.upsert`/`reembed_stale` for the bake-off, with cache, retry and cost recording.
VERIFY: `.venv/bin/python -m pytest tests/creative_rag/test_embed_client.py -q` + `tests/creative_rag -q -x`; ruff on touched files; then the single live smoke per available key (gemini-embedding-2 and text-embedding-3-large, 2 strings each, print shape + norm + the usd recorded, never the key); if a provider rejects the model id, try `gemini-embedding-001` and report exactly what the API said (status + message).
REPORT: full report to `.artifacts/agent-reports/e5a-builder.md`; return ≤8 lines: verdict, files, tests, live smoke results per provider with USD, risks, report path.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/creative_rag/test_embed_client.py -q
.venv/bin/python -m pytest tests/creative_rag -q -x
.venv/bin/ruff check src/creative_rag/embed_client.py tests/creative_rag/test_embed_client.py
# The builder spec also asked for a LIVE paid smoke. Cross-auditors must NOT run it.
```

## Risk area to weigh
secrets (API keys) + money (cost ledger) + retries/backoff + sqlite cache persistence
