#!/bin/bash
# Inicialización de la réplica: clona el primario con pg_basebackup y arranca
# PostgreSQL en modo standby. Si ya hay datos, arranca directamente.
set -euo pipefail

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PRIMARY_HOST="${PRIMARY_HOST:-postgres-primary}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
PGPASSFILE="${HOME:-/var/lib/postgresql}/.pgpass"

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER no definida}"
: "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD no definida}"

# Se recrea en cada arranque: el fichero vive en la capa del contenedor,
# no en el volumen, y el standby lo necesita para autenticarse al primario.
umask 077
printf '%s:%s:replication:%s:%s\n' \
  "$PRIMARY_HOST" \
  "$PRIMARY_PORT" \
  "$POSTGRES_REPLICATION_USER" \
  "$POSTGRES_REPLICATION_PASSWORD" > "$PGPASSFILE"
export PGPASSFILE

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Réplica vacía: clonando desde ${PRIMARY_HOST}:${PRIMARY_PORT}..."
  until pg_basebackup \
    --host="$PRIMARY_HOST" \
    --port="$PRIMARY_PORT" \
    --username="$POSTGRES_REPLICATION_USER" \
    --pgdata="$PGDATA" \
    --wal-method=stream \
    --checkpoint=fast \
    --progress \
    --write-recovery-conf; do
    echo "Primario no disponible todavía; reintentando en 2 s..."
    sleep 2
  done

  chmod 700 "$PGDATA"
fi

exec docker-entrypoint.sh postgres
