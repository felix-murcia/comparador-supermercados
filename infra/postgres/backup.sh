#!/bin/bash
# Backup comprimido de la base de datos y limpieza por retención.
# Se ejecuta dentro de un contenedor con pg_dump (no el del servidor: la base
# vive en otro contenedor) y deja los ficheros en BACKUP_DIR con el nombre
# `precios-<fecha>.sql.gz`.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENCION_DIAS="${RETENCION_DIAS:-7}"
PREFIJO="${BACKUP_PREFIX:-precios}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres-primary}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

: "${POSTGRES_USER:?POSTGRES_USER no definida}"
: "${POSTGRES_DB:?POSTGRES_DB no definida}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD no definida}"

# pg_dump/psql leen la contraseña del entorno (no la piden por TTY).
export PGPASSWORD="$POSTGRES_PASSWORD"

mkdir -p "$BACKUP_DIR"

FECHA="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINO="${BACKUP_DIR}/${PREFIJO}-${FECHA}.sql.gz"
TEMPORAL="${DESTINO}.tmp"

echo "Backup de ${POSTGRES_DB} en ${POSTGRES_HOST}:${POSTGRES_PORT} -> ${DESTINO}"
if ! pg_dump \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  | gzip -9 > "$TEMPORAL"; then
  rm -f "$TEMPORAL"
  echo "pg_dump ha fallado; no se conserva el fichero."
  exit 1
fi

# La base vacía genera un dump de 0 bytes: no lo conservamos.
if [ ! -s "$TEMPORAL" ]; then
  rm -f "$TEMPORAL"
  echo "El dump ha salido vacío; no se conserva."
  exit 0
fi

mv "$TEMPORAL" "$DESTINO"

echo "Retirando backups con más de ${RETENCION_DIAS} días..."
find "$BACKUP_DIR" -maxdepth 1 -name "${PREFIJO}-*.sql.gz" -type f \
  -mtime "+${RETENCION_DIAS}" -print -delete

ls -lh "$BACKUP_DIR"
