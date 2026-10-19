"""Implementación SQLAlchemy de `RepositorioProductos`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import producto_desde_modelo
from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)
from src.dominio.productos.entidades import (
    Producto,
    ProductoIngestable,
    ProductoNuevo,
)
from src.dominio.productos.reglas import normalizar_nombre


class SQLAlchemyRepositorioProductos:
    """Clase inyectable con la sesión del caso de uso (RO o RW)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener(self, producto_id: UUID) -> Producto | None:
        modelo = await self._session.get(ProductoModelo, producto_id)
        if modelo is None:
            return None
        return producto_desde_modelo(modelo)

    async def obtener_por_ean(self, ean: str) -> Producto | None:
        modelo = await self._session.scalar(
            select(ProductoModelo).where(ProductoModelo.ean == ean).limit(1)
        )
        if modelo is None:
            return None
        return producto_desde_modelo(modelo)

    async def buscar_por_nombre(
        self, consulta: str, limite: int = 20
    ) -> list[Producto]:
        similitud = func.similarity(ProductoModelo.nombre, consulta)
        sentencia = (
            select(ProductoModelo)
            .where(
                or_(
                    ProductoModelo.nombre.icontains(consulta, autoescape=True),
                    similitud >= 0.2,
                )
            )
            .order_by(similitud.desc(), ProductoModelo.nombre)
            .limit(limite)
        )
        modelos = (await self._session.scalars(sentencia)).all()
        return [producto_desde_modelo(modelo) for modelo in modelos]

    async def crear(self, datos: ProductoNuevo) -> Producto:
        modelo = ProductoModelo(
            nombre=datos.nombre,
            marca=datos.marca,
            categoria=datos.categoria,
            formato=datos.formato,
            litros_o_kg=datos.litros_o_kg,
            ean=datos.ean,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return producto_desde_modelo(modelo)

    async def obtener_por_slug(self, slug: str) -> Producto | None:
        """Resuelve un producto por su slug (nombre normalizado o EAN)."""
        texto = normalizar_nombre(slug.replace("-", " "))
        if not texto:
            return None

        if texto.isdigit():
            por_ean = await self.obtener_por_ean(texto)
            if por_ean is not None:
                return por_ean

        for producto in await self.buscar_por_nombre(texto, limite=5):
            if normalizar_nombre(producto.nombre) == texto:
                return producto
        return None

    async def listar_ingestables(self) -> list[ProductoIngestable]:
        """Productos con al menos una cadena, con los `slug` de esas cadenas."""
        filas = (
            await self._session.execute(
                select(ProductoModelo.id, ProductoModelo.nombre, CadenaModelo.slug)
                .join(
                    ProductoCadenaModelo,
                    ProductoCadenaModelo.producto_id == ProductoModelo.id,
                )
                .join(CadenaModelo, CadenaModelo.id == ProductoCadenaModelo.cadena_id)
                .order_by(ProductoModelo.nombre, CadenaModelo.slug)
            )
        ).all()

        por_producto: dict[UUID, ProductoIngestable] = {}
        for producto_id, nombre, slug in filas:
            existente = por_producto.get(producto_id)
            if existente is None:
                por_producto[producto_id] = ProductoIngestable(
                    id=producto_id, nombre=nombre, cadenas=(slug,)
                )
            else:
                por_producto[producto_id] = ProductoIngestable(
                    id=producto_id,
                    nombre=existente.nombre,
                    cadenas=existente.cadenas + (slug,),
                )
        return list(por_producto.values())
