#!/bin/bash
# Restauración de un backup comprimido (.sql.gz) en la base de datos.
#
# Uso (dentro de un contenedor con psql):
#   restore.sh /backups/precios-20261020T030000Z.sql.gz
#
# La base destino se recrea: CUIDADO, esto borra los datos actuales.
set -euo pipefail

ORIGEN="${1:?uso: restore.sh <fichero.sql.gz>}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres-primary}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

: "${POSTGRES_USER:?POSTGRES_USER no definida}"
: "${POSTGRES_DB:?POSTGRES_DB no definida}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD no definida}"

# pg_dump/psql leen la contraseña del entorno (no la piden por TTY).
export PGPASSWORD="$POSTGRES_PASSWORD"

if [ ! -f "$ORIGEN" ]; then
  echo "No existe el backup: ${ORIGEN}" >&2
  exit 1
fi

echo "Restaurando ${ORIGEN} en ${POSTGRES_HOST}:${POSTGRES_PORT} (${POSTGRES_DB})..."
psql -v ON_ERROR_STOP=1 \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" \
  -c "GRANT ALL ON SCHEMA public TO ${POSTGRES_USER};"

gunzip -c "$ORIGEN" | psql -v ON_ERROR_STOP=1 \
  --host "$POSTGRES_HOST" \
  --port "$POSTGRES_PORT" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB"

echo "Restauración completada."
