#!/bin/bash
# Backup comprimido de la base de datos y limpieza por retención.
# Se ejecuta dentro del contenedor de Postgres (tiene pg_dump) y deja los
# ficheros en BACKUP_DIR con el nombre `precios-<fecha>.sql.gz`.
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENCION_DIAS="${RETENCION_DIAS:-7}"
PREFIJO="${BACKUP_PREFIX:-precios}"

: "${POSTGRES_USER:?POSTGRES_USER no definida}"
: "${POSTGRES_DB:?POSTGRES_DB no definida}"

mkdir -p "$BACKUP_DIR"

FECHA="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINO="${BACKUP_DIR}/${PREFIJO}-${FECHA}.sql.gz"

echo "Backup de ${POSTGRES_DB} -> ${DESTINO}"
pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  | gzip -9 > "$DESTINO"

# La base vacía genera un dump de 0 bytes: no lo conservamos.
if [ ! -s "$DESTINO" ]; then
  rm -f "$DESTINO"
  echo "El dump ha salido vacío; no se conserva."
  exit 0
fi

echo "Retirando backups con más de ${RETENCION_DIAS} días..."
find "$BACKUP_DIR" -maxdepth 1 -name "${PREFIJO}-*.sql.gz" -type f \
  -mtime "+${RETENCION_DIAS}" -print -delete

ls -lh "$BACKUP_DIR"
