# Cross-audit U05: E6b live re-embed script

## Rules for this audit
- Read-only. No network, no paid/provider calls, no live DB writes.
- Do NOT read commit messages (`git log`, plain `git show`). Use only the commands below.
- Do NOT open any `.artifacts/agent-reports/*audit*.md` / `*auditor*.md` file, `.artifacts/cross-audit/KEY.md`, or any agent transcript. The builder report (if present) is a CLAIM, not evidence.
- The repo has moved on since this commit. Read files at the commit with `git show e35e7ef06bd1:<path>`, not from the working tree.

## Repo and commit
- Repo: `/Users/rodrigoarista/Downloads/virality-pipeline`
- Commit: `e35e7ef06bd19f5a4ca97e00c5b94c8e71fec471` (parent `418fc1e95e4694fffd9d5a94fc164182d1ce97b3`)
- Builder report (claim): `.artifacts/agent-reports/e6b-builder.md`

```
git -C /Users/rodrigoarista/Downloads/virality-pipeline diff 418fc1e95e46 e35e7ef06bd1 -- scripts/creative_rag/reembed_live.py tests/creative_rag/test_reembed_live.py
git -C /Users/rodrigoarista/Downloads/virality-pipeline show --stat --format= e35e7ef06bd1 -- scripts/creative_rag/reembed_live.py tests/creative_rag/test_reembed_live.py
```

Code stat (unit paths only):
```
scripts/creative_rag/reembed_live.py    | 148 ++++++++++++++++++++++++++++++++
 tests/creative_rag/test_reembed_live.py |  95 ++++++++++++++++++++
 2 files changed, 243 insertions(+)
```

## Unit spec as given to the builder (verbatim, 2026-09-23T17:24:09.035Z)

````text
You are the BUILDER for unit E6b in /Users/rodrigoarista/Downloads/virality-pipeline. Read the full spec at /Users/rodrigoarista/.claude/jobs/99bc5ad8/tmp/e6b_spec.md and implement exactly it. Keep reads scoped (spec files plus what you touch); be concise. Hard rules: .venv/bin/python only; no git add/commit/checkout/stash/reset; do NOT modify src/ (report gaps instead), state/, .env, .planning/, .now.md; never run the script against the live DB except the --dry-run VERIFY step (read-only, must create no backup); no new dependencies; new files ≤200 lines. Run every VERIFY command for real and paste the real tails in the report. Write the complete report to .artifacts/agent-reports/e6b-builder.md. Return ≤8 lines: verdict, files, test counts, dry-run numbers (rows, estimated USD), risks, report path. No diffs or logs in the reply.
````

### Referenced spec file: /Users/rodrigoarista/.claude/jobs/99bc5ad8/tmp/e6b_spec.md (file no longer on disk; recovered verbatim from the orchestrator Write call at 2026-09-23T17:24:01Z)

````text
# E6b — reindex vivo con el modelo ganador (scripts/creative_rag/reembed_live.py)

CONTEXT
- E6a (commit 418fc1e9): src/creative_rag/active_model.py: ensure_meta, get_active_model(conn), set_active_model(conn, model), document_embedder(conn), query_embedder(conn); store.reembed_stale(embedder=None) re-embebe filas vivas con embed_model != activo o key_version != KEY_VERSION y estampa el activo; store.upsert/unretire siguen el activo. rag_vec y rag_vec_aspect se rellenan en reembed_stale (comprobar en store.py L263-297 que también rehace rag_vec_aspect; si no, usar src/creative_rag/aspects.backfill_aspect_vectors tras borrar los aspect vectors viejos).
- Patrón a reutilizar: scripts/creative_rag/migrate_e0_filters.py (refuses live sin CREATIVE_RAG_ALLOW_LIVE=1; VACUUM INTO backup con fecha en state/creative_rag/backups/; --dry-run sin escrituras) y scripts/creative_rag/bakeoff_embed.py (PaidEmbedder(model,"document", cache_dir), ledger delta, conteos rag_vec/rag_vec_aspect antes/después, _run_eval).
- Base viva: state/creative_rag/creative_rag.db (≈3.888 vivas, 5.833 totales, rag_vec 3.438). Costo esperado gemini-embedding-2 ≈0,10 USD. Caché de embeddings en state/creative_rag/embed_cache/ (git-ignored) — ya contiene ~3.947 textos gemini del bake-off: reutilizarla (cache_dir por defecto de PaidEmbedder) para que el costo real sea menor.
- Eval: scripts/creative_rag/eval_golden.py --label <x> escribe .artifacts/rag-eval/<fecha>_<x>.json (summary.overall.ndcg5). Con el modelo activo en rag_meta la consulta debe usarlo sin env var.

