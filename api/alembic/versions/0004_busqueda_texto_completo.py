"""Búsqueda por texto completo sobre el nombre del producto.

La comparativa busca por el nombre del producto. Con `icontains` ("la
consulta aparece tal cual") no se encontraba "Aceite de oliva virgen extra"
al buscar "aceite oliva", porque en el nombre hay palabras de por medio. La
similitud de trigramas tampoco: da 0,448, por debajo del umbral.

Aquí se añade una función SQL con la normalización del nombre (minúsculas y
sin espacio entre la cantidad y la unidad, igual que `normalizar_nombre` del
dominio) y una columna generada con el `tsvector` de esa normalización. Con
ello la búsqueda usa `plainto_tsquery`, que busca por términos: "aceite
oliva" se convierte en `'aceit' & 'oliv'` y encuentra el producto aunque el
nombre tenga palabras intermedias. El índice GIN acelera la búsqueda.

La normalización vive en la base de datos (y no solo en la expresión de la
columna) para que la consulta aplique exactamente la misma regla al nombre
almacenado y a lo que escribe el usuario. `test_normalizar_nombre_coincide_con_sql`
comprueba que la función SQL y la del dominio dan el mismo resultado.

Revisión ID: 0004_busqueda_texto_completo
Revises: 0003_ingesta_metricas
Create Date: 2026-10-21

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_busqueda_texto_completo"
down_revision: str | None = "0003_ingesta_metricas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Normalización del nombre, equivalente a `normalizar_nombre` del dominio:
#   1. sin tildes (`unaccent`)
#   2. el multiplicador sin espacios ("4 x 125" -> "4x125")
#   3. el espacio entre la cantidad y la unidad ("1 L" -> "1L")
# Las minúsculas las pone `lower`.
_FUNCION_NORMALIZAR = """
CREATE FUNCTION nombre_buscable_normalizado(nombre text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT AS $$
    SELECT regexp_replace(
        regexp_replace(
            regexp_replace(lower(unaccent(nombre)), '(\\d)\\s*x\\s*(\\d)', '\\1x\\2', 'g'),
            '(\\d)\\s+([a-z]+)', '\\1\\2', 'g'
        ),
        '\\s+', ' ', 'g'
    );
$$
"""


def upgrade() -> None:
    # `unaccent` quita las tildes, como hace `normalizar_texto` en el dominio.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(_FUNCION_NORMALIZAR)
    op.execute(
        "ALTER TABLE productos ADD COLUMN nombre_buscable tsvector "
        "GENERATED ALWAYS AS ("
        "to_tsvector('spanish', nombre_buscable_normalizado(nombre))"
        ") STORED"
    )
    op.create_index(
        "idx_productos_nombre_buscable",
        "productos",
        ["nombre_buscable"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_productos_nombre_buscable", table_name="productos")
    op.execute("ALTER TABLE productos DROP COLUMN nombre_buscable")
    op.execute("DROP FUNCTION IF EXISTS nombre_buscable_normalizado(text)")
