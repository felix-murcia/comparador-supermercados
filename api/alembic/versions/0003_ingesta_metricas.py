"""Tabla de métricas de ingesta.

Revision ID: 0003_ingesta_metricas
Revises: 0002_usuarios
Create Date: 2026-10-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_ingesta_metricas"
down_revision: str | None = "0002_usuarios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingesta_metricas",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("producto_cadena_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cadena", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingesta_metricas"),
        sa.CheckConstraint(
            "estado IN ('verificado', 'sospechoso', 'rechazado')",
            name="chk_ingesta_metricas_estado",
        ),
    )
    op.create_index("idx_ingesta_metricas_estado", "ingesta_metricas", ["estado"])
    op.create_index("idx_ingesta_metricas_creado_en", "ingesta_metricas", ["creado_en"])


def downgrade() -> None:
    op.drop_index("idx_ingesta_metricas_creado_en", table_name="ingesta_metricas")
    op.drop_index("idx_ingesta_metricas_estado", table_name="ingesta_metricas")
    op.drop_table("ingesta_metricas")