CHANGE
scripts/creative_rag/reembed_live.py (≤150 líneas), CLI: --model (obligatorio, debe estar en embed_client.KNOWN_MODELS o ser src.spine.embeddings.MODEL_NAME para volver a bge), --cap-usd (default 1.0), --dry-run, --db (default vivo), --skip-eval, --label (default e6-live-<model>).
Flujo: (1) sin CREATIVE_RAG_ALLOW_LIVE=1 y --db vivo → exit 2 sin tocar nada; (2) --dry-run imprime conteo de filas a re-embeber (vivas con embed_model != model o key_version distinta) y costo estimado (tokens ≈ chars/4 × precio de config/s1_providers.yaml) y sale sin escribir ni respaldar; (3) respaldo `VACUUM INTO state/creative_rag/backups/pre-e6-<model>-<fecha>.db` (falla si ya existe salvo --allow-existing-backup); (4) set_active_model(conn, model); (5) reembed_stale(embedder=PaidEmbedder(model,"document")) en lotes con checkpoint natural (si muere a medias, re-ejecutar continúa: las filas ya estampadas no se repiten — verificar que reembed_stale lo garantiza; si no, procesarlas en trozos comprometidos); abortar si el delta del ledger state/costs.jsonl supera --cap-usd; (6) post-checks: 0 filas vivas con embed_model != model; count(rag_vec) == vivas con vector antes; count(rag_vec_aspect) igual o mayor; imprime tabla antes/después + USD gastado; (7) salvo --skip-eval, corre eval_golden con --label y imprime overall ndcg5/mrr/hit10 y por consumidor; (8) exit ≠0 si algún post-check falla (y dice qué respaldo restaurar, sin restaurar solo).
Tests tests/creative_rag/test_reembed_live.py (≤120): sobre una base temporal sembrada (reusar fixtures de test_active_model / test_bakeoff): refuses sin ALLOW_LIVE; dry-run no escribe ni crea respaldo; corrida completa con PaidEmbedder monkeypatched (transport falso) estampa el modelo en todas las vivas, crea el respaldo, respeta el cap (cap 0 → aborta antes de estampar, base intacta = respaldo); re-ejecución tras abortar termina el resto sin repetir filas ya hechas.

GOAL
`CREATIVE_RAG_ALLOW_LIVE=1 .venv/bin/python scripts/creative_rag/reembed_live.py --model gemini-embedding-2 --cap-usd 1` deja la base viva entera en gemini-embedding-2, con respaldo, y reporta la nota del set dorado.

NOT-GOAL
No tocar store.py/active_model.py (si falta algo, decirlo en el informe, no parchear). No correr contra la base viva (solo tests). No reranker.

VERIFY
.venv/bin/python -m pytest tests/creative_rag -q (verde, ≥267+5) · .venv/bin/ruff check scripts/creative_rag tests/creative_rag · wc -l scripts/creative_rag/reembed_live.py (≤150) · `.venv/bin/python scripts/creative_rag/reembed_live.py --model gemini-embedding-2 --dry-run` contra la base viva (lectura; debe imprimir filas y costo estimado sin crear respaldo: comprobar `ls state/creative_rag/backups`).

REGLAS
Solo .venv/bin/python. Sin git add/commit. No escribir en state/ salvo lo que la propia --dry-run no hace (nada). No leer .env. Informe a .artifacts/agent-reports/e6b-builder.md; devolver ≤8 líneas.
````

## VERIFY
Run from the repo root against the commit's code (tests in today's tree may have changed; if so, check out the paths at the commit into a scratch copy, never into the repo):
```
.venv/bin/python -m pytest tests/creative_rag -q
.venv/bin/ruff check scripts/creative_rag tests/creative_rag
# The spec has a --dry-run against the live DB; do NOT run it unless you can guarantee read-only (it must create no backup file). Prefer reading the code.
```

## Risk area to weigh
live DB persistence / data loss (backup ordering, crash mid-run) + spend cap
