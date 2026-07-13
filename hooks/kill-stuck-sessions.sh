#!/usr/bin/env bash
# Mata sesiones de Claude que están atascadas en "context window limit".
# Uso: kill-stuck-sessions.sh [--dry-run] [--all|--repo <path>]
set -euo pipefail

DRY=0
KILL_ALL=0
TARGET_REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --all) KILL_ALL=1; shift ;;
    --repo) TARGET_REPO="$2"; shift 2 ;;
    *) echo "Uso: $0 [--dry-run] [--all|--repo <path>]"; exit 1 ;;
  esac
done

echo "=== Sesiones de Claude activas ==="
# Buscar procesos claude que no sean el daemon principal
ps aux | grep "[c]laude" | grep -v "daemon run" | while read -r line; do
  pid=$(echo "$line" | awk '{print $2}')
  cmd=$(echo "$line" | awk '{print $11,$12,$13,$14,$15}')
  # Obtener cwd de forma segura
  cwd="unknown"
  if command -v lsof >/dev/null 2>&1; then
    cwd=$(lsof -p "$pid" 2>/dev/null | grep cwd | awk '{print $NF}' | head -1 | sed "s|$HOME|~|" || echo "unknown")
  fi
  printf "%-8s %s\n" "PID:$pid" "$cwd  →  $cmd"
done

echo
if [[ "$KILL_ALL" -eq 1 ]]; then
  if [[ "$DRY" -eq 1 ]]; then
    echo "=== MODO DRY: mataría todas las sesiones (excepto daemon) ==="
    ps aux | grep "[c]laude" | grep -v "daemon run" | awk '{print $2}' | while read -r pid; do
      echo "  Mataría PID $pid"
    done
  else
    echo "=== Matando TODAS las sesiones de Claude (excepto daemon) ==="
    pkill -f "claude" || echo "No hay sesiones para matar."
    echo "Listo. Reinicia tus sesiones desde cada terminal."
  fi
elif [[ -n "$TARGET_REPO" ]]; then
  echo "=== Matando sesiones en $TARGET_REPO ==="
  if [[ "$DRY" -eq 1 ]]; then
    echo "MODO DRY: estas sesiones serían matadas en $TARGET_REPO"
    lsof +D "$TARGET_REPO" 2>/dev/null | grep -i claude | awk '{print $2}' | sort -u || echo "  (ninguna encontrada)"
  else
    pids=$(lsof +D "$TARGET_REPO" 2>/dev/null | grep -i claude | awk '{print $2}' | sort -u || true)
    if [[ -z "$pids" ]]; then
      echo "No se encontraron sesiones Claude en $TARGET_REPO"
    else
      for pid in $pids; do
        echo "Matando PID $pid..."
        kill "$pid" 2>/dev/null || echo "  (ya murió o no existe)"
      done
    fi
  fi
else
  echo "Modo info. Para matar sesiones, usa:"
  echo "  $0 --all                         # matar TODAS las sesiones"
  echo "  $0 --all --dry-run              # ver qué mataría (simulación)"
  echo "  $0 --repo ~/Downloads/intrn     # matar solo las de un repo"
fi
