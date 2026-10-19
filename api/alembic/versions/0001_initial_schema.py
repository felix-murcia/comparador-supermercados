"""Esquema inicial de datos.

Incluye cadenas, productos, mapeos, precios, búsquedas, listas y sus items.
La tabla `usuarios` y las claves foráneas de `usuario_id` se añaden en T1.2,
cuando exista dicha tabla.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "cadenas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("logo_svg", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cadenas"),
        sa.UniqueConstraint("slug", name="uq_cadenas_slug"),
    )

    op.create_table(
        "productos",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("marca", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("formato", sa.Text(), nullable=True),
        sa.Column("litros_o_kg", sa.Numeric(), nullable=True),
        sa.Column("ean", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "litros_o_kg IS NULL OR litros_o_kg > 0",
            name="chk_productos_litros_o_kg",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_productos"),
    )

    op.create_table(
        "productos_cadena",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("producto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cadena_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url_producto", sa.Text(), nullable=False),
        sa.Column("nombre_en_cadena", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["productos.id"],
            name="fk_productos_cadena_producto",
        ),
        sa.ForeignKeyConstraint(
            ["cadena_id"],
            ["cadenas.id"],
            name="fk_productos_cadena_cadena",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_productos_cadena"),
        sa.UniqueConstraint(
            "producto_id",
            "cadena_id",
            name="uq_productos_cadena_producto_cadena",
        ),
    )

    op.create_table(
        "precios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("producto_cadena_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("precio_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("precio_por_litro_kg", sa.Numeric(10, 4), nullable=True),
        sa.Column("disponible", sa.Boolean(), nullable=True),
        sa.Column("promocion", sa.Text(), nullable=True),
        sa.Column(
            "ambito",
            sa.Text(),
            server_default=sa.text("'nacional'"),
            nullable=False,
        ),
        sa.Column("provincia", sa.Text(), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("url_fuente", sa.Text(), nullable=False),
        sa.Column("fecha_consulta", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ambito IN ('nacional', 'provincia')",
            name="chk_precios_ambito",
        ),
        sa.CheckConstraint(
            "ambito = 'nacional' OR provincia IS NOT NULL",
            name="chk_precios_ambito_provincia",
        ),
        sa.CheckConstraint(
            "estado IN ('verificado', 'sospechoso', 'rechazado')",
            name="chk_precios_estado",
        ),
        sa.CheckConstraint("precio_eur >= 0", name="chk_precios_precio_eur"),
        sa.CheckConstraint(
            "precio_por_litro_kg IS NULL OR precio_por_litro_kg >= 0",
            name="chk_precios_precio_por_litro_kg",
        ),
        sa.ForeignKeyConstraint(
            ["producto_cadena_id"],
            ["productos_cadena.id"],
            name="fk_precios_producto_cadena",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_precios"),
    )

    op.create_table(
        "busquedas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("cadenas", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("provincia", sa.Text(), nullable=True),
        sa.Column(
            "estado",
            sa.Text(),
            server_default=sa.text("'pendiente'"),
            nullable=False,
        ),
        sa.Column(
            "progreso",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("cache_key", sa.Text(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'en_progreso', 'completada', 'fallida')",
            name="chk_busquedas_estado",
        ),
        sa.CheckConstraint(
            "progreso BETWEEN 0 AND 100",
            name="chk_busquedas_progreso",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_busquedas"),
    )

    op.create_table(
        "listas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_listas"),
    )

    op.create_table(
        "lista_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("lista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("producto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cadena_compra_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "cantidad",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("precio_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cantidad > 0",
            name="chk_lista_items_cantidad",
        ),
        sa.CheckConstraint(
            "precio_snapshot IS NULL OR precio_snapshot >= 0",
            name="chk_lista_items_precio_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["lista_id"],
            ["listas.id"],
            name="fk_lista_items_lista",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["productos.id"],
            name="fk_lista_items_producto",
        ),
        sa.ForeignKeyConstraint(
            ["cadena_compra_id"],
            ["cadenas.id"],
            name="fk_lista_items_cadena_compra",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lista_items"),
    )

    op.create_index(
        "idx_productos_nombre_trgm",
        "productos",
        ["nombre"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"nombre": "gin_trgm_ops"},
    )
    op.create_index(
        "idx_productos_cadena_cadena_id",
        "productos_cadena",
        ["cadena_id"],
        unique=False,
    )
    op.create_index(
        "idx_busquedas_cache_key",
        "busquedas",
        ["cache_key"],
        unique=False,
    )
    op.create_index(
        "idx_busquedas_estado",
        "busquedas",
        ["estado"],
        unique=False,
    )
    op.create_index(
        "idx_busquedas_usuario_id",
        "busquedas",
        ["usuario_id"],
        unique=False,
    )
    op.create_index(
        "idx_listas_usuario_id",
        "listas",
        ["usuario_id"],
        unique=False,
    )
    op.create_index(
        "idx_lista_items_lista_id",
        "lista_items",
        ["lista_id"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX idx_precios_pc_fecha "
        "ON precios (producto_cadena_id, fecha_consulta DESC)"
    )

    # `precios` es append-only: el histórico se conserva y nunca se actualiza
    # ni se borra. Las correcciones se insertan como una nueva fila.
    op.execute(
        """
        CREATE FUNCTION fn_precios_append_only()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'precios es append-only: solo se permiten INSERT';
        END;
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_precios_append_only "
        "BEFORE UPDATE OR DELETE ON precios "
        "FOR EACH ROW EXECUTE FUNCTION fn_precios_append_only()"
    )


def downgrade() -> None:
    op.drop_table("lista_items")
    op.drop_table("listas")
    op.drop_table("busquedas")
    op.drop_table("precios")
    op.drop_table("productos_cadena")
    op.drop_table("productos")
    op.drop_table("cadenas")
    op.execute("DROP FUNCTION IF EXISTS fn_precios_append_only()")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
