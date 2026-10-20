"""Entidades del dominio de listas de la compra."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Lista:
    """Lista de la compra de un usuario (o anónima)."""

    id: UUID
    nombre: str
    creado_en: datetime
    usuario_id: UUID | None = None


@dataclass(frozen=True)
class ItemLista:
    """Producto dentro de una lista, con cantidad y compra opcional."""

    id: UUID
    lista_id: UUID
    producto_id: UUID
    cantidad: int
    creado_en: datetime
    cadena_compra_id: UUID | None = None
    precio_snapshot: Decimal | None = None


@dataclass(frozen=True)
class ItemListaNuevo:
    """Datos para agregar un item; id y creado_en los asigna la BD."""

    lista_id: UUID
    producto_id: UUID
    cantidad: int = 1
    cadena_compra_id: UUID | None = None
    precio_snapshot: Decimal | None = None


@dataclass(frozen=True)
class ItemListaDetalle:
    """Item de lista con los datos del producto, para mostrarlo en la interfaz."""

    item: ItemLista
    producto_nombre: str
    producto_marca: str | None = None
    producto_ean: str | None = None
    cadena_compra: str | None = None
