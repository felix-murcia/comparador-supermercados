"""Modelos SQLAlchemy que reflejan la migración inicial.

`Base.metadata` no crea esquema: la fuente de verdad es Alembic. Estos modelos
solo se usan para consultar y escribir filas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CadenaModelo(Base):
    __tablename__ = "cadenas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(Text, unique=True)
    nombre: Mapped[str] = mapped_column(Text)
    logo_svg: Mapped[str] = mapped_column(Text)


class ProductoModelo(Base):
    __tablename__ = "productos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(Text)
    marca: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(Text)
    formato: Mapped[str | None] = mapped_column(Text)
    litros_o_kg: Mapped[Decimal | None] = mapped_column(Numeric)
    ean: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ProductoCadenaModelo(Base):
    __tablename__ = "productos_cadena"
    __table_args__ = (
        UniqueConstraint(
            "producto_id",
            "cadena_id",
            name="uq_productos_cadena_producto_cadena",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id")
    )
    cadena_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadenas.id")
    )
    url_producto: Mapped[str] = mapped_column(Text)
    nombre_en_cadena: Mapped[str | None] = mapped_column(Text)


class PrecioModelo(Base):
    __tablename__ = "precios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    producto_cadena_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos_cadena.id")
    )
    precio_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_por_litro_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    disponible: Mapped[bool | None] = mapped_column(Boolean)
    promocion: Mapped[str | None] = mapped_column(Text)
    ambito: Mapped[str] = mapped_column(Text, server_default=text("'nacional'"))
    provincia: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text)
    url_fuente: Mapped[str] = mapped_column(Text)
    fecha_consulta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class UsuarioModelo(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_id",
            name="uq_usuarios_provider_provider_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    provider: Mapped[str] = mapped_column(Text)
    provider_id: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    nombre: Mapped[str | None] = mapped_column(Text)
    provincia: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class IngestaMetricasModelo(Base):
    __tablename__ = "ingesta_metricas"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('verificado', 'sospechoso', 'rechazado')",
            name="chk_ingesta_metricas_estado",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    producto_cadena_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    cadena: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text)
    motivo: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class BusquedaModelo(Base):
    __tablename__ = "busquedas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    query: Mapped[str] = mapped_column(Text)
    cadenas: Mapped[list[str]] = mapped_column(ARRAY(Text))
    provincia: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, server_default=text("'pendiente'"))
    progreso: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_key: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    completado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ListaModelo(Base):
    __tablename__ = "listas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    nombre: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ItemListaModelo(Base):
    __tablename__ = "lista_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    lista_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listas.id", ondelete="CASCADE")
    )
    producto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("productos.id")
    )
    cadena_compra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadenas.id")
    )
    cantidad: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    precio_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
