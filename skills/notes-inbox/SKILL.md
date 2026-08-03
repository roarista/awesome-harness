---
name: notes-inbox
description: Procesar el Video Inbox de Notion — transcribir links de videos pegados por Ro, clasificarlos por proyecto, y rutearlos a Notion + espejo local ~/Notes. Activar cuando Ro diga "procesa el inbox", "checa el inbox", "/notes-inbox", o pegue un link de video pidiendo transcripción/ruteo.
---

<!-- MIRROR: copy of ~/.claude/skills/notes-inbox/SKILL.md (authoritative = the live ~/.claude copy). Re-sync: cp ~/.claude/skills/notes-inbox/SKILL.md skills/notes-inbox/SKILL.md -->

# notes-inbox — procesar el Video Inbox

Pipeline en `~/NotesPipeline/` (lee su CLAUDE.md). Config e IDs en `~/NotesPipeline/.env`.
Cero API credits de Claude: la transcripción es yt-dlp + ElevenLabs; la clasificación la haces
TÚ en esta sesión (suscripción).

## Pasos

1. **Fetch + transcribe**: `cd ~/NotesPipeline && ./run.sh`
   - Consulta filas Status=New del Inbox via REST (`scripts/notion_io.py list-new`), transcribe
     EN SERIE con `scripts/ingest.py`, deja `queue/<page_id>.json`, marca Transcribed.
   - Si `notion_io.py check` falla con 404: la página 🧠 Second Brain no está compartida con la
     integración "connection" — pedir a Ro el clic (••• → Connections) o, como fallback, leer el
     inbox via Notion MCP y correr ingest.py a mano por URL.
2. **Clasifica** cada `queue/*.json` que no tenga `.routed` marker: lee transcript y decide
   `{title (corto, descriptivo), project, summary (3 bullets), platform}`.
   Proyectos válidos: intrn, video-pipeline, vividlist, foreclosure-homes, ui, bible-pipeline,
   open-source, resume-linkedin, claude-code-tips, ideas, other.
3. **Escribe doble**:
   - Notion: `python3 scripts/notion_io.py write-result --page-id <id> --json <resultfile>`
     (actualiza fila → Routed + crea subpágina Transcript). Si REST no disponible, usar MCP.
   - Local: `~/Notes/<project>/new/<YYYY-MM-DD>-<slug>.md` con frontmatter:
     `notion_page_id`, `source_url`, `platform`, `status: new`, `summary`, y el transcript como body.
4. **Marca** el queue file procesado: crea `queue/<page_id>.routed` (vacío).
5. **Sync de vuelta**: `python3 scripts/sync_status.py` (refleja moves locales
   integrated/discarded → Status en Notion).
6. Reporta a Ro: cuántos videos, títulos y a qué proyecto fue cada uno.

## Reglas
- CPU bajo: serie, nunca paralelo; nunca whisper local.
- No borrar queue files (son el caché de idempotencia).
- Si un video falla (link muerto, video privado), marca la fila Status=Discarded con Summary
  explicando, y sigue.
