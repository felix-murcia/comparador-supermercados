"""Puertos de repositorios (SQLAlchemy los implementa en adaptadores).

Los métodos no eligen engine: quien los invoca inyecta una `AsyncSession` de
lectura (RO) o de escritura (RW) según el caso de uso.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable
from uuid import UUID

from src.dominio.busquedas.entidades import Busqueda, BusquedaNueva
from src.dominio.busquedas.estados import EstadoBusqueda
from src.dominio.listas.entidades import ItemLista, ItemListaNuevo, Lista
from src.dominio.precios.entidades import PrecioNuevo, PrecioRegistrado
from src.dominio.productos.entidades import Producto, ProductoNuevo
from src.dominio.usuarios.entidades import IdentidadOAuth, Usuario


@runtime_checkable
class RepositorioProductos(Protocol):
    """Lecturas y altas de productos canónicos."""

    async def obtener(self, producto_id: UUID) -> Producto | None: ...

    async def obtener_por_ean(self, ean: str) -> Producto | None: ...

    async def buscar_por_nombre(
        self, consulta: str, limite: int = 20
    ) -> list[Producto]: ...

    async def crear(self, datos: ProductoNuevo) -> Producto: ...


@runtime_checkable
class RepositorioPrecios(Protocol):
    """Histórico append-only de precios."""

    async def insertar(self, datos: PrecioNuevo) -> PrecioRegistrado: ...

    async def ultimo_verificado(
        self, producto_cadena_id: UUID
    ) -> PrecioRegistrado | None: ...

    async def historico(
        self, producto_cadena_id: UUID, limite: int = 10
    ) -> list[PrecioRegistrado]: ...


@runtime_checkable
class RepositorioListas(Protocol):
    """Listas de la compra y sus items."""

    async def crear(self, usuario_id: UUID | None, nombre: str) -> Lista: ...

    async def obtener(self, lista_id: UUID) -> Lista | None: ...

    async def listar_por_usuario(self, usuario_id: UUID) -> list[Lista]: ...

    async def agregar_item(self, datos: ItemListaNuevo) -> ItemLista: ...

    async def obtener_items(self, lista_id: UUID) -> list[ItemLista]: ...

    async def actualizar_item(
        self,
        item_id: UUID,
        *,
        cantidad: int | None = None,
        cadena_compra_id: UUID | None = None,
        precio_snapshot: Decimal | None = None,
    ) -> ItemLista | None: ...

    async def eliminar_item(self, item_id: UUID) -> bool: ...


@runtime_checkable
class RepositorioBusquedas(Protocol):
    """Jobs de búsqueda asíncrona."""

    async def crear(self, datos: BusquedaNueva) -> Busqueda: ...

    async def obtener(self, busqueda_id: UUID) -> Busqueda | None: ...

    async def obtener_por_cache_key(self, cache_key: str) -> Busqueda | None: ...

    async def actualizar_estado(
        self,
        busqueda_id: UUID,
        estado: EstadoBusqueda,
        progreso: int,
        completado_en: datetime | None = None,
    ) -> Busqueda | None: ...


@runtime_checkable
class RepositorioUsuarios(Protocol):
    """Perfiles de usuario indexados por proveedor OAuth."""

    async def upsert(self, identidad: IdentidadOAuth) -> Usuario: ...
