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
from src.dominio.cadenas.entidades import Cadena
from src.dominio.ingesta.entidades import MetricaIngesta, MetricasIngesta
from src.dominio.listas.entidades import ItemLista, ItemListaNuevo, Lista
from src.dominio.precios.entidades import (
    FiltrosComparacion,
    HistoricoPrecio,
    PrecioNuevo,
    PrecioRegistrado,
    PrecioVigente,
    ResultadoComparacion,
)
from src.dominio.productos.entidades import Producto, ProductoIngestable, ProductoNuevo
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

    async def listar_ingestables(self) -> list[ProductoIngestable]: ...

    async def obtener_por_slug(self, slug: str) -> Producto | None: ...


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

    async def buscar_comparativa(
        self, filtros: FiltrosComparacion
    ) -> list[ResultadoComparacion]: ...

    async def precios_actuales(
        self, producto_id: UUID, provincia: str | None = None
    ) -> list[PrecioVigente]: ...

    async def historico_producto(
        self, producto_id: UUID, desde: datetime | None = None
    ) -> list[HistoricoPrecio]: ...


@runtime_checkable
class RepositorioListas(Protocol):
    """Listas de la compra y sus items."""

    async def crear(self, usuario_id: UUID | None, nombre: str) -> Lista: ...

    async def obtener(self, lista_id: UUID) -> Lista | None: ...

    async def listar_por_usuario(self, usuario_id: UUID) -> list[Lista]: ...

    async def renombrar(self, lista_id: UUID, nombre: str) -> Lista | None: ...

    async def eliminar(self, lista_id: UUID) -> bool: ...

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

    async def obtener_por_provider(
        self, provider: str, provider_id: str
    ) -> Usuario | None: ...

    async def actualizar(
        self, usuario_id: UUID, nombre: str | None, provincia: str | None
    ) -> Usuario: ...


@runtime_checkable
class RepositorioCadenas(Protocol):
    """Catálogo de cadenas de supermercados."""

    async def obtener_por_slug(self, slug: str) -> Cadena | None: ...


@runtime_checkable
class RepositorioProductosCadenas(Protocol):
    """Relación entre un producto canónico y una cadena, con su URL de ficha."""

    async def obtener_por_producto_y_cadena(
        self, producto_id: UUID, cadena_id: UUID
    ) -> UUID | None: ...

    async def crear(
        self,
        producto_id: UUID,
        cadena_id: UUID,
        url_producto: str,
        nombre_en_cadena: str,
    ) -> UUID: ...


@runtime_checkable
class RepositorioMetricas(Protocol):
    """Métricas de la ingesta: reparto por estado y motivos más frecuentes."""

    async def registrar(self, metrica: MetricaIngesta) -> None: ...

    async def resumen(self, desde: datetime | None = None) -> MetricasIngesta: ...
