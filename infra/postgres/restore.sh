#!/bin/bash
# Restauración de un backup comprimido (.sql.gz) en la base de datos.
#
# Uso (dentro del contenedor de Postgres):
#   restore.sh /backups/precios-20261020T030000Z.sql.gz
#
# La base destino se recrea: CUIDADO, esto borra los datos actuales.
set -euo pipefail

ORIGEN="${1:?uso: restore.sh <fichero.sql.gz>}"

: "${POSTGRES_USER:?POSTGRES_USER no definida}"
: "${POSTGRES_DB:?POSTGRES_DB no definida}"

if [ ! -f "$ORIGEN" ]; then
  echo "No existe el backup: ${ORIGEN}" >&2
  exit 1
fi

echo "Restaurando ${ORIGEN} en ${POSTGRES_DB}..."
psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" \
  -c "GRANT ALL ON SCHEMA public TO ${POSTGRES_USER};"

gunzip -c "$ORIGEN" | psql -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB"

echo "Restauración completada."
