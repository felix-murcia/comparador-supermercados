"""Tabla usuarios y claves foráneas de usuario_id.

Crea `usuarios` (T1.2) y añade las FK de `busquedas.usuario_id` y
`listas.usuario_id` que quedaron pendientes en la migración inicial.
`ON DELETE SET NULL`: borrar un usuario no elimina su historial de
búsquedas ni sus listas; quedan como anónimas.

Revision ID: 0002_usuarios
Revises: 0001_initial_schema
Create Date: 2026-10-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_usuarios"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=True),
        sa.Column("provincia", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.UniqueConstraint(
            "provider", "provider_id", name="uq_usuarios_provider_provider_id"
        ),
    )
    op.create_index("idx_usuarios_email", "usuarios", ["email"])
    op.create_foreign_key(
        "fk_busquedas_usuario",
        "busquedas",
        "usuarios",
        ["usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_listas_usuario",
        "listas",
        "usuarios",
        ["usuario_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_listas_usuario", "listas", type_="foreignkey")
    op.drop_constraint("fk_busquedas_usuario", "busquedas", type_="foreignkey")
    op.drop_index("idx_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
