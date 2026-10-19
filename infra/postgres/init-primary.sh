#!/bin/bash
# Inicialización del primario: crea el usuario de replicación y permite
# conexiones de streaming desde la réplica. Solo se ejecuta con el volumen vacío.
set -euo pipefail

: "${POSTGRES_REPLICATION_USER:?POSTGRES_REPLICATION_USER no definida}"
: "${POSTGRES_REPLICATION_PASSWORD:?POSTGRES_REPLICATION_PASSWORD no definida}"

psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=replication_user="$POSTGRES_REPLICATION_USER" \
  --set=replication_password="$POSTGRES_REPLICATION_PASSWORD" <<'EOSQL'
SELECT format(
  'CREATE ROLE %I WITH REPLICATION LOGIN PASSWORD %L',
  :'replication_user',
  :'replication_password'
)
WHERE NOT EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname = :'replication_user'
)\gexec
EOSQL

HBA_LINE="host replication ${POSTGRES_REPLICATION_USER} all scram-sha-256"
if ! grep -qxF "$HBA_LINE" "$PGDATA/pg_hba.conf"; then
  printf '%s\n' "$HBA_LINE" >> "$PGDATA/pg_hba.conf"
fi
